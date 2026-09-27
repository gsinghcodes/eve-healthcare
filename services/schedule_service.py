from datetime import date, datetime, time, timedelta, timezone
import logging
from uuid import UUID
from zoneinfo import ZoneInfo

from database.repositories.center_test_repo import CenterTestRepository
from database.repositories.schedule_repo import ScheduleRepository
from database.models.booking_model import BookingStatus
from database.models.schedule_model import ScheduleStatus
from database.session import SessionLocal
from utils.responses import send_response

logger = logging.getLogger(__name__)


class ScheduleService:

    IST = ZoneInfo("Asia/Kolkata")
    SLOT_DURATION = timedelta(minutes=30)

    def __init__(self):
        self.center_test_repository = CenterTestRepository()
        self.schedule_repository = ScheduleRepository()

    def get_available_schedules(
        self,
        center_test_id: UUID,
        appointment_date: date,
    ):
        now_utc = datetime.now(timezone.utc)
        now = now_utc.astimezone(self.IST)
        today = now.date()
        if appointment_date < today:
            logger.warning(
                "Schedule lookup rejected: appointment date is in the past "
                "center_test_id=%s date=%s",
                center_test_id,
                appointment_date,
            )
            return send_response(
                data=None,
                status_code=400,
                message="Appointment date must not be in the past",
            )

        try:
            with SessionLocal() as session:
                center_test = self.center_test_repository.get_by_id(
                    center_test_id=center_test_id,
                    session=session,
                )
                if not center_test:
                    logger.warning(
                        "Schedule lookup rejected: center test not found "
                        "center_test_id=%s",
                        center_test_id,
                    )
                    return send_response(
                        data=None,
                        status_code=404,
                        message="Diagnostic test is not available",
                    )

                if not center_test.is_active:
                    logger.warning(
                        "Schedule lookup rejected: center test inactive "
                        "center_test_id=%s",
                        center_test_id,
                    )
                    return send_response(
                        data=None,
                        status_code=400,
                        message="Diagnostic test is no longer available at this center",
                    )

                opening_time = center_test.center.opening_time
                closing_time = center_test.center.closing_time
                day_start = datetime.combine(
                    appointment_date,
                    opening_time,
                    tzinfo=self.IST,
                )
                day_end = datetime.combine(
                    appointment_date,
                    closing_time,
                    tzinfo=self.IST,
                )
                existing_schedules = self.schedule_repository.get_for_center_test_on_date(
                    center_test_id=center_test_id,
                    starts_at=day_start,
                    ends_at=day_end,
                    session=session,
                )
                occupied_starts = set()
                for schedule in existing_schedules:
                    booking = getattr(schedule, "booking", None)
                    booking_status = getattr(booking, "status", None)
                    expires_at = getattr(booking, "expires_at", None)
                    if (
                        schedule.status == ScheduleStatus.CONFIRMED.value
                        or booking_status == BookingStatus.CONFIRMED.value
                        or (
                            booking_status == BookingStatus.PENDING.value
                            and expires_at is not None
                            and expires_at > now_utc
                        )
                    ):
                        occupied_starts.add(schedule.starts_at)
                slots = []
                current = day_start
                while current + self.SLOT_DURATION <= day_end:
                    if appointment_date == today and current <= now:
                        current += self.SLOT_DURATION
                        continue
                    occupied = current in occupied_starts
                    slots.append(
                        {
                            "starts_at": current.isoformat(),
                            "ends_at": (current + self.SLOT_DURATION).isoformat(),
                            "available": not occupied,
                        }
                    )
                    current += self.SLOT_DURATION

                available_count = sum(slot["available"] for slot in slots)
                logger.info(
                    "Schedule lookup completed: center_test_id=%s date=%s "
                    "available=%s total=%s",
                    center_test_id,
                    appointment_date,
                    available_count,
                    len(slots),
                )
                return send_response(
                    data={
                        "center_test_id": str(center_test_id),
                        "date": appointment_date.isoformat(),
                        "timezone": "IST",
                        "slots": slots,
                    },
                    status_code=200,
                    message="Available schedules fetched successfully",
                )
        except Exception as error:
            logger.error(
                "Schedule lookup failed: center_test_id=%s date=%s "
                "error_type=%s",
                center_test_id,
                appointment_date,
                type(error).__name__,
            )
            return send_response(
                data=None,
                status_code=500,
                message="Failed to fetch available schedules",
            )
