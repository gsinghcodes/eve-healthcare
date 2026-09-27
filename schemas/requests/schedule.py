from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, model_validator


class CreateScheduleRequest(BaseModel):
    center_test_id: UUID
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.starts_at.tzinfo is None or self.starts_at.utcoffset() is None:
            raise ValueError("starts_at must include a timezone")
        if self.ends_at.tzinfo is None or self.ends_at.utcoffset() is None:
            raise ValueError("ends_at must include a timezone")
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self