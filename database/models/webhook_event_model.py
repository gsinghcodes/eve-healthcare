from uuid import UUID, uuid4
from datetime import datetime

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.postgresql import JSONB

from database.models.base_model import BaseModel
from database.models.date_time_model import DateTimeMixin


class WebhookEvent(BaseModel, DateTimeMixin):
    __tablename__ = "webhook_events"

    __table_args__ = (
        UniqueConstraint(
            "event_id",
            name="uq_webhook_event_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    event_id: Mapped[str] = mapped_column(String(255), nullable=False)

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    processed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
