from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.functions import current_timestamp
from sqlalchemy import DateTime
from datetime import datetime


class DateTimeMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=current_timestamp(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        onupdate=current_timestamp(),
        server_default=current_timestamp(),
        nullable=False,
    )
