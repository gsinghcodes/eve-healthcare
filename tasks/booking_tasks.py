from datetime import datetime, timezone

from core.celery_app import celery_app
from database.repositories.booking_repo import BookingRepository
from database.session import SessionLocal


@celery_app.task(name="tasks.booking_tasks.release_expired_bookings")
def release_expired_bookings() -> int:
    now_utc = datetime.now(timezone.utc)
    with SessionLocal() as session:
        try:
            expired_count = BookingRepository().expire_due(
                now=now_utc,
                session=session,
            )
            session.commit()
            return expired_count
        except Exception:
            session.rollback()
            raise