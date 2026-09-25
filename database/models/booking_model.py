from uuid import UUID, uuid4
from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    ForeignKey,
    DateTime,
    Numeric,
    String,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from database.models.base_model import BaseModel
from database.models.date_time_model import DateTimeMixin


class BookingStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    RESCHEDULED = "RESCHEDULED"


class Booking(BaseModel, DateTimeMixin):
    __tablename__ = "bookings"

    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_booking_amount_non_negative"),
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

    center_test_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("center_tests.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    appointment_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
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

    center_test: Mapped["CenterTest"] = relationship(
        "CenterTest",
        back_populates="bookings",
    )

    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="booking",
        cascade="all, delete-orphan",
    )
