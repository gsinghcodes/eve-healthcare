from decimal import Decimal
from uuid import UUID
from typing import Optional
from pydantic import BaseModel


class CreateCenterTestRequest(BaseModel):
    test_id: UUID
    price: Decimal
    title_override: Optional[str] = None
    description_override: Optional[str] = None
    image_url_override: Optional[str] = None


class UpdateCenterTestRequest(BaseModel):
    price: Decimal
    title_override: Optional[str] = None
    description_override: Optional[str] = None
    image_url_override: Optional[str] = None
    is_active: bool = True
