#!/usr/bin/env python3
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tiktok.settings')
django.setup()

from api.models import CombineLabelTask
from django.contrib.auth.models import User

def create_test_tasks(num_tasks=5, urls_per_task=3):
    """Tạo nhiều test tasks để test parallel processing"""
    
    # Get first user (hoặc tạo test user)
    try:
        user = User.objects.first()
        if not user:
            user = User.objects.create_user(
                username='testuser',
                email='test@example.com',
                password='testpass123'
            )
            print("Created test user")
    except Exception as e:
        print(f"Error getting user: {e}")
        return
    
    # Sample PDF URLs for testing
    test_urls = [
        "https://example.com/label1.pdf",
        "https://example.com/label2.pdf", 
        "https://example.com/label3.pdf",
        "https://example.com/label4.pdf",
        "https://example.com/label5.pdf",
        "https://example.com/label6.pdf",
        "https://example.com/label7.pdf",
        "https://example.com/label8.pdf",
    ]
    
    created_tasks = []
    
    for i in range(num_tasks):
        # Take different URLs for each task
        start_idx = (i * urls_per_task) % len(test_urls)
        task_urls = []
        
        for j in range(urls_per_task):
            url_idx = (start_idx + j) % len(test_urls)
            task_urls.append(test_urls[url_idx])
        
        # Create task
        task = CombineLabelTask.objects.create(
            user=user,
            urls=task_urls,
            total_urls=len(task_urls),
            status='PENDING'
        )
        
        created_tasks.append(task)
        print(f"✅ Created task {task.id} with {len(task_urls)} URLs")
    
    print(f"\n🎉 Created {len(created_tasks)} test tasks!")
    print("Now start background processor to see parallel processing:")
    print("python3 background_processor.py 5")
    
    return created_tasks

def cleanup_test_tasks():
    """Xóa tất cả test tasks"""
    tasks = CombineLabelTask.objects.all()
    count = tasks.count()
    tasks.delete()
    print(f"🧹 Deleted {count} tasks")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'cleanup':
        cleanup_test_tasks()
    else:
        # Parse arguments
        num_tasks = 5
        urls_per_task = 3
        
        if len(sys.argv) > 1:
            try:
                num_tasks = int(sys.argv[1])
            except ValueError:
                pass
                
        if len(sys.argv) > 2:
            try:
                urls_per_task = int(sys.argv[2])
            except ValueError:
                pass
        
        print(f"Creating {num_tasks} tasks with {urls_per_task} URLs each...")
        create_test_tasks(num_tasks, urls_per_task)
