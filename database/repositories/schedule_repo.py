from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.schedule_model import Schedule, ScheduleStatus


class ScheduleRepository:

    def get_by_id_for_update(
        self,
        schedule_id: UUID,
        session: Session,
    ) -> Optional[Schedule]:
        stmt = (
            select(Schedule)
            .where(Schedule.id == schedule_id)
            .with_for_update()
        )
        return session.scalar(stmt)

    def get_by_slot_for_update(
        self,
        center_test_id: UUID,
        starts_at: datetime,
        session: Session,
    ) -> Optional[Schedule]:
        stmt = (
            select(Schedule)
            .where(
                Schedule.center_test_id == center_test_id,
                Schedule.starts_at == starts_at,
                Schedule.status.in_(
                    [
                        ScheduleStatus.PENDING.value,
                        ScheduleStatus.CONFIRMED.value,
                    ]
                ),
            )
            .with_for_update()
        )
        return session.scalar(stmt)

    def get_for_center_test_on_date(
        self,
        center_test_id: UUID,
        starts_at: datetime,
        ends_at: datetime,
        session: Session,
    ) -> list[Schedule]:
        stmt = (
            select(Schedule)
            .where(
                Schedule.center_test_id == center_test_id,
                Schedule.starts_at >= starts_at,
                Schedule.starts_at < ends_at,
            )
            .order_by(Schedule.starts_at)
        )
        return list(session.scalars(stmt).all())

    def create(
        self,
        center_test_id: UUID,
        starts_at: datetime,
        ends_at: datetime,
        session: Session,
    ) -> Schedule:
        schedule = Schedule(
            center_test_id=center_test_id,
            starts_at=starts_at,
            ends_at=ends_at,
        )
        session.add(schedule)
        session.flush()
        return schedule