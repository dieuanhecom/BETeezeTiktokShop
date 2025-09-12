#!/usr/bin/env python3
import os
import django
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tiktok.settings')
django.setup()

from api.models import CombineLabelTask
from api.utils.pdf.download_pdf import download_pdf_from_url
from api.utils.pdf.merge_pdf import merge_pdf_files
from api.utils.google.googleapi import GoogleDriveService
import logging

logger = logging.getLogger(__name__)

class BackgroundProcessor:
    def __init__(self, max_workers=5):
        self.running = False
        self.thread = None
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_tasks = set()  # Track active task IDs
    
    def start(self):
        """Start background processor"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._process_loop)
            self.thread.daemon = True
            self.thread.start()
            print(f"✅ Background processor started with {self.max_workers} workers")
    
    def stop(self):
        """Stop background processor"""
        self.running = False
        if self.thread:
            self.thread.join()
        self.executor.shutdown(wait=True)
        print("✅ Background processor stopped")
    
    def _process_loop(self):
        """Main processing loop"""
        futures = {}  # Track futures for active tasks
        
        while self.running:
            try:
                # Check completed futures
                completed_futures = []
                for future in list(futures.keys()):
                    if future.done():
                        task_id = futures[future]
                        try:
                            result = future.result()
                            print(f"✅ Task {task_id} completed: {result}")
                        except Exception as e:
                            print(f"❌ Task {task_id} failed: {e}")
                        finally:
                            self.active_tasks.discard(task_id)
                            completed_futures.append(future)
                
                # Remove completed futures
                for future in completed_futures:
                    del futures[future]
                
                # Find pending tasks (exclude already processing ones)
                pending_tasks = CombineLabelTask.objects.filter(
                    status='PENDING'
                ).exclude(id__in=self.active_tasks)
                
                # Submit new tasks up to max_workers limit
                available_slots = self.max_workers - len(futures)
                
                for task in pending_tasks[:available_slots]:
                    if not self.running:
                        break
                    
                    print(f"🚀 Starting task {task.id} in background...")
                    future = self.executor.submit(self._process_single_task, task)
                    futures[future] = task.id
                    self.active_tasks.add(task.id)
                
                # Show status
                if futures:
                    print(f"📊 Processing {len(futures)} tasks, {len(pending_tasks) - len(futures)} pending")
                
                # Sleep for 3 seconds before next check
                time.sleep(3)
                
            except Exception as e:
                print(f"Error in background processor: {e}")
                time.sleep(10)  # Wait longer on error
    
    def _process_single_task(self, task):
        """Process a single task"""
        try:
            # Refresh task from database to get latest status
            task.refresh_from_db()
            
            # Check if task was cancelled
            if task.status == 'CANCELLED':
                return f"Task {task.id} was cancelled"
            
            # Update status to PROCESSING
            task.status = 'PROCESSING'
            task.started_at = timezone.now()
            task.save()
            
            print(f"  [Task {task.id}] Starting processing {len(task.urls)} PDFs...")
            overall_start_time = timezone.now()
            
            # Download PDFs with parallel processing
            download_results = self._download_pdfs_parallel(task.urls, task.id)
            successful_downloads = sum(1 for r in download_results if r.get('success', False))
            
            # Merge PDFs with optimization
            print(f"  [Task {task.id}] Merging {successful_downloads} PDFs...")
            start_merge_time = timezone.now()
            merge_result = merge_pdf_files(download_results)
            merge_duration = (timezone.now() - start_merge_time).total_seconds()
            print(f"  [Task {task.id}] Merge completed in {merge_duration:.1f}s")
            
            if not merge_result['success']:
                # Task failed
                task.status = 'FAILED'
                task.completed_at = timezone.now()
                task.error_message = merge_result['error']
                task.failed_count = len(task.urls)
                task.failed_urls = merge_result.get('failed_urls', [])
                task.save()
                
                return f"Task {task.id} failed: {merge_result['error']}"
            
            # Upload to Google Drive
            print(f"  [Task {task.id}] Uploading to Google Drive...")
            start_upload_time = timezone.now()
            filename = f"combined_labels_{task.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            upload_result = GoogleDriveService().upload_pdf_to_drive(
                merge_result['pdf_buffer'], 
                filename
            )
            upload_duration = (timezone.now() - start_upload_time).total_seconds()
            print(f"  [Task {task.id}] Upload completed in {upload_duration:.1f}s")
            
            if not upload_result['success']:
                # Upload failed
                task.status = 'FAILED'
                task.completed_at = timezone.now()
                task.error_message = f"Failed to upload to Google Drive: {upload_result['error']}"
                task.successful_count = len(merge_result['successful_urls'])
                task.failed_count = len(merge_result['failed_urls'])
                task.successful_urls = merge_result['successful_urls']
                task.failed_urls = merge_result['failed_urls']
                task.save()
                
                return f"Task {task.id} upload failed: {upload_result['error']}"
            
            # Success - Update task với kết quả
            task.status = 'COMPLETED'
            task.completed_at = timezone.now()
            task.drive_link = upload_result['link']
            task.successful_count = len(merge_result['successful_urls'])
            task.failed_count = len(merge_result['failed_urls'])
            task.successful_urls = merge_result['successful_urls']
            task.failed_urls = merge_result['failed_urls']
            task.save()
            
            # Calculate total processing time
            total_duration = (timezone.now() - overall_start_time).total_seconds()
            print(f"  [Task {task.id}] ✅ Total processing time: {total_duration:.1f}s")
            
            return f"Task {task.id} completed successfully in {total_duration:.1f}s! Drive: {upload_result['link']}"
            
        except Exception as e:
            print(f"  ❌ Error processing task {task.id}: {str(e)}")
            
            # Update task với error
            try:
                task.status = 'FAILED'
                task.completed_at = timezone.now()
                task.error_message = str(e)
                task.save()
            except:
                pass
            
            return f"Task {task.id} failed: {str(e)}"
    
    def _download_pdfs_parallel(self, urls, task_id, max_download_workers=10):
        """Download PDFs in parallel for faster processing"""
        download_results = []
        
        def download_single_pdf(url_with_index):
            index, url = url_with_index
            print(f"    [Task {task_id}] Downloading {index+1}/{len(urls)}: {url[:50]}...")
            return download_pdf_from_url(url)
        
        # Use ThreadPoolExecutor for parallel downloads - increased workers
        with ThreadPoolExecutor(max_workers=min(max_download_workers, len(urls))) as download_executor:
            # Submit all download tasks
            future_to_index = {
                download_executor.submit(download_single_pdf, (i, url)): i 
                for i, url in enumerate(urls)
            }
            
            # Collect results in order
            results_dict = {}
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    result = future.result()
                    results_dict[index] = result
                except Exception as e:
                    print(f"    [Task {task_id}] Error downloading URL {index}: {e}")
                    results_dict[index] = {
                        'success': False,
                        'error': str(e),
                        'url': urls[index]
                    }
            
            # Sort results by index to maintain order
            download_results = [results_dict[i] for i in sorted(results_dict.keys())]
        
        successful_downloads = sum(1 for r in download_results if r.get('success', False))
        print(f"    [Task {task_id}] Downloaded {successful_downloads}/{len(urls)} PDFs successfully")
        
        return download_results

def main():
    """Main function to run background processor"""
    import sys
    
    # Allow configuring max workers via command line
    max_workers = 5  # Increased default
    if len(sys.argv) > 1:
        try:
            max_workers = int(sys.argv[1])
            if max_workers < 1:
                max_workers = 1
            elif max_workers > 15:
                max_workers = 15  # Increased max
        except ValueError:
            print("Invalid max_workers argument, using default (5)")
    
    processor = BackgroundProcessor(max_workers=max_workers)
    
    try:
        print(f"Starting background processor with {max_workers} concurrent tasks...")
        print("Usage: python3 background_processor.py [max_workers]")
        print("Example: python3 background_processor.py 5  # Process up to 5 tasks simultaneously")
        print("-" * 60)
        processor.start()
        
        # Keep running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping background processor...")
        processor.stop()
        print("Background processor stopped")

if __name__ == "__main__":
    main() 