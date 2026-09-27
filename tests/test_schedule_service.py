from datetime import date, datetime as real_datetime, time, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from services.schedule_service import ScheduleService


def test_today_slots_start_after_current_time_in_ist():
    appointment_date = date(2026, 9, 26)
    center_test_id = uuid4()
    session_context = MagicMock()
    session_context.__enter__.return_value = MagicMock()
    service = ScheduleService()
    service.center_test_repository.get_by_id = MagicMock(
        return_value=SimpleNamespace(
            is_active=True,
            center=SimpleNamespace(opening_time=time(15, 0), closing_time=time(17, 0)),
        )
    )
    service.schedule_repository.get_for_center_test_on_date = MagicMock(
        return_value=[]
    )

    with patch("services.schedule_service.SessionLocal", return_value=session_context):
        with patch("services.schedule_service.datetime") as datetime_mock:
            datetime_mock.now.return_value = real_datetime(
                2026, 9, 26, 9, 31, tzinfo=timezone.utc
            )
            datetime_mock.combine.side_effect = real_datetime.combine

            response = service.get_available_schedules(
                center_test_id=center_test_id,
                appointment_date=appointment_date,
            )

    assert [slot["starts_at"] for slot in response["data"]["slots"]] == [
        "2026-09-26T15:30:00+05:30",
        "2026-09-26T16:00:00+05:30",
        "2026-09-26T16:30:00+05:30",
    ]


def test_existing_ist_schedule_marks_matching_slot_unavailable():
    appointment_date = date(2026, 9, 27)
    center_test_id = uuid4()
    session_context = MagicMock()
    session_context.__enter__.return_value = MagicMock()
    service = ScheduleService()
    service.center_test_repository.get_by_id = MagicMock(
        return_value=SimpleNamespace(
            is_active=True,
            center=SimpleNamespace(opening_time=time(9, 0), closing_time=time(17, 0)),
        )
    )
    service.schedule_repository.get_for_center_test_on_date = MagicMock(
        return_value=[
                SimpleNamespace(
                starts_at=real_datetime(
                    2026,
                    9,
                    27,
                    16,
                    0,
                    tzinfo=timezone(timedelta(hours=5, minutes=30)),
                ),
                status="PENDING",
                    booking=SimpleNamespace(
                        status="PENDING",
                        expires_at=real_datetime(
                            2026, 9, 28, 0, 0, tzinfo=timezone.utc
                        ),
                    ),
            )
        ]
    )

    with patch("services.schedule_service.SessionLocal", return_value=session_context):
        with patch("services.schedule_service.datetime") as datetime_mock:
            datetime_mock.now.return_value = real_datetime(
                2026, 9, 26, 9, 31, tzinfo=timezone.utc
            )
            datetime_mock.combine.side_effect = real_datetime.combine

            response = service.get_available_schedules(
                center_test_id=center_test_id,
                appointment_date=appointment_date,
            )

    slot = next(
        slot
        for slot in response["data"]["slots"]
        if slot["starts_at"] == "2026-09-27T16:00:00+05:30"
    )
    assert slot["ends_at"] == "2026-09-27T16:30:00+05:30"
    assert slot["available"] is False


def test_expired_pending_booking_does_not_block_slot():
    appointment_date = date(2026, 9, 27)
    center_test_id = uuid4()
    session_context = MagicMock()
    session_context.__enter__.return_value = MagicMock()
    service = ScheduleService()
    service.center_test_repository.get_by_id = MagicMock(
        return_value=SimpleNamespace(
            is_active=True,
            center=SimpleNamespace(opening_time=time(9, 0), closing_time=time(10, 0)),
        )
    )
    service.schedule_repository.get_for_center_test_on_date = MagicMock(
        return_value=[
            SimpleNamespace(
                starts_at=real_datetime(
                    2026,
                    9,
                    27,
                    9,
                    0,
                    tzinfo=timezone(timedelta(hours=5, minutes=30)),
                ),
                status="PENDING",
                booking=SimpleNamespace(
                    status="PENDING",
                    expires_at=real_datetime(
                        2026, 9, 26, 0, 0, tzinfo=timezone.utc
                    ),
                ),
            )
        ]
    )

    with patch("services.schedule_service.SessionLocal", return_value=session_context):
        with patch("services.schedule_service.datetime") as datetime_mock:
            datetime_mock.now.return_value = real_datetime(
                2026, 9, 26, 9, 31, tzinfo=timezone.utc
            )
            datetime_mock.combine.side_effect = real_datetime.combine
            response = service.get_available_schedules(
                center_test_id=center_test_id,
                appointment_date=appointment_date,
            )

    slot = next(
        slot
        for slot in response["data"]["slots"]
        if slot["starts_at"] == "2026-09-27T09:00:00+05:30"
    )
    assert slot["available"] is True