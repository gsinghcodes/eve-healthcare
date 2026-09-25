from uuid import UUID, uuid4
from decimal import Decimal
from enum import Enum

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from database.models.base_model import BaseModel
from database.models.date_time_model import DateTimeMixin


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Payment(BaseModel, DateTimeMixin):
    __tablename__ = "payments"

    __table_args__ = (
        UniqueConstraint(
            "provider_payment_id",
            name="uq_provider_payment_id",
        ),
        CheckConstraint("amount >= 0", name="ck_payment_amount_non_negative"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    booking_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    provider_payment_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    status: Mapped[PaymentStatus] = mapped_column(
        String(20),
        nullable=False,
        default=PaymentStatus.PENDING,
        index=True,
    )

    payment_method: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    booking: Mapped["Booking"] = relationship(
        "Booking",
        back_populates="payments",
    )
