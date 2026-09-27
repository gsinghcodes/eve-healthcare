from datetime import time

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator
from typing import Literal, Optional


class CreateCenterRequest(BaseModel):
    name: str
    address: str
    latitude: float
    longitude: float
    opening_time: time = time(9, 0)
    closing_time: time = time(17, 0)

    @model_validator(mode="after")
    def validate_operating_hours(self):
        if (
            self.opening_time is not None
            and self.closing_time is not None
            and self.opening_time >= self.closing_time
        ):
            raise ValueError("opening_time must be earlier than closing_time")
        return self


class UpdateCenterRequest(CreateCenterRequest):
    name: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None


class SearchCentersRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius: float = Field(gt=0, le=20000, description="Search radius in kilometres")
    test_id: Optional[str] = None
    sort_by: Literal["distance", "test_price"] = "distance"
    sort_order: Literal["asc", "desc"] = "asc"
    view: Literal["list", "map"] = "list"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
