from uuid import UUID, uuid4
from enum import Enum

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from typing import TYPE_CHECKING

from database.models.base_model import BaseModel
from database.models.date_time_model import DateTimeMixin


class UserRole(str, Enum):
    USER = "user"
    CENTER_MANAGER = "center_manager"
    ADMIN = "admin"


class User(BaseModel, DateTimeMixin):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    phone_number: Mapped[str] = mapped_column(
        String(13),
        unique=True,
        nullable=False,
        index=True,
    )

    first_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    last_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    role: Mapped[UserRole] = mapped_column(
        String(32),
        default=UserRole.USER,
        nullable=False,
    )

    refresh_token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=True,
    )

    otp_verifications: Mapped[list["OTPVerification"]] = relationship(
        "OTPVerification",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    bookings: Mapped[list["Booking"]] = relationship(
        "Booking",
        back_populates="user",
    )

    managed_centers: Mapped[list["DiagnosticCenter"]] = relationship(
        "DiagnosticCenter",
        back_populates="owner",
    )
