from datetime import datetime
from uuid import UUID, uuid4

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base_model import BaseModel
from database.models.date_time_model import DateTimeMixin

if TYPE_CHECKING:
    from database.models.booking_model import Booking
    from database.models.center_test_model import CenterTest


class ScheduleStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    RESCHEDULED = "RESCHEDULED"


class Schedule(BaseModel, DateTimeMixin):
    __tablename__ = "schedules"

    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="ck_schedule_end_after_start"),
        Index(
            "uq_active_schedule_slot",
            "center_test_id",
            "starts_at",
            unique=True,
            postgresql_where="status IN ('PENDING', 'CONFIRMED')",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    center_test_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("center_tests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    ends_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    status: Mapped[ScheduleStatus] = mapped_column(
        String(20),
        nullable=False,
        default=ScheduleStatus.PENDING,
        index=True,
    )

    center_test: Mapped["CenterTest"] = relationship(
        "CenterTest",
        back_populates="schedules",
    )

    booking: Mapped["Booking"] = relationship(
        "Booking",
        back_populates="schedule",
        uselist=False,
    )