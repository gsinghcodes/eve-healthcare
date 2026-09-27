from datetime import datetime, time, timedelta, timezone
import logging
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from core.config import settings
from database.models.booking_model import BookingStatus
from database.models.payment_model import PaymentStatus
from database.models.schedule_model import ScheduleStatus
from database.repositories.booking_repo import BookingRepository
from database.repositories.center_test_repo import CenterTestRepository
from database.repositories.payment_repo import PaymentRepository
from database.repositories.schedule_repo import ScheduleRepository
from database.session import SessionLocal
from utils.model_utils import serialize_model
from utils.responses import send_response

logger = logging.getLogger(__name__)


class BookingService:

    SLOT_DURATION = timedelta(minutes=30)
    IST = timezone(timedelta(hours=5, minutes=30))
    ACTIVE_BOOKING_STATUSES = {
        BookingStatus.PENDING.value,
        BookingStatus.CONFIRMED.value,
    }
    CANCELLABLE_BOOKING_STATUSES = ACTIVE_BOOKING_STATUSES | {
        BookingStatus.RESCHEDULED.value,
    }
    REFUND_CUTOFF = timedelta(days=1)

    def __init__(self):
        self.booking_repository = BookingRepository()
        self.center_test_repository = CenterTestRepository()
        self.payment_repository = PaymentRepository()
        self.schedule_repository = ScheduleRepository()

    def create_booking(
        self,
        user_id: UUID,
        center_test_id: UUID,
        appointment_date,
        time_slot: time,
    ):
        with SessionLocal() as session:
            try:
                appointment_at = datetime.combine(
                    appointment_date,
                    time_slot,
                    tzinfo=self.IST,
                ).astimezone(timezone.utc)
                if appointment_at <= datetime.now(timezone.utc):
                    logger.warning(
                        "Booking rejected: appointment is not in the future "
                        "user_id=%s center_test_id=%s",
                        user_id,
                        center_test_id,
                    )
                    return send_response(
                        data=None,
                        status_code=400,
                        message="Appointment time must be in the future",
                    )

                center_test = self.center_test_repository.get_by_id(
                    center_test_id=center_test_id,
                    session=session,
                )

                if not center_test:
                    logger.warning(
                        "Booking rejected: diagnostic test not found "
                        "user_id=%s center_test_id=%s",
                        user_id,
                        center_test_id,
                    )
                    return send_response(
                        data=None,
                        status_code=404,
                        message="Diagnostic test is not available",
                    )

                if not center_test.is_active:
                    logger.warning(
                        "Booking rejected: diagnostic test inactive "
                        "user_id=%s center_test_id=%s",
                        user_id,
                        center_test_id,
                    )
                    return send_response(
                        data=None,
                        status_code=400,
                        message="Diagnostic test is no longer available at this center",
                    )

                appointment_local = datetime.combine(appointment_date, time_slot)
                opening_at = datetime.combine(
                    appointment_date,
                    center_test.center.opening_time,
                )
                closing_at = datetime.combine(
                    appointment_date,
                    center_test.center.closing_time,
                )
                slot_offset = appointment_local - opening_at
                if (
                    appointment_local < opening_at
                    or appointment_local + self.SLOT_DURATION > closing_at
                    or slot_offset % self.SLOT_DURATION != timedelta(0)
                ):
                    logger.warning(
                        "Booking rejected: appointment outside center hours "
                        "or slot cadence user_id=%s center_test_id=%s",
                        user_id,
                        center_test_id,
                    )
                    return send_response(
                        data=None,
                        status_code=400,
                        message=(
                            "Appointment time is outside the center's operating "
                            "hours or does not match an available slot"
                        ),
                    )

                schedule = self.schedule_repository.get_by_slot_for_update(
                    center_test_id=center_test_id,
                    starts_at=appointment_at,
                    session=session,
                )

                now_utc = datetime.now(timezone.utc)
                if schedule:
                    existing_booking = (
                        self.booking_repository.get_by_schedule_for_update(
                            schedule_id=schedule.id,
                            session=session,
                        )
                    )
                    if (
                        schedule.status == ScheduleStatus.CONFIRMED.value
                        or (
                            existing_booking
                            and existing_booking.status == BookingStatus.CONFIRMED.value
                        )
                        or (
                            existing_booking
                            and existing_booking.status == BookingStatus.PENDING.value
                            and existing_booking.expires_at > now_utc
                        )
                    ):
                        session.rollback()
                        logger.warning(
                            "Booking rejected: schedule already booked "
                            "user_id=%s schedule_id=%s",
                            user_id,
                            schedule.id,
                        )
                        return send_response(
                            data=None,
                            status_code=409,
                            message="A booking already exists for this schedule",
                        )

                    if (
                        existing_booking
                        and existing_booking.status == BookingStatus.PENDING.value
                    ):
                        existing_booking.status = BookingStatus.EXPIRED.value
                    schedule.status = ScheduleStatus.CANCELLED.value
                    session.flush()

                schedule = self.schedule_repository.create(
                    center_test_id=center_test_id,
                    starts_at=appointment_at,
                    ends_at=appointment_at + self.SLOT_DURATION,
                    session=session,
                )

                booking = self.booking_repository.create(
                    user_id=user_id,
                    schedule_id=schedule.id,
                    amount=center_test.price,
                    expires_at=now_utc
                    + timedelta(minutes=settings.BOOKING_PAYMENT_TIMEOUT_MINUTES),
                    session=session,
                )

                session.commit()
                session.refresh(booking)
                logger.info(
                    "Booking created: booking_id=%s user_id=%s schedule_id=%s",
                    booking.id,
                    user_id,
                    schedule.id,
                )

                return send_response(
                    data=serialize_model(booking),
                    status_code=201,
                    message="Booking created successfully",
                )

            except IntegrityError:
                session.rollback()
                logger.warning(
                    "Booking rejected: schedule conflict user_id=%s "
                    "center_test_id=%s",
                    user_id,
                    center_test_id,
                )
                return send_response(
                    data=None,
                    status_code=409,
                    message="A booking already exists for this schedule",
                )
            except Exception as error:
                session.rollback()
                logger.error(
                    "Booking creation failed: user_id=%s center_test_id=%s "
                    "error_type=%s",
                    user_id,
                    center_test_id,
                    type(error).__name__,
                )

                return send_response(
                    data=None,
                    status_code=500,
                    message="Failed to create booking",
                )

    def get_user_bookings(self, user_id: UUID):
        with SessionLocal() as session:
            try:
                bookings = self.booking_repository.get_user_bookings(
                    user_id=user_id,
                    session=session,
                )
                logger.info(
                    "Bookings retrieved: user_id=%s count=%s",
                    user_id,
                    len(bookings),
                )
                return send_response(
                    data=[serialize_model(booking) for booking in bookings],
                    status_code=200,
                    message="Bookings retrieved successfully",
                )
            except Exception as error:
                logger.error(
                    "Booking retrieval failed: user_id=%s error_type=%s",
                    user_id,
                    type(error).__name__,
                )
                return send_response(
                    data=None,
                    status_code=500,
                    message="Failed to retrieve bookings",
                )

    def reschedule_booking(
        self,
        booking_id: UUID,
        user_id: UUID,
        appointment_date,
        time_slot: time,
    ):
        appointment_at = datetime.combine(
            appointment_date,
            time_slot,
            tzinfo=self.IST,
        ).astimezone(timezone.utc)
        now_utc = datetime.now(timezone.utc)
        if appointment_at <= now_utc:
            return send_response(
                data=None,
                status_code=400,
                message="Appointment time must be in the future",
            )

        with SessionLocal() as session:
            try:
                initial_booking = self.booking_repository.get_by_id(
                    booking_id=booking_id,
                    session=session,
                )
                if not initial_booking or initial_booking.user_id != user_id:
                    return send_response(
                        data=None,
                        status_code=404,
                        message="Booking not found",
                    )

                old_schedule = self.schedule_repository.get_by_id_for_update(
                    schedule_id=initial_booking.schedule_id,
                    session=session,
                )
                booking = self.booking_repository.get_by_id_for_update(
                    booking_id=booking_id,
                    session=session,
                )
                if (
                    not booking
                    or booking.user_id != user_id
                    or booking.schedule_id != initial_booking.schedule_id
                ):
                    session.rollback()
                    return send_response(
                        data=None,
                        status_code=409,
                        message="Booking changed; retry the request",
                    )

                if booking.status not in self.ACTIVE_BOOKING_STATUSES:
                    return send_response(
                        data=None,
                        status_code=400,
                        message="This booking cannot be rescheduled",
                    )

                if not old_schedule:
                    return send_response(
                        data=None,
                        status_code=404,
                        message="Booking schedule not found",
                    )

                if old_schedule.starts_at == appointment_at:
                    return send_response(
                        data=None,
                        status_code=400,
                        message="New appointment must differ from the current appointment",
                    )

                if (
                    booking.status == BookingStatus.PENDING.value
                    and booking.expires_at <= now_utc
                ):
                    booking.status = BookingStatus.EXPIRED.value
                    old_schedule.status = ScheduleStatus.CANCELLED.value
                    session.commit()
                    return send_response(
                        data=None,
                        status_code=400,
                        message="Payment window has expired",
                    )

                center_test = self.center_test_repository.get_by_id(
                    center_test_id=old_schedule.center_test_id,
                    session=session,
                )
                if not center_test or not center_test.is_active:
                    return send_response(
                        data=None,
                        status_code=400,
                        message="Diagnostic test is no longer available at this center",
                    )

                local_start = appointment_at.astimezone(self.IST)
                local_end = (appointment_at + self.SLOT_DURATION).astimezone(self.IST)
                if (
                    local_start.time() < center_test.center.opening_time
                    or local_end.time() > center_test.center.closing_time
                ):
                    return send_response(
                        data=None,
                        status_code=400,
                        message="Appointment time is outside the center's operating hours",
                    )

                target_schedule = self.schedule_repository.get_by_slot_for_update(
                    center_test_id=old_schedule.center_test_id,
                    starts_at=appointment_at,
                    session=session,
                )
                if target_schedule:
                    existing_booking = (
                        self.booking_repository.get_by_schedule_for_update(
                            schedule_id=target_schedule.id,
                            session=session,
                        )
                    )
                    target_pending_is_active = (
                        existing_booking
                        and existing_booking.status == BookingStatus.PENDING.value
                        and existing_booking.expires_at > now_utc
                    )
                    if (
                        target_schedule.status == ScheduleStatus.CONFIRMED.value
                        or (
                            existing_booking
                            and existing_booking.status == BookingStatus.CONFIRMED.value
                        )
                        or target_pending_is_active
                    ):
                        session.rollback()
                        return send_response(
                            data=None,
                            status_code=409,
                            message="A booking already exists for this schedule",
                        )

                    if (
                        existing_booking
                        and existing_booking.status == BookingStatus.PENDING.value
                    ):
                        existing_booking.status = BookingStatus.EXPIRED.value
                    target_schedule.status = ScheduleStatus.CANCELLED.value
                    session.flush()

                old_schedule.status = ScheduleStatus.RESCHEDULED.value
                new_schedule = self.schedule_repository.create(
                    center_test_id=old_schedule.center_test_id,
                    starts_at=appointment_at,
                    ends_at=appointment_at + self.SLOT_DURATION,
                    session=session,
                )
                new_schedule.status = (
                    ScheduleStatus.CONFIRMED.value
                    if booking.status == BookingStatus.CONFIRMED.value
                    else ScheduleStatus.PENDING.value
                )
                booking.schedule_id = new_schedule.id

                session.commit()
                session.refresh(booking)
                logger.info(
                    "Booking rescheduled: booking_id=%s user_id=%s schedule_id=%s",
                    booking_id,
                    user_id,
                    new_schedule.id,
                )
                return send_response(
                    data=serialize_model(booking),
                    status_code=200,
                    message="Booking rescheduled successfully",
                )
            except IntegrityError:
                session.rollback()
                return send_response(
                    data=None,
                    status_code=409,
                    message="A booking already exists for this schedule",
                )
            except Exception as error:
                session.rollback()
                logger.error(
                    "Booking reschedule failed: booking_id=%s error_type=%s",
                    booking_id,
                    type(error).__name__,
                )
                return send_response(
                    data=None,
                    status_code=500,
                    message="Failed to reschedule booking",
                )

    def cancel_booking(self, booking_id: UUID, user_id: UUID):
        with SessionLocal() as session:
            try:
                initial_booking = self.booking_repository.get_by_id(
                    booking_id=booking_id,
                    session=session,
                )
                if not initial_booking or initial_booking.user_id != user_id:
                    return send_response(
                        data=None,
                        status_code=404,
                        message="Booking not found",
                    )

                schedule = self.schedule_repository.get_by_id_for_update(
                    schedule_id=initial_booking.schedule_id,
                    session=session,
                )
                if schedule is None:
                    logger.error(
                        "Booking references missing schedule: booking_id=%s "
                        "schedule_id=%s",
                        booking_id,
                        initial_booking.schedule_id,
                    )
                    return send_response(
                        data=None,
                        status_code=404,
                        message="Booking schedule not found",
                    )

                booking = self.booking_repository.get_by_id_for_update(
                    booking_id=booking_id,
                    session=session,
                )
                if (
                    not booking
                    or booking.user_id != user_id
                    or booking.schedule_id != initial_booking.schedule_id
                ):
                    session.rollback()
                    return send_response(
                        data=None,
                        status_code=409,
                        message="Booking changed; retry the request",
                    )

                if booking.status not in self.CANCELLABLE_BOOKING_STATUSES:
                    return send_response(
                        data=None,
                        status_code=400,
                        message="This booking cannot be cancelled",
                    )

                refund_issued = False
                now_utc = datetime.now(timezone.utc)
                if (
                    schedule
                    and schedule.starts_at - now_utc >= self.REFUND_CUTOFF
                ):
                    successful_payments = (
                        self.payment_repository.get_successful_for_booking_for_update(
                            booking_id=booking.id,
                            session=session,
                        )
                    )
                    for payment in successful_payments:
                        self.payment_repository.update_status(
                            payment=payment,
                            status=PaymentStatus.REFUNDED.value,
                            session=session,
                        )
                    refund_issued = bool(successful_payments)

                booking.status = BookingStatus.CANCELLED.value
                if schedule:
                    schedule.status = ScheduleStatus.CANCELLED.value

                session.commit()
                session.refresh(booking)
                logger.info(
                    "Booking cancelled: booking_id=%s user_id=%s",
                    booking_id,
                    user_id,
                )
                message = (
                    "Booking cancelled successfully; refund issued"
                    if refund_issued
                    else "Booking cancelled successfully"
                )
                return send_response(
                    data=serialize_model(booking),
                    status_code=200,
                    message=message,
                )
            except Exception as error:
                session.rollback()
                logger.error(
                    "Booking cancellation failed: booking_id=%s error_type=%s",
                    booking_id,
                    type(error).__name__,
                )
                return send_response(
                    data=None,
                    status_code=500,
                    message="Failed to cancel booking",
                )
