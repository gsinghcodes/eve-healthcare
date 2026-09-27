from datetime import date, time, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from services.booking_service import BookingService


def test_booking_converts_ist_time_to_utc():
    user_id = uuid4()
    center_test_id = uuid4()
    session_context = MagicMock()
    session_context.__enter__.return_value = MagicMock()
    service = BookingService()
    service.center_test_repository.get_by_id = MagicMock(
        return_value=SimpleNamespace(
            is_active=True,
            price=Decimal("500.00"),
            center=SimpleNamespace(
                opening_time=time(8, 30),
                closing_time=time(12, 0),
            ),
        )
    )
    service.schedule_repository.get_by_slot_for_update = MagicMock(return_value=None)
    service.schedule_repository.create = MagicMock(
        return_value=SimpleNamespace(id=uuid4())
    )
    service.booking_repository.create = MagicMock(
        return_value=SimpleNamespace(id=uuid4(), status="PENDING")
    )

    with patch("services.booking_service.SessionLocal", return_value=session_context):
        response = service.create_booking(
            user_id=user_id,
            center_test_id=center_test_id,
            appointment_date=date.today() + timedelta(days=1),
            time_slot=time(9, 0),
        )

    assert response["status"] == 201
    assert (
        service.schedule_repository.get_by_slot_for_update.call_args.kwargs["starts_at"]
        == service.schedule_repository.create.call_args.kwargs["starts_at"]
    )
    assert service.schedule_repository.create.call_args.kwargs["starts_at"].time() == (
        time(3, 30)
    )
    assert service.schedule_repository.create.call_args.kwargs["starts_at"].tzinfo == (
        timezone.utc
    )
    expires_at = service.booking_repository.create.call_args.kwargs["expires_at"]
    assert expires_at.tzinfo is not None
    assert expires_at.utcoffset() == timedelta(0)
    assert expires_at > real_now_utc()


@pytest.mark.parametrize(
    "time_slot",
    [time(2, 0), time(8, 0), time(9, 15), time(12, 0), time(11, 0, 1)],
)
def test_create_booking_rejects_time_outside_business_slots(time_slot):
    service = BookingService()
    service.center_test_repository.get_by_id = MagicMock(
        return_value=SimpleNamespace(
            is_active=True,
            center=SimpleNamespace(
                opening_time=time(8, 30),
                closing_time=time(12, 0),
            ),
        )
    )
    service.schedule_repository.get_by_slot_for_update = MagicMock()
    service.schedule_repository.create = MagicMock()
    session_context = MagicMock()

    with patch("services.booking_service.SessionLocal", return_value=session_context):
        response = service.create_booking(
            user_id=uuid4(),
            center_test_id=uuid4(),
            appointment_date=date.today() + timedelta(days=1),
            time_slot=time_slot,
        )

    assert response["status"] == 400
    service.center_test_repository.get_by_id.assert_called_once()
    service.schedule_repository.get_by_slot_for_update.assert_not_called()
    service.schedule_repository.create.assert_not_called()


def test_get_user_bookings_returns_only_repository_results():
    user_id = uuid4()
    booking = SimpleNamespace(id=uuid4(), user_id=user_id, status="PENDING")
    session_context = MagicMock()
    session_context.__enter__.return_value = MagicMock()
    service = BookingService()
    service.booking_repository.get_user_bookings = MagicMock(return_value=[booking])

    with patch("services.booking_service.SessionLocal", return_value=session_context):
        response = service.get_user_bookings(user_id=user_id)

    assert response["status"] == 200
    assert response["data"] == [
        {"id": str(booking.id), "user_id": str(user_id), "status": "PENDING"}
    ]
    assert (
        service.booking_repository.get_user_bookings.call_args.kwargs["user_id"]
        == user_id
    )


def real_now_utc():
    from datetime import datetime

    return datetime.now(timezone.utc)


