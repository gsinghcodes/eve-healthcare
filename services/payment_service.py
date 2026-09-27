# services/payment/payment_service.py

import logging
import uuid
from datetime import datetime, timezone

from database.models.booking_model import BookingStatus
from database.models.schedule_model import ScheduleStatus
from database.models.payment_model import PaymentStatus
from database.session import SessionLocal
from database.repositories.booking_repo import BookingRepository
from database.repositories.webhook_event_repo import WebhookEventRepository
from database.repositories.payment_repo import PaymentRepository
from database.repositories.schedule_repo import ScheduleRepository
from utils.model_utils import serialize_model
from utils.responses import send_response

logger = logging.getLogger(__name__)


class PaymentService:

    def __init__(self):
        self.payment_repository = PaymentRepository()
        self.booking_repository = BookingRepository()
        self.schedule_repository = ScheduleRepository()
        self.webhook_event_repository = WebhookEventRepository()

    def create_payment(
        self,
        booking_id,
        user_id,
        payment_method=None,
    ):
        with SessionLocal() as session:
            try:
                booking = self.booking_repository.get_by_id(
                    booking_id=booking_id,
                    session=session,
                )

                if not booking:
                    logger.warning(
                        "Payment rejected: booking not found booking_id=%s",
                        booking_id,
                    )
                    return send_response(
                        data=None,
                        status_code=404,
                        message="Booking not found",
                    )

                if booking.user_id != user_id:
                    logger.warning(
                        "Payment rejected: booking ownership mismatch "
                        "booking_id=%s user_id=%s",
                        booking_id,
                        user_id,
                    )
                    return send_response(
                        data=None,
                        status_code=404,
                        message="Booking not found",
                    )

                schedule = self.schedule_repository.get_by_id_for_update(
                    schedule_id=booking.schedule_id,
                    session=session,
                )
                booking = self.booking_repository.get_by_id_for_update(
                    booking_id=booking.id,
                    session=session,
                )

                if booking.status == BookingStatus.CONFIRMED.value:
                    logger.warning(
                        "Payment rejected: booking already paid booking_id=%s",
                        booking_id,
                    )
                    return send_response(
                        data=None,
                        status_code=400,
                        message="Booking has already been paid",
                    )

                if booking.status != BookingStatus.PENDING.value:
                    logger.warning(
                        "Payment rejected: booking not payable booking_id=%s "
                        "booking_status=%s",
                        booking_id,
                        booking.status,
                    )
                    return send_response(
                        data=None,
                        status_code=400,
                        message="Payment cannot be made for this booking",
                    )

                if booking.expires_at <= datetime.now(timezone.utc):
                    booking.status = BookingStatus.EXPIRED.value
                    if schedule and schedule.status == ScheduleStatus.PENDING.value:
                        schedule.status = ScheduleStatus.CANCELLED.value
                    session.commit()
                    logger.warning(
                        "Payment rejected: booking expired booking_id=%s",
                        booking_id,
                    )
                    return send_response(
                        data=None,
                        status_code=400,
                        message="Payment window has expired",
                    )

                active_payment = self.payment_repository.get_pending_for_booking(
                    booking_id=booking.id,
                    session=session,
                )
                if active_payment:
                    return send_response(
                        data=None,
                        status_code=409,
                        message="A payment is already pending for this booking",
                    )

                provider_payment_id = f"MOCK_{uuid.uuid4()}"

                payment = self.payment_repository.create(
                    booking_id=booking.id,
                    provider="MOCK",
                    provider_payment_id=provider_payment_id,
                    amount=booking.amount,
                    status=PaymentStatus.PENDING.value,
                    payment_method=payment_method,
                    session=session,
                )

                session.commit()
                session.refresh(payment)
                logger.info(
                    "Payment initiated: payment_id=%s booking_id=%s",
                    payment.id,
                    booking.id,
                )

                return send_response(
                    data=serialize_model(payment),
                    status_code=201,
                    message="Payment initiated; awaiting payment confirmation",
                )

            except Exception as e:
                session.rollback()
                logger.error(
                    "Payment initiation failed: booking_id=%s error_type=%s",
                    booking_id,
                    type(e).__name__,
                )

                return send_response(
                    data=None,
                    status_code=500,
                    message="Failed to process payment",
                    error=str(e),
                )

    def process_webhook(
        self,
        event_id,
        event_type,
        provider_payment_id,
        status,
        payload,
    ):
        with SessionLocal() as session:
            try:
                response = self._process_webhook_in_session(
                    session=session,
                    event_id=event_id,
                    provider_payment_id=provider_payment_id,
                    event_type=event_type,
                    status=status,
                    payload=payload,
                )

                if response["status"] == 200:
                    session.commit()
                else:
                    session.rollback()

                return response

            except Exception as e:
                session.rollback()
                logger.error(
                    "Payment webhook failed: event_id=%s error_type=%s",
                    event_id,
                    type(e).__name__,
                )

                return send_response(
                    data=None,
                    status_code=500,
                    message="Failed to process payment webhook",
                    error=str(e),
                )

    def _process_webhook_in_session(
        self,
        session,
        event_id,
        event_type,
        provider_payment_id,
        status,
        payload,
    ):
        existing_event = self.webhook_event_repository.get_by_event_id(
            event_id=event_id,
            session=session,
        )

        if existing_event:
            logger.info("Duplicate payment webhook ignored: event_id=%s", event_id)
            return send_response(
                data=None,
                status_code=200,
                message="Webhook already processed",
            )

        if status not in {
            PaymentStatus.SUCCESS.value,
            PaymentStatus.FAILED.value,
        }:
            logger.warning(
                "Payment webhook rejected: invalid status event_id=%s status=%s",
                event_id,
                status,
            )
            return send_response(
                data=None,
                status_code=400,
                message="Invalid payment status",
            )

        expected_event_type = (
            "payment.succeeded"
            if status == PaymentStatus.SUCCESS.value
            else "payment.failed"
        )
        if event_type != expected_event_type:
            logger.warning(
                "Payment webhook rejected: event type mismatch event_id=%s "
                "status=%s",
                event_id,
                status,
            )
            return send_response(
                data=None,
                status_code=400,
                message="Webhook event does not match payment status",
            )

        payment = self.payment_repository.get_by_provider_payment_id(
            provider_payment_id=provider_payment_id,
            session=session,
        )
        if not payment:
            logger.warning(
                "Payment webhook rejected: payment not found event_id=%s",
                event_id,
            )
            return send_response(
                data=None,
                status_code=404,
                message="Payment not found",
            )

        booking = self.booking_repository.get_by_id(
            booking_id=payment.booking_id,
            session=session,
        )
        if not booking:
            logger.error(
                "Payment webhook references missing booking: payment_id=%s "
                "booking_id=%s",
                payment.id,
                payment.booking_id,
            )
            return send_response(
                data=None,
                status_code=404,
                message="Booking not found",
            )

        schedule = self.schedule_repository.get_by_id_for_update(
            schedule_id=booking.schedule_id,
            session=session,
        )
        booking = self.booking_repository.get_by_id_for_update(
            booking_id=booking.id,
            session=session,
        )
        if not booking:
            logger.error(
                "Payment webhook booking disappeared during update: "
                "payment_id=%s booking_id=%s",
                payment.id,
                payment.booking_id,
            )
            return send_response(
                data=None,
                status_code=404,
                message="Booking not found",
            )

        payment = self.payment_repository.get_by_provider_payment_id_for_update(
            provider_payment_id=provider_payment_id,
            session=session,
        )
        if not payment:
            logger.warning(
                "Payment webhook rejected: payment disappeared event_id=%s",
                event_id,
            )
            return send_response(
                data=None,
                status_code=404,
                message="Payment not found",
            )

        if payment.status != PaymentStatus.PENDING.value:
            if payment.status == status:
                logger.info(
                    "Repeated payment status ignored: event_id=%s payment_id=%s",
                    event_id,
                    payment.id,
                )
                return send_response(
                    data=None,
                    status_code=200,
                    message="Payment already has this status",
                )
            logger.warning(
                "Contradictory payment webhook rejected: event_id=%s "
                "payment_id=%s current_status=%s requested_status=%s",
                event_id,
                payment.id,
                payment.status,
                status,
            )
            return send_response(
                data=None,
                status_code=409,
                message="Payment has already reached a different final status",
            )

        webhook_event = self.webhook_event_repository.create(
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            session=session,
        )
        self.payment_repository.update_status(
            payment=payment,
            status=status,
            session=session,
        )

        now_utc = datetime.now(timezone.utc)
        booking_expired = (
            booking.status == BookingStatus.PENDING.value
            and booking.expires_at <= now_utc
        )

        if status == PaymentStatus.SUCCESS.value:
            if booking_expired:
                booking.status = BookingStatus.EXPIRED.value
                if schedule and schedule.status == ScheduleStatus.PENDING.value:
                    schedule.status = ScheduleStatus.CANCELLED.value
            elif booking.status == BookingStatus.PENDING.value:
                booking.status = BookingStatus.CONFIRMED.value
                if schedule:
                    schedule.status = ScheduleStatus.CONFIRMED.value
        elif booking_expired:
            booking.status = BookingStatus.EXPIRED.value
            if schedule and schedule.status == ScheduleStatus.PENDING.value:
                schedule.status = ScheduleStatus.CANCELLED.value
        elif booking.status == BookingStatus.PENDING.value:
            booking.status = BookingStatus.FAILED.value
            if schedule and schedule.status == ScheduleStatus.PENDING.value:
                schedule.status = ScheduleStatus.CANCELLED.value

        self.webhook_event_repository.mark_processed(
            event=webhook_event,
            session=session,
        )
        logger.info(
            "Payment webhook applied: event_id=%s payment_id=%s booking_id=%s "
            "payment_status=%s booking_status=%s",
            event_id,
            payment.id,
            booking.id,
            payment.status,
            booking.status,
        )

        return send_response(
            data={
                "payment_id": str(payment.id),
                "booking_id": str(booking.id),
                "status": payment.status,
            },
            status_code=200,
            message=(
                "Payment succeeded after the booking expired"
                if status == PaymentStatus.SUCCESS.value
                and booking.status == BookingStatus.EXPIRED.value
                else "Payment webhook processed successfully"
            ),
        )
