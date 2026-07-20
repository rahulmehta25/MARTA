"""
Celery application configuration for background tasks.
"""
from celery import Celery
from celery.schedules import crontab
from src.config import settings

# Create Celery app
app = Celery(
    'marta_tasks',
    broker=settings.redis_url or 'redis://localhost:6379/0',
    backend=settings.redis_url or 'redis://localhost:6379/0',
    include=['src.tasks.gtfs_tasks', 'src.tasks.analytics_tasks', 'src.tasks.cleanup_tasks']
)

# Configure Celery
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/New_York',
    enable_utc=True,
    result_expires=3600,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes
    task_soft_time_limit=540,  # 9 minutes
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=100
)

# Configure periodic tasks
app.conf.beat_schedule = {
    'update-gtfs-data': {
        'task': 'src.tasks.gtfs_tasks.update_gtfs_data',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
        'options': {'queue': 'gtfs'}
    },
    'poll-realtime-data': {
        'task': 'src.tasks.gtfs_tasks.poll_realtime_data',
        'schedule': 30.0,  # Every 30 seconds
        'options': {'queue': 'realtime'}
    },
    'calculate-analytics': {
        'task': 'src.tasks.analytics_tasks.calculate_system_metrics',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
        'options': {'queue': 'analytics'}
    },
    'cleanup-old-data': {
        'task': 'src.tasks.cleanup_tasks.cleanup_old_arrivals',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
        'options': {'queue': 'maintenance'}
    },
    'optimize-routes': {
        'task': 'src.tasks.analytics_tasks.optimize_routes',
        'schedule': crontab(hour='*/6'),  # Every 6 hours
        'options': {'queue': 'analytics'}
    }
}

# Route tasks to specific queues
app.conf.task_routes = {
    'src.tasks.gtfs_tasks.*': {'queue': 'gtfs'},
    'src.tasks.analytics_tasks.*': {'queue': 'analytics'},
    'src.tasks.cleanup_tasks.*': {'queue': 'maintenance'}
}

if __name__ == '__main__':
    app.start()