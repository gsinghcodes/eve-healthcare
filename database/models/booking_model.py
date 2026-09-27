from datetime import datetime
from uuid import UUID, uuid4
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    ForeignKey,
    Numeric,
    String,
    CheckConstraint,
    UniqueConstraint,
    DateTime,
)
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from database.models.base_model import BaseModel
from database.models.date_time_model import DateTimeMixin

if TYPE_CHECKING:
    from database.models.payment_model import Payment
    from database.models.schedule_model import Schedule
    from database.models.user_model import User


class BookingStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    RESCHEDULED = "RESCHEDULED"


class Booking(BaseModel, DateTimeMixin):
    __tablename__ = "bookings"

    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_booking_amount_non_negative"),
        UniqueConstraint("schedule_id", name="uq_booking_schedule"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    schedule_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("schedules.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    status: Mapped[BookingStatus] = mapped_column(
        String(20),
        nullable=False,
        default=BookingStatus.PENDING,
        index=True,
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="bookings",
    )

    schedule: Mapped["Schedule"] = relationship(
        "Schedule",
        back_populates="booking",
    )

    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="booking",
        cascade="all, delete-orphan",
    )
