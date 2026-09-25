from uuid import UUID, uuid4

from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from database.models.base_model import BaseModel
from database.models.date_time_model import DateTimeMixin


class DiagnosticTest(BaseModel, DateTimeMixin):
    __tablename__ = "tests"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    is_global: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    center_tests: Mapped[list["CenterTest"]] = relationship(
        "CenterTest",
        back_populates="test",
        cascade="all, delete-orphan",
    )