def test_expired_pending_booking_releases_schedule_for_new_booking():
    user_id = uuid4()
    center_test_id = uuid4()
    old_schedule = SimpleNamespace(id=uuid4(), status="PENDING")
    old_booking = SimpleNamespace(
        id=uuid4(),
        status="PENDING",
        expires_at=real_now_utc() - timedelta(seconds=1),
    )
    new_schedule = SimpleNamespace(id=uuid4())
    session_context = MagicMock()
    session_context.__enter__.return_value = MagicMock()
    service = BookingService()
    service.center_test_repository.get_by_id = MagicMock(
        return_value=SimpleNamespace(
            is_active=True,
            price=Decimal("500.00"),
            center=SimpleNamespace(
                opening_time=time(8, 30),
                closing_time=time(12, 0),
            ),
        )
    )
    service.schedule_repository.get_by_slot_for_update = MagicMock(
        return_value=old_schedule
    )
    service.booking_repository.get_by_schedule_for_update = MagicMock(
        return_value=old_booking
    )
    service.schedule_repository.create = MagicMock(return_value=new_schedule)
    service.booking_repository.create = MagicMock(
        return_value=SimpleNamespace(id=uuid4(), status="PENDING")
    )

    with patch("services.booking_service.SessionLocal", return_value=session_context):
        response = service.create_booking(
            user_id=user_id,
            center_test_id=center_test_id,
            appointment_date=date.today() + timedelta(days=1),
            time_slot=time(9, 0),
        )

    assert response["status"] == 201
    assert old_booking.status == "EXPIRED"
    assert old_schedule.status == "CANCELLED"
    assert service.booking_repository.create.call_args.kwargs["schedule_id"] == (
        new_schedule.id
    )


def test_cancel_rescheduled_booking_releases_its_current_schedule():
    user_id = uuid4()
    booking = SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        schedule_id=uuid4(),
        status="RESCHEDULED",
    )
    schedule = SimpleNamespace(
        id=booking.schedule_id,
        status="CONFIRMED",
        starts_at=real_now_utc() + timedelta(hours=12),
    )
    session_context = MagicMock()
    session_context.__enter__.return_value = MagicMock()
    service = BookingService()
    service.booking_repository.get_by_id = MagicMock(return_value=booking)
    service.booking_repository.get_by_id_for_update = MagicMock(return_value=booking)
    service.schedule_repository.get_by_id_for_update = MagicMock(return_value=schedule)
    service.payment_repository.get_successful_for_booking_for_update = MagicMock(
        return_value=[]
    )

    with patch("services.booking_service.SessionLocal", return_value=session_context):
        response = service.cancel_booking(booking_id=booking.id, user_id=user_id)

    assert response["status"] == 200
    assert booking.status == "CANCELLED"
    assert schedule.status == "CANCELLED"


@pytest.mark.parametrize(
    ("hours_before", "expected_payment_status"),
    [(25, "REFUNDED"), (23, "SUCCESS")],
)
def test_cancellation_refunds_successful_payments_only_at_least_one_day_ahead(
    hours_before,
    expected_payment_status,
):
    user_id = uuid4()
    booking = SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        schedule_id=uuid4(),
        status="CONFIRMED",
    )
    schedule = SimpleNamespace(
        id=booking.schedule_id,
        status="CONFIRMED",
        starts_at=real_now_utc() + timedelta(hours=hours_before),
    )
    payment = SimpleNamespace(status="SUCCESS")
    session_context = MagicMock()
    session_context.__enter__.return_value = MagicMock()
    service = BookingService()
    service.booking_repository.get_by_id = MagicMock(return_value=booking)
    service.booking_repository.get_by_id_for_update = MagicMock(return_value=booking)
    service.schedule_repository.get_by_id_for_update = MagicMock(return_value=schedule)
    service.payment_repository.get_successful_for_booking_for_update = MagicMock(
        return_value=[payment]
    )

    with patch("services.booking_service.SessionLocal", return_value=session_context):
        response = service.cancel_booking(booking_id=booking.id, user_id=user_id)

    assert response["status"] == 200
    assert payment.status == expected_payment_status
    assert ("refund issued" in response["message"]) == (
        expected_payment_status == "REFUNDED"
    )
