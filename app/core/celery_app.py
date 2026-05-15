import os
from celery import Celery

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "worker",
    broker=redis_url,
    backend=redis_url,
    include=["app.tasks.link_checker_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    broker_connection_retry_on_startup=True
)

# Beat schedule
celery_app.conf.beat_schedule = {
    'check-all-links-every-6h': {
        'task': 'app.tasks.link_checker_tasks.check_all_active_links',
        'schedule': 6 * 60 * 60.0,  # a cada 6 horas
    },
}
