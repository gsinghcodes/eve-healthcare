from datetime import time
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text, Float, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from database.models.base_model import BaseModel
from database.models.date_time_model import DateTimeMixin


class DiagnosticCenter(BaseModel, DateTimeMixin):
    __tablename__ = "diagnostic_centers"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    address: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    latitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    longitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    opening_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        default=time(9, 0),
    )

    closing_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        default=time(17, 0),
    )

    geohash: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    owner_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    owner: Mapped["User | None"] = relationship(
        "User",
        back_populates="managed_centers",
    )

    center_tests: Mapped[list["CenterTest"]] = relationship(
        "CenterTest",
        back_populates="center",
        cascade="all, delete-orphan",
    )
