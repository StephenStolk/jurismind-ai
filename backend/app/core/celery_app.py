from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "legal_intelligence",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.document_tasks"],
)

celery_app.conf.update(
    # Task settings
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
    
     # Retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_max_retries=3,
    
    # Result expiry — keep results for 1 hour
    result_expires=3600,
    
    # Windows-specific — use eventlet pool
    worker_pool="eventlet",
    worker_concurrency=4,
)