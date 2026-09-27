from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from database.models.schedule_model import Schedule
from database.repositories.booking_repo import BookingRepository


def test_cleanup_expires_due_pending_booking_and_releases_schedule():
    now_utc = datetime.now(timezone.utc)
    booking = SimpleNamespace(
        status="PENDING",
        expires_at=now_utc - timedelta(seconds=1),
    )
    schedule = SimpleNamespace(id=uuid4(), status="PENDING")
    session = MagicMock()
    session.scalars.return_value.all.return_value = [schedule]
    session.scalar.return_value = booking

    expired_count = BookingRepository().expire_due(now=now_utc, session=session)

    assert expired_count == 1
    assert booking.status == "EXPIRED"
    assert schedule.status == "CANCELLED"
    session.flush.assert_called_once()


def test_cleanup_does_not_change_confirmed_booking():
    now_utc = datetime.now(timezone.utc)
    booking = SimpleNamespace(
        status="CONFIRMED",
        expires_at=now_utc - timedelta(seconds=1),
    )
    schedule = SimpleNamespace(id=uuid4(), status="CONFIRMED")
    session = MagicMock()
    session.scalars.return_value.all.return_value = [schedule]
    session.scalar.return_value = booking

    expired_count = BookingRepository().expire_due(now=now_utc, session=session)

    assert expired_count == 0
    assert booking.status == "CONFIRMED"
    assert schedule.status == "CONFIRMED"


def test_cleanup_is_idempotent_for_already_expired_booking():
    now_utc = datetime.now(timezone.utc)
    booking = SimpleNamespace(
        status="PENDING",
        expires_at=now_utc - timedelta(seconds=1),
    )
    schedule = SimpleNamespace(id=uuid4(), status="PENDING")
    session = MagicMock()
    session.scalars.return_value.all.return_value = [schedule]
    session.scalar.return_value = booking
    repository = BookingRepository()

    assert repository.expire_due(now=now_utc, session=session) == 1
    assert repository.expire_due(now=now_utc, session=session) == 0
    assert booking.status == "EXPIRED"
    assert schedule.status == "CANCELLED"


def test_cleanup_task_commits_transaction():
    from tasks.booking_tasks import release_expired_bookings

    session_context = MagicMock()
    session_context.__enter__.return_value = MagicMock()
    with patch("tasks.booking_tasks.SessionLocal", return_value=session_context):
        with patch.object(BookingRepository, "expire_due", return_value=3):
            assert release_expired_bookings.run() == 3

    session_context.__enter__.return_value.commit.assert_called_once()


def test_schedule_slot_has_database_unique_active_slot_guard():
    index = next(
        index
        for index in Schedule.__table__.indexes
        if index.name == "uq_active_schedule_slot"
    )

    assert index.unique
    assert "PENDING" in str(index.dialect_options["postgresql"]["where"])
    assert "CONFIRMED" in str(index.dialect_options["postgresql"]["where"])