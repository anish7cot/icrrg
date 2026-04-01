"""Celery application — single worker, single queue, Redis broker."""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "icrrg",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Auto-discover tasks in app.tasks package
celery_app.autodiscover_tasks(["app.tasks"])

# Explicit imports to ensure tasks are registered
import app.tasks.review_task  # noqa: F401, E402
import app.tasks.report_task  # noqa: F401, E402
