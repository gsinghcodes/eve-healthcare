from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.center_test_model import CenterTest


class CenterTestRepository:

    def get_by_id(
        self,
        center_test_id: UUID,
        session: Session,
    ) -> Optional[CenterTest]:
        stmt = select(CenterTest).where(CenterTest.id == center_test_id)

        return session.scalar(stmt)

    def get_by_center_and_test(
        self,
        center_id: UUID,
        test_id: UUID,
        session: Session,
    ) -> Optional[CenterTest]:
        stmt = select(CenterTest).where(
            CenterTest.center_id == center_id,
            CenterTest.test_id == test_id,
        )

        return session.scalar(stmt)

    def create(
        self,
        center_id: UUID,
        test_id: UUID,
        price,
        title_override: str | None,
        description_override: str | None,
        image_url_override: str | None,
        session: Session,
    ) -> CenterTest:

        center_test = CenterTest(
            center_id=center_id,
            test_id=test_id,
            price=price,
            title_override=title_override,
            description_override=description_override,
            image_url_override=image_url_override,
            is_active=True,
        )

        session.add(center_test)
        session.flush()

        return center_test

    def update(
        self,
        center_test: CenterTest,
        price,
        title_override: str | None,
        description_override: str | None,
        image_url_override: str | None,
        is_active: bool,
        session: Session,
    ) -> CenterTest:
        center_test.price = price
        center_test.title_override = title_override
        center_test.description_override = description_override
        center_test.image_url_override = image_url_override
        center_test.is_active = is_active
        session.flush()

        return center_test

    def get_by_center(
        self,
        center_id: UUID,
        session: Session,
    ) -> list[CenterTest]:
        stmt = (
            select(CenterTest)
            .where(
                CenterTest.center_id == center_id,
                CenterTest.is_active.is_(True),
            )
            .order_by(CenterTest.created_at)
        )

        return list(session.scalars(stmt).all())
