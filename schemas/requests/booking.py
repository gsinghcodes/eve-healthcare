from datetime import date, time
from uuid import UUID

from pydantic import BaseModel, field_validator


class CreateBookingRequest(BaseModel):
    center_test_id: UUID
    appointment_date: date
    time_slot: time

    @field_validator("time_slot")
    @classmethod
    def validate_time_slot(cls, value: time) -> time:
        if value.second or value.microsecond or value.minute not in {0, 30}:
            raise ValueError("time_slot must be aligned to a 30-minute slot")
        return value


class RescheduleBookingRequest(BaseModel):
    appointment_date: date
    time_slot: time

    @field_validator("time_slot")
    @classmethod
    def validate_time_slot(cls, value: time) -> time:
        if value.second or value.microsecond or value.minute not in {0, 30}:
            raise ValueError("time_slot must be aligned to a 30-minute slot")
        return value
