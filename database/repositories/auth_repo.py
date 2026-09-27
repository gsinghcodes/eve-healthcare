from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from database.models.otp_verifications_model import OTPVerification


class AuthRepository:

    def create_otp(
        self,
        user_id: UUID,
        otp_hash: str,
        expires_at: datetime,
        session: Session,
    ) -> OTPVerification:
        otp = OTPVerification(
            user_id=user_id,
            otp_hash=otp_hash,
            expires_at=expires_at,
            attempts=0,
        )

        session.add(otp)
        session.flush()

        return otp

    def get_active_otp(
        self,
        user_id: UUID,
        session: Session,
    ) -> OTPVerification | None:
        stmt = (
            select(OTPVerification)
            .where(
                OTPVerification.user_id == user_id,
                OTPVerification.verified_at.is_(None),
            )
            .order_by(OTPVerification.created_at.desc())
        )

        return session.scalar(stmt)

    def invalidate_active_otps(
        self,
        user_id: UUID,
        session: Session,
    ) -> None:
        stmt = update(OTPVerification).where(
            OTPVerification.user_id == user_id,
            OTPVerification.verified_at.is_(None),
        )

        session.execute(stmt)
