from uuid import UUID, uuid4
from decimal import Decimal

from sqlalchemy import (
    ForeignKey,
    String,
    Text,
    Boolean,
    Numeric,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from database.models.base_model import BaseModel
from database.models.date_time_model import DateTimeMixin


class CenterTest(BaseModel, DateTimeMixin):
    __tablename__ = "center_tests"

    __table_args__ = (
        UniqueConstraint(
            "center_id",
            "test_id",
            name="uq_center_test",
        ),
        CheckConstraint("price >= 0", name="ck_center_test_price_non_negative"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    center_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("diagnostic_centers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    test_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    title_override: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    description_override: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    image_url_override: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    center: Mapped["DiagnosticCenter"] = relationship(
        "DiagnosticCenter",
        back_populates="center_tests",
    )

    test: Mapped["DiagnosticTest"] = relationship(
        "DiagnosticTest",
        back_populates="center_tests",
    )

    schedules: Mapped[list["Schedule"]] = relationship(
        "Schedule",
        back_populates="center_test",
        cascade="all, delete-orphan",
    )
