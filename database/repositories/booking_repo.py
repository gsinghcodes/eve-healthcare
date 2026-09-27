from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.booking_model import Booking
from database.models.schedule_model import Schedule


class BookingRepository:

    def get_by_id(
        self,
        booking_id: UUID,
        session: Session,
    ) -> Optional[Booking]:
        stmt = select(Booking).where(Booking.id == booking_id)

        return session.scalar(stmt)

    def get_by_id_for_update(
        self,
        booking_id: UUID,
        session: Session,
    ) -> Optional[Booking]:
        stmt = (
            select(Booking)
            .where(Booking.id == booking_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return session.scalar(stmt)

    def get_by_schedule_for_update(
        self,
        schedule_id: UUID,
        session: Session,
    ) -> Optional[Booking]:
        stmt = (
            select(Booking)
            .where(Booking.schedule_id == schedule_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return session.scalar(stmt)

    def create(
        self,
        user_id: UUID,
        schedule_id: UUID,
        amount,
        expires_at,
        session: Session,
    ) -> Booking:

        booking = Booking(
            user_id=user_id,
            schedule_id=schedule_id,
            amount=amount,
            status="PENDING",
            expires_at=expires_at,
        )

        session.add(booking)
        session.flush()

        return booking

    def get_user_bookings(
        self,
        user_id: UUID,
        session: Session,
    ) -> list[Booking]:
        stmt = (
            select(Booking)
            .where(Booking.user_id == user_id)
            .order_by(Booking.created_at.desc())
        )

        return list(session.scalars(stmt).all())

    def expire_due(self, now, session: Session) -> int:
        stmt = (
            select(Schedule)
            .join(Booking, Booking.schedule_id == Schedule.id)
            .where(
                Booking.status == "PENDING",
                Booking.expires_at <= now,
            )
            .order_by(Schedule.id)
            .with_for_update(of=Schedule, skip_locked=True)
        )
        schedules = list(session.scalars(stmt).all())
        expired_count = 0

        for schedule in schedules:
            booking = self.get_by_schedule_for_update(
                schedule_id=schedule.id,
                session=session,
            )
            if (
                booking
                and booking.status == "PENDING"
                and booking.expires_at <= now
            ):
                booking.status = "EXPIRED"
                if schedule.status == "PENDING":
                    schedule.status = "CANCELLED"
                expired_count += 1

        session.flush()
        return expired_count
