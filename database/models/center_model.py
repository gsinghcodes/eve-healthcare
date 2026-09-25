from uuid import UUID, uuid4

from sqlalchemy import String, Text, Float
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

    geohash: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    center_tests: Mapped[list["CenterTest"]] = relationship(
        "CenterTest",
        back_populates="center",
        cascade="all, delete-orphan",
    )
