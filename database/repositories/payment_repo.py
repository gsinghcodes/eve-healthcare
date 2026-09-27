from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.payment_model import Payment
from database.models.payment_model import PaymentStatus


class PaymentRepository:

    def get_by_id(
        self,
        payment_id: UUID,
        session: Session,
    ) -> Optional[Payment]:
        stmt = select(Payment).where(Payment.id == payment_id)

        return session.scalar(stmt)

    def get_by_provider_payment_id(
        self,
        provider_payment_id: str,
        session: Session,
    ) -> Optional[Payment]:
        stmt = select(Payment).where(Payment.provider_payment_id == provider_payment_id)

        return session.scalar(stmt)

    def get_by_provider_payment_id_for_update(
        self,
        provider_payment_id: str,
        session: Session,
    ) -> Optional[Payment]:
        stmt = (
            select(Payment)
            .where(Payment.provider_payment_id == provider_payment_id)
            .with_for_update()
        )
        return session.scalar(stmt)

    def get_pending_for_booking(
        self,
        booking_id: UUID,
        session: Session,
    ) -> Optional[Payment]:
        stmt = select(Payment).where(
            Payment.booking_id == booking_id,
            Payment.status == PaymentStatus.PENDING.value,
        )
        return session.scalar(stmt)

    def get_successful_for_booking_for_update(
        self,
        booking_id: UUID,
        session: Session,
    ) -> list[Payment]:
        stmt = (
            select(Payment)
            .where(
                Payment.booking_id == booking_id,
                Payment.status == PaymentStatus.SUCCESS.value,
            )
            .with_for_update()
        )
        return list(session.scalars(stmt).all())

    def create(
        self,
        booking_id: UUID,
        provider: str,
        provider_payment_id: str,
        amount,
        status: str,
        payment_method: Optional[str],
        session: Session,
    ) -> Payment:

        payment = Payment(
            booking_id=booking_id,
            provider=provider,
            provider_payment_id=provider_payment_id,
            amount=amount,
            status=status,
            payment_method=payment_method,
        )

        session.add(payment)
        session.flush()

        return payment

    def update_status(
        self,
        payment: Payment,
        status: str,
        session: Session,
    ) -> Payment:
        current_status = PaymentStatus(payment.status)
        next_status = PaymentStatus(status)
        allowed_transitions = {
            PaymentStatus.PENDING: {
                PaymentStatus.SUCCESS,
                PaymentStatus.FAILED,
            },
            PaymentStatus.SUCCESS: {PaymentStatus.REFUNDED},
            PaymentStatus.FAILED: set(),
            PaymentStatus.REFUNDED: set(),
        }

        if next_status not in allowed_transitions[current_status]:
            raise ValueError(
                f"Invalid payment transition: {current_status.value} -> "
                f"{next_status.value}"
            )

        payment.status = next_status.value
        session.flush()

        return payment
