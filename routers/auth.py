from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from core.config import settings
from schemas.requests.auth import (
    RequestOTPRequest,
    VerifyOTPRequest,
)
from services.auth.auth_service import AuthService
from utils.rate_limiter import (
    RateLimit,
    check_rate_limits,
    hashed_identifier,
    request_client_ip,
)

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Auth"],
)

auth_service = AuthService()
REFRESH_TOKEN_COOKIE = "refresh_token"


def enforce_otp_request_limit(
    request: Request,
    payload: RequestOTPRequest,
) -> RequestOTPRequest:
    phone_hash = hashed_identifier(payload.phone_number)
    check_rate_limits(
        request.app.state.redis,
        [
            RateLimit(
                key=f"rate_limit:otp:ip:{request_client_ip(request)}",
                limit=settings.OTP_IP_RATE_LIMIT,
                window_seconds=settings.OTP_IP_RATE_WINDOW_SECONDS,
            ),
            RateLimit(
                key=f"rate_limit:otp:phone:{phone_hash}",
                limit=settings.OTP_PHONE_RATE_LIMIT,
                window_seconds=settings.OTP_PHONE_RATE_WINDOW_SECONDS,
            ),
        ],
    )
    return payload


def enforce_otp_verification_limit(
    request: Request,
    payload: VerifyOTPRequest,
) -> VerifyOTPRequest:
    phone_hash = hashed_identifier(payload.phone_number)
    check_rate_limits(
        request.app.state.redis,
        [
            RateLimit(
                key=f"rate_limit:otp:verify:{phone_hash}",
                limit=settings.OTP_VERIFY_RATE_LIMIT,
                window_seconds=settings.OTP_VERIFY_RATE_WINDOW_SECONDS,
            )
        ],
    )
    return payload


def enforce_refresh_limit(request: Request) -> None:
    check_rate_limits(
        request.app.state.redis,
        [
            RateLimit(
                key=f"rate_limit:refresh:ip:{request_client_ip(request)}",
                limit=settings.REFRESH_RATE_LIMIT,
                window_seconds=settings.REFRESH_RATE_WINDOW_SECONDS,
            )
        ],
    )


def _set_refresh_token_cookie(response: JSONResponse, token: str) -> None:
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/auth/refresh-token",
        httponly=True,
        secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        samesite="lax",
    )


@router.post(
    "/request-otp",
    summary="Request OTP",
    description=(
        "Creates a user if the phone number is not registered and "
        "sends a new OTP to the provided phone number. "
        "Any previously active OTP for the user is invalidated."
    ),
    status_code=200,
    response_description="OTP request result",
    responses={
        200: {
            "description": "OTP generated and sent successfully",
        },
        500: {
            "description": "Failed to generate or send OTP",
        },
    },
)
def request_otp(
    request: RequestOTPRequest = Depends(enforce_otp_request_limit),
):
    data = auth_service.request_otp(
        phone_number=request.phone_number,
    )

    return JSONResponse(
        content=data,
        status_code=data["status"],
    )


@router.post(
    "/verify-otp",
    summary="Verify OTP",
    description=(
        "Verifies the OTP associated with the provided phone number. "
        "A successful verification marks the user as verified and "
        "returns a JWT access token and sets a refresh-token cookie."
    ),
    status_code=200,
    response_description="OTP verification result",
    responses={
        200: {
            "description": "OTP verified successfully and access token issued",
        },
        400: {
            "description": (
                "Invalid, expired, or already used OTP, "
                "or maximum verification attempts exceeded"
            ),
        },
        404: {
            "description": "User not found",
        },
        500: {
            "description": "Failed to verify OTP",
        },
    },
)
def verify_otp(
    request: VerifyOTPRequest = Depends(enforce_otp_verification_limit),
):
    data = auth_service.verify_otp(
        phone_number=request.phone_number,
        otp=request.otp,
    )

    refresh_token = None
    if data["status"] == 200:
        refresh_token = data["data"].pop("refresh_token")

    response = JSONResponse(
        content=data,
        status_code=data["status"],
    )
    if refresh_token:
        _set_refresh_token_cookie(response, refresh_token)

    return response


@router.post(
    "/refresh-token",
    summary="Refresh access token",
    description=(
        "Validates the refresh-token cookie, rotates it, and returns a new "
        "access token."
    ),
    status_code=200,
    response_description="New access token and rotated refresh-token cookie",
    responses={
        401: {"description": "Invalid, expired, or previously used refresh token"},
        500: {"description": "Failed to refresh token"},
    },
)
def refresh_token(
    request: Request,
    _: None = Depends(enforce_refresh_limit),
):
    data = auth_service.refresh_token(
        refresh_token=request.cookies.get(REFRESH_TOKEN_COOKIE),
    )

    rotated_refresh_token = None
    if data["status"] == 200:
        rotated_refresh_token = data["data"].pop("refresh_token")

    response = JSONResponse(
        content=data,
        status_code=data["status"],
    )
    if rotated_refresh_token:
        _set_refresh_token_cookie(response, rotated_refresh_token)

    return response
