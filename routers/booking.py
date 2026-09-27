from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from database.models.user_model import User
from routers.middlewares.auth import get_current_user
from schemas.requests.booking import CreateBookingRequest, RescheduleBookingRequest
from services.booking_service import BookingService
from core.config import settings
from utils.rate_limiter import RateLimit, check_rate_limits

router = APIRouter(
    prefix="/api/v1/bookings",
    tags=["Bookings"],
)

booking_service = BookingService()


def enforce_booking_limit(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> None:
    check_rate_limits(
        request.app.state.redis,
        [
            RateLimit(
                key=f"rate_limit:booking:user:{current_user.id}",
                limit=settings.BOOKING_RATE_LIMIT,
                window_seconds=settings.BOOKING_RATE_WINDOW_SECONDS,
            )
        ],
    )


@router.post(
    "",
    summary="Create booking",
    description="Create a booking for the user.",
    status_code=201,
)
def create_booking(
    request: CreateBookingRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(enforce_booking_limit),
):
    data = booking_service.create_booking(
        user_id=current_user.id,
        center_test_id=request.center_test_id,
        appointment_date=request.appointment_date,
        time_slot=request.time_slot,
    )

    return JSONResponse(
        content=data,
        status_code=data["status"],
    )


@router.get(
    "",
    summary="Get current user's bookings",
    description="Retrieve bookings belonging to the user.",
)
def get_user_bookings(
    current_user: User = Depends(get_current_user),
):
    data = booking_service.get_user_bookings(user_id=current_user.id)

    return JSONResponse(
        content=data,
        status_code=data["status"],
    )


@router.patch(
    "/{booking_id}/reschedule",
    summary="Reschedule booking",
    description="Move the user's booking to another available slot.",
)
def reschedule_booking(
    booking_id,
    request: RescheduleBookingRequest,
    current_user: User = Depends(get_current_user),
):
    data = booking_service.reschedule_booking(
        booking_id=booking_id,
        user_id=current_user.id,
        appointment_date=request.appointment_date,
        time_slot=request.time_slot,
    )

    return JSONResponse(
        content=data,
        status_code=data["status"],
    )


@router.post(
    "/{booking_id}/cancel",
    summary="Cancel booking",
    description="Cancel the user's booking.",
)
def cancel_booking(
    booking_id,
    current_user: User = Depends(get_current_user),
):
    data = booking_service.cancel_booking(
        booking_id=booking_id,
        user_id=current_user.id,
    )

    return JSONResponse(
        content=data,
        status_code=data["status"],
    )
