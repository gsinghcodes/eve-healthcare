from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from database.models.user_model import User
from routers.middlewares.auth import get_current_user
from schemas.requests.payment import CreatePaymentRequest, PaymentWebhookRequest
from services.payment_service import PaymentService
from core.config import settings
from utils.rate_limiter import RateLimit, check_rate_limits

router = APIRouter(
    prefix="/api/v1/payments",
    tags=["Payments"],
)

payment_service = PaymentService()


def enforce_payment_limit(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> None:
    check_rate_limits(
        request.app.state.redis,
        [
            RateLimit(
                key=f"rate_limit:payment:user:{current_user.id}",
                limit=settings.PAYMENT_RATE_LIMIT,
                window_seconds=settings.PAYMENT_RATE_WINDOW_SECONDS,
            )
        ],
    )


@router.post("")
def create_payment(
    request: CreatePaymentRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(enforce_payment_limit),
):
    data = payment_service.create_payment(
        booking_id=request.booking_id,
        user_id=current_user.id,
        payment_method=request.payment_method,
    )

    return JSONResponse(
        content=data,
        status_code=data["status"],
    )


@router.post("/webhook")
def payment_webhook(request: PaymentWebhookRequest):
    data = payment_service.process_webhook(
        event_id=request.event_id,
        event_type=request.event_type,
        provider_payment_id=request.provider_payment_id,
        status=request.status,
        payload=request.model_dump(),
    )

    return JSONResponse(
        content=data,
        status_code=data["status"],
    )
