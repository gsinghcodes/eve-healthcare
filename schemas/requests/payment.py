from uuid import UUID
from typing import Optional
from pydantic import BaseModel


class CreatePaymentRequest(BaseModel):
    booking_id: UUID
    payment_method: Optional[str] = None


class PaymentWebhookRequest(BaseModel):
    event_id: str
    event_type: str
    provider_payment_id: str
    status: str
