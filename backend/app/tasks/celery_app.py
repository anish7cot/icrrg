"""Celery application -- single worker, single queue, Redis broker.

When Redis is unreachable (e.g. corporate firewall), set REDIS_URL=""
in .env to run all tasks synchronously in the API process. No separate
Celery worker is needed in that mode.
"""

import ssl

from celery import Celery

from app.config import settings

_eager_mode = not settings.REDIS_URL

if _eager_mode:
    # No Redis -- run tasks synchronously inside the API process
    celery_app = Celery("icrrg")
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
    )
else:
    celery_app = Celery(
        "icrrg",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
    )

    # If using rediss:// (TLS), configure SSL to skip cert verification
    _broker_ssl = None
    if settings.REDIS_URL.startswith("rediss://"):
        _broker_ssl = {"ssl_cert_reqs": ssl.CERT_NONE}

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        broker_use_ssl=_broker_ssl,
        redis_backend_use_ssl=_broker_ssl,
    )

# Auto-discover tasks in app.tasks package
celery_app.autodiscover_tasks(["app.tasks"])

# Explicit imports to ensure tasks are registered
import app.tasks.review_task  # noqa: F401, E402
import app.tasks.report_task  # noqa: F401, E402
