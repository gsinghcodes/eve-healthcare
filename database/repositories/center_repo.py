from datetime import time
from typing import Optional
from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from database.models.center_model import DiagnosticCenter
from database.models.center_test_model import CenterTest


class CenterRepository:

    def get_center_by_id(
        self,
        center_id: UUID,
        session: Session,
    ) -> Optional[DiagnosticCenter]:
        stmt = select(DiagnosticCenter).where(DiagnosticCenter.id == center_id)

        return session.scalar(stmt)

    def get_center_by_name(
        self,
        name: str,
        session: Session,
    ) -> Optional[DiagnosticCenter]:
        stmt = select(DiagnosticCenter).where(DiagnosticCenter.name == name)

        return session.scalar(stmt)

    def create_center(
        self,
        name: str,
        address: str,
        latitude: float,
        longitude: float,
        opening_time: time,
        closing_time: time,
        geohash: str,
        owner_user_id: Optional[UUID],
        session: Session,
    ) -> DiagnosticCenter:

        center = DiagnosticCenter(
            name=name,
            address=address,
            latitude=latitude,
            longitude=longitude,
            opening_time=opening_time,
            closing_time=closing_time,
            geohash=geohash,
            owner_user_id=owner_user_id,
        )

        session.add(center)
        session.flush()

        return center

    def update_center(
        self,
        center: DiagnosticCenter,
        updates: dict[str, object],
        session: Session,
    ) -> DiagnosticCenter:
        for field, value in updates.items():
            setattr(center, field, value)
        session.flush()

        return center

    def get_all_centers(
        self,
        session: Session,
    ) -> list[DiagnosticCenter]:
        stmt = select(DiagnosticCenter).order_by(DiagnosticCenter.name)

        return list(session.scalars(stmt).all())

    def get_centers_by_geohash_prefixes(
        self,
        prefixes: list[str],
        session: Session,
        latitude: float,
        longitude: float,
        radius_km: float,
        test_id=None,
        sort_by_test_price: bool = False,
        sort_order: str = "asc",
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> tuple[list[DiagnosticCenter], int]:
        if not prefixes:
            return [], 0

        latitude_delta = func.radians(DiagnosticCenter.latitude - latitude)
        longitude_delta = func.radians(DiagnosticCenter.longitude - longitude)
        haversine = (
            func.pow(func.sin(latitude_delta / 2), 2)
            + func.cos(func.radians(latitude))
            * func.cos(func.radians(DiagnosticCenter.latitude))
            * func.pow(func.sin(longitude_delta / 2), 2)
        )
        distance = 2 * 6371.0088 * func.asin(
            func.sqrt(case((haversine > 1, 1.0), else_=haversine))
        )
        conditions = [
            or_(
                *[
                    DiagnosticCenter.geohash.startswith(prefix)
                    for prefix in prefixes
                ]
            ),
            distance <= radius_km,
        ]

        count_stmt = select(func.count(DiagnosticCenter.id))
        stmt = select(DiagnosticCenter)

        if test_id is not None:
            test_join = CenterTest.center_id == DiagnosticCenter.id
            test_conditions = (
                CenterTest.test_id == test_id,
                CenterTest.is_active.is_(True),
            )
            stmt = stmt.join(CenterTest, test_join)
            count_stmt = count_stmt.join(CenterTest, test_join)
            conditions.extend(test_conditions)

        stmt = stmt.where(*conditions)
        count_stmt = count_stmt.where(*conditions)
        total = session.scalar(count_stmt) or 0

        if sort_by_test_price:
            price_order = (
                CenterTest.price.desc()
                if sort_order == "desc"
                else CenterTest.price.asc()
            )
            stmt = stmt.order_by(price_order, DiagnosticCenter.name)
        else:
            distance_order = distance.desc() if sort_order == "desc" else distance.asc()
            stmt = stmt.order_by(distance_order, DiagnosticCenter.name)

        if page is not None and page_size is not None:
            stmt = stmt.limit(page_size).offset((page - 1) * page_size)

        return list(session.scalars(stmt).all()), total
