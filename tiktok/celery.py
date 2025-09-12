import os
import sys
from celery import Celery

# Fix for macOS fork() safety issues
if sys.platform == 'darwin':
    os.environ.setdefault('OBJC_DISABLE_INITIALIZE_FORK_SAFETY', 'YES')

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tiktok.settings')

app = Celery('tiktok')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Force Redis configuration
app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='django-db',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    # macOS specific settings to avoid SIGABRT
    worker_pool='threads' if sys.platform == 'darwin' else 'prefork',
    worker_concurrency=2 if sys.platform == 'darwin' else 4,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=True,
)

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}') 