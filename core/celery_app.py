from celery import Celery

from core.config import settings


celery_app = Celery(
    "eve_healthcare",
    broker=settings.CELERY_BROKER_URL,
    include=["tasks.booking_tasks"],
)
celery_app.conf.update(
    enable_utc=True,
    timezone="UTC",
    beat_schedule={
        "release-expired-bookings-every-minute": {
            "task": "tasks.booking_tasks.release_expired_bookings",
            "schedule": 60.0,
        }
    },
)