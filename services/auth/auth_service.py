from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import logging
import secrets
from uuid import UUID

from jwt import InvalidTokenError

from services.auth.jwt_service import JWTService
from services.providers.sms_provider import SMSProvider
from database.session import SessionLocal
from database.repositories.auth_repo import AuthRepository
from database.repositories.user_repo import UserRepository
from utils.auth_utils import normalize_otp, normalize_phone_number
from utils.model_utils import serialize_model
from utils.responses import send_response

OTP_EXPIRY_MINUTES = 5
MAX_OTP_ATTEMPTS = 5
logger = logging.getLogger(__name__)


class AuthService:

    def __init__(self):
        self.jwt_service = JWTService()
        self.sms_provider_service = SMSProvider()
        self.user_repository = UserRepository()
        self.auth_repository = AuthRepository()

    def request_otp(self, phone_number: str):
        normalized_phone_number = normalize_phone_number(phone_number)

        if not normalized_phone_number:
            return send_response(
                data={},
                status_code=400,
                message="Invalid phone number",
            )

        user_id = None
        with SessionLocal() as session:
            try:
                user = self.user_repository.get_user_by_phone(
                    phone_number=normalized_phone_number,
                    session=session,
                )

                if not user:
                    user = self.user_repository.create_user(
                        phone_number=normalized_phone_number,
                        session=session,
                    )
                user_id = user.id

                self.auth_repository.invalidate_active_otps(
                    user_id=user.id,
                    session=session,
                )

                otp = self._generate_otp()
                otp_hash = self._hash_token(otp)

                expires_at = datetime.now(timezone.utc) + timedelta(
                    minutes=OTP_EXPIRY_MINUTES
                )

                self.auth_repository.create_otp(
                    user_id=user.id,
                    otp_hash=otp_hash,
                    expires_at=expires_at,
                    session=session,
                )

                session.commit()

                self.sms_provider_service.send_otp(normalized_phone_number, otp)
                logger.info(
                    "OTP sent: user_id=%s expires_at=%s",
                    user_id,
                    expires_at.isoformat(),
                )

                return send_response(
                    data=None,
                    status_code=200,
                    message="OTP sent successfully",
                )

            except Exception as e:
                session.rollback()
                logger.error(
                    "OTP request failed: user_id=%s error_type=%s",
                    user_id,
                    type(e).__name__,
                )

                return send_response(
                    data=None,
                    status_code=500,
                    message="Failed to send OTP",
                    error=str(e),
                )

    def verify_otp(self, phone_number: str, otp: str):
        normalized_phone_number = normalize_phone_number(phone_number)
        normalized_otp = normalize_otp(otp)

        if not normalized_phone_number or not normalized_otp:
            return send_response(
                data=None,
                status_code=400,
                message="Invalid phone number",
            )

        user_id = None
        with SessionLocal() as session:
            try:
                user = self.user_repository.get_user_by_phone(
                    phone_number=normalized_phone_number,
                    session=session,
                )

                if not user:
                    return send_response(
                        data=None,
                        status_code=404,
                        message="User not found",
                    )
                user_id = user.id

                otp_verification = self.auth_repository.get_active_otp(
                    user_id=user.id,
                    session=session,
                )

                if not otp_verification:
                    logger.warning(
                        "OTP verification rejected: no active OTP for user_id=%s",
                        user_id,
                    )
                    return send_response(
                        data=None,
                        status_code=400,
                        message="No active OTP found",
                    )

                now = datetime.now(timezone.utc)

                if otp_verification.verified_at is not None:
                    logger.warning(
                        "OTP verification rejected: already used for user_id=%s",
                        user_id,
                    )
                    return send_response(
                        data=None,
                        status_code=400,
                        message="OTP has already been used",
                    )

                if now >= otp_verification.expires_at:
                    logger.warning(
                        "OTP verification rejected: expired for user_id=%s " "at %s",
                        user_id,
                        otp_verification.expires_at.isoformat(),
                    )
                    return send_response(
                        data=None,
                        status_code=400,
                        message="OTP has expired",
                    )

                if otp_verification.attempts >= MAX_OTP_ATTEMPTS:
                    logger.warning(
                        "OTP verification rejected: attempt limit reached "
                        "for user_id=%s (%s/%s)",
                        user_id,
                        otp_verification.attempts,
                        MAX_OTP_ATTEMPTS,
                    )
                    return send_response(
                        data=None,
                        status_code=400,
                        message="Maximum OTP attempts exceeded",
                    )

                otp_verification.attempts += 1

                otp_hash = self._hash_token(normalized_otp)

                if not hmac.compare_digest(
                    otp_hash,
                    otp_verification.otp_hash,
                ):
                    session.commit()
                    logger.warning(
                        "OTP verification rejected: incorrect code for "
                        "user_id=%s (attempt %s/%s)",
                        user_id,
                        otp_verification.attempts,
                        MAX_OTP_ATTEMPTS,
                    )

                    return send_response(
                        data=None,
                        status_code=400,
                        message="Invalid OTP",
                    )

                otp_verification.verified_at = now
                user.is_verified = True

                access_token = self.jwt_service.create_access_token(user.id)
                refresh_token = self.jwt_service.create_refresh_token(user.id)
                user.refresh_token_hash = self._hash_token(refresh_token)

                session.commit()
                session.refresh(user)
                user_data = serialize_model(user)
                user_data.pop("refresh_token_hash", None)
                logger.info(
                    "OTP verified: user_id=%s attempts=%s",
                    user_id,
                    otp_verification.attempts,
                )

                return send_response(
                    data={
                        "user": user_data,
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                    },
                    status_code=200,
                    message="OTP verified successfully",
                )

            except Exception as e:
                session.rollback()
                logger.error(
                    "OTP verification failed: user_id=%s error_type=%s",
                    user_id,
                    type(e).__name__,
                )

                return send_response(
                    data=None,
                    status_code=500,
                    message="Failed to verify OTP",
                    error=str(e),
                )

    def refresh_token(self, refresh_token: str | None):
        try:
            if not refresh_token:
                raise InvalidTokenError("Missing refresh token")
            claims = self.jwt_service.decode_refresh_token(refresh_token)
            if claims.get("type") != "refresh":
                raise InvalidTokenError("Invalid refresh token")
            user_id = UUID(claims["sub"])
        except (InvalidTokenError, KeyError, ValueError):
            return send_response(
                data=None,
                status_code=401,
                message="Invalid or expired refresh token",
            )

        with SessionLocal() as session:
            try:
                user = self.user_repository.get_user_by_id(
                    user_id=user_id,
                    session=session,
                )

                if (
                    not user
                    or not user.is_verified
                    or not user.refresh_token_hash
                    or not hmac.compare_digest(
                        self._hash_token(refresh_token),
                        user.refresh_token_hash,
                    )
                ):
                    logger.warning(
                        "Refresh token rejected: invalid account or token "
                        "for user_id=%s",
                        user_id,
                    )
                    return send_response(
                        data=None,
                        status_code=401,
                        message="Invalid or expired refresh token",
                    )

                access_token = self.jwt_service.create_access_token(user.id)
                rotated_refresh_token = self.jwt_service.create_refresh_token(user.id)
                user.refresh_token_hash = self._hash_token(rotated_refresh_token)
                session.commit()
                logger.info("Refresh token rotated: user_id=%s", user_id)

                return send_response(
                    data={
                        "access_token": access_token,
                        "refresh_token": rotated_refresh_token,
                    },
                    status_code=200,
                    message="Token refreshed successfully",
                )
            except Exception as e:
                session.rollback()
                logger.error(
                    "Refresh token rotation failed: user_id=%s error_type=%s",
                    user_id,
                    type(e).__name__,
                )

                return send_response(
                    data=None,
                    status_code=500,
                    message="Failed to refresh token",
                    error=str(e),
                )

    @staticmethod
    def _generate_otp() -> str:
        return str(secrets.randbelow(1_000_000)).zfill(6)

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
