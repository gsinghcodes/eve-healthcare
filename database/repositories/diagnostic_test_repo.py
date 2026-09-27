from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.test_model import DiagnosticTest


class DiagnosticTestRepository:

    def get_test_by_id(
        self,
        test_id: UUID,
        session: Session,
    ) -> Optional[DiagnosticTest]:
        stmt = select(DiagnosticTest).where(DiagnosticTest.id == test_id)

        return session.scalar(stmt)

    def get_test_by_name(
        self,
        name: str,
        session: Session,
    ) -> Optional[DiagnosticTest]:
        stmt = select(DiagnosticTest).where(DiagnosticTest.name == name)

        return session.scalar(stmt)

    def create_test(
        self,
        name: str,
        description: str,
        image_url: Optional[str],
        session: Session,
    ) -> DiagnosticTest:

        test = DiagnosticTest(
            name=name,
            description=description,
            image_url=image_url,
            is_global=True,
        )

        session.add(test)
        session.flush()

        return test

    def get_global_tests(
        self,
        session: Session,
    ) -> list[DiagnosticTest]:
        stmt = (
            select(DiagnosticTest)
            .where(DiagnosticTest.is_global.is_(True))
            .order_by(DiagnosticTest.name)
        )

        return list(session.scalars(stmt).all())
