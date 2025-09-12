from celery import shared_task
from django.utils import timezone
from api.models import CombineLabelTask
from api.utils.pdf.download_pdf import download_pdf_from_url
from api.utils.pdf.merge_pdf import merge_pdf_files
from api.utils.google.googleapi import GoogleDriveService
import logging

logger = logging.getLogger(__name__)

@shared_task
def debug_task():
    """Simple debug task to test Celery"""
    return "Celery is working!"

@shared_task(bind=True)
def process_combine_label_task(self, task_id):
    """
    Background task để xử lý combine label
    """
    try:
        # Lấy task từ database
        combine_task = CombineLabelTask.objects.get(id=task_id)
        
        # Update status thành PROCESSING
        combine_task.status = 'PROCESSING'
        combine_task.started_at = timezone.now()
        combine_task.celery_task_id = self.request.id
        combine_task.save()
        
        logger.info(f"Starting combine label task {task_id} with {len(combine_task.urls)} URLs")
        
        # Download PDFs với retry mechanism
        download_results = []
        for url in combine_task.urls:
            result = download_pdf_from_url(url)
            download_results.append(result)
            
            # Update progress (optional)
            self.update_state(
                state='PROGRESS',
                meta={'current': len(download_results), 'total': len(combine_task.urls)}
            )
        
        # Merge PDFs
        merge_result = merge_pdf_files(download_results)
        
        if not merge_result['success']:
            # Task failed
            combine_task.status = 'FAILED'
            combine_task.completed_at = timezone.now()
            combine_task.error_message = merge_result['error']
            combine_task.failed_count = len(combine_task.urls)
            combine_task.failed_urls = merge_result.get('failed_urls', [])
            combine_task.save()
            
            logger.error(f"Combine label task {task_id} failed: {merge_result['error']}")
            return {'status': 'FAILED', 'error': merge_result['error']}
        
        # Upload to Google Drive
        filename = f"combined_labels_{combine_task.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        upload_result = GoogleDriveService().upload_pdf_to_drive(
            merge_result['pdf_buffer'], 
            filename
        )
        
        if not upload_result['success']:
            # Upload failed
            combine_task.status = 'FAILED'
            combine_task.completed_at = timezone.now()
            combine_task.error_message = f"Failed to upload to Google Drive: {upload_result['error']}"
            combine_task.successful_count = len(merge_result['successful_urls'])
            combine_task.failed_count = len(merge_result['failed_urls'])
            combine_task.successful_urls = merge_result['successful_urls']
            combine_task.failed_urls = merge_result['failed_urls']
            combine_task.save()
            
            logger.error(f"Combine label task {task_id} upload failed: {upload_result['error']}")
            return {'status': 'FAILED', 'error': upload_result['error']}
        
        # Success - Update task với kết quả
        combine_task.status = 'COMPLETED'
        combine_task.completed_at = timezone.now()
        combine_task.drive_link = upload_result['link']
        combine_task.successful_count = len(merge_result['successful_urls'])
        combine_task.failed_count = len(merge_result['failed_urls'])
        combine_task.successful_urls = merge_result['successful_urls']
        combine_task.failed_urls = merge_result['failed_urls']
        combine_task.save()
        
        logger.info(f"Combine label task {task_id} completed successfully")
        return {
            'status': 'COMPLETED',
            'drive_link': upload_result['link'],
            'successful_count': len(merge_result['successful_urls']),
            'failed_count': len(merge_result['failed_urls'])
        }
        
    except CombineLabelTask.DoesNotExist:
        logger.error(f"Combine label task {task_id} not found")
        return {'status': 'FAILED', 'error': 'Task not found'}
    except Exception as e:
        logger.error(f"Error in combine label task {task_id}: {str(e)}")
        
        # Update task với error
        try:
            combine_task = CombineLabelTask.objects.get(id=task_id)
            combine_task.status = 'FAILED'
            combine_task.completed_at = timezone.now()
            combine_task.error_message = str(e)
            combine_task.save()
        except:
            pass
            
        return {'status': 'FAILED', 'error': str(e)} 