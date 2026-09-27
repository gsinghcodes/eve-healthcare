import logging
from uuid import UUID

from database.session import SessionLocal
from database.repositories.center_test_repo import CenterTestRepository
from schemas.requests.center import (
    CreateCenterRequest,
    SearchCentersRequest,
    UpdateCenterRequest,
)
from database.repositories.center_repo import CenterRepository
from utils.geohash import calculate_geohash, geohashes_for_radius
from utils.model_utils import serialize_model
from utils.responses import send_response

logger = logging.getLogger(__name__)


class CenterService:

    def __init__(self):
        self.center_repository = CenterRepository()
        self.center_test_repository = CenterTestRepository()

    def get_center_by_id(self, center_id: UUID):
        with SessionLocal() as session:
            try:
                center = self.center_repository.get_center_by_id(
                    center_id=center_id,
                    session=session,
                )
                if not center:
                    return send_response(
                        data=None,
                        status_code=404,
                        message="Diagnostic center not found",
                    )

                center_data = serialize_model(center)
                center_data["tests"] = []

                for offering in self.center_test_repository.get_by_center(
                    center_id=center_id,
                    session=session,
                ):
                    offering_data = serialize_model(offering)
                    offering_data["test"] = serialize_model(offering.test)
                    center_data["tests"].append(offering_data)

                return send_response(
                    data=center_data,
                    status_code=200,
                    message="Diagnostic center fetched successfully",
                )
            except Exception as e:
                logger.error(
                    "Center lookup failed: center_id=%s error_type=%s",
                    center_id,
                    type(e).__name__,
                )
                return send_response(
                    data=None,
                    status_code=500,
                    message="Failed to fetch diagnostic center",
                    error=str(e),
                )

    def create_center(
        self,
        center: CreateCenterRequest,
        user_id: UUID,
        is_admin: bool,
    ):
        center_id = None
        with SessionLocal() as session:
            try:
                existing_center = self.center_repository.get_center_by_name(
                    name=center.name,
                    session=session,
                )

                if existing_center:
                    logger.warning(
                        "Center creation rejected: duplicate center_id=%s",
                        existing_center.id,
                    )
                    return send_response(
                        data=None,
                        status_code=409,
                        message="Diagnostic center already exists",
                    )

                geohash = calculate_geohash(
                    latitude=center.latitude,
                    longitude=center.longitude,
                )

                center = self.center_repository.create_center(
                    name=center.name,
                    address=center.address,
                    latitude=center.latitude,
                    longitude=center.longitude,
                    opening_time=center.opening_time,
                    closing_time=center.closing_time,
                    geohash=geohash,
                    owner_user_id=None if is_admin else user_id,
                    session=session,
                )

                session.commit()
                session.refresh(center)
                center_id = center.id
                logger.info("Center created: center_id=%s", center_id)

                return send_response(
                    data=serialize_model(center),
                    status_code=201,
                    message="Diagnostic center created successfully",
                )

            except Exception as e:
                session.rollback()
                logger.error(
                    "Center creation failed: center_id=%s error_type=%s",
                    center_id,
                    type(e).__name__,
                )

                return send_response(
                    data=None,
                    status_code=500,
                    message="Failed to create diagnostic center",
                    error=str(e),
                )

    def update_center(
        self,
        center_id: UUID,
        request: UpdateCenterRequest,
        user_id: UUID,
        is_admin: bool,
    ):
        with SessionLocal() as session:
            try:
                center = self.center_repository.get_center_by_id(
                    center_id=center_id,
                    session=session,
                )
                if not center:
                    logger.warning(
                        "Center update rejected: center not found center_id=%s",
                        center_id,
                    )
                    return send_response(
                        data=None,
                        status_code=404,
                        message="Diagnostic center not found",
                    )

                if not is_admin and center.owner_user_id != user_id:
                    return send_response(
                        data=None,
                        status_code=403,
                        message="You do not manage this diagnostic center",
                    )

                updates = request.model_dump(exclude_unset=True, exclude_none=True)
                if "name" in updates:
                    existing_center = self.center_repository.get_center_by_name(
                        name=updates["name"],
                        session=session,
                    )
                    if existing_center and existing_center.id != center_id:
                        logger.warning(
                            "Center update rejected: duplicate name center_id=%s "
                            "duplicate_center_id=%s",
                            center_id,
                            existing_center.id,
                        )
                        return send_response(
                            data=None,
                            status_code=409,
                            message="Diagnostic center already exists",
                        )

                opening_time = updates.get("opening_time", center.opening_time)
                closing_time = updates.get("closing_time", center.closing_time)
                if opening_time >= closing_time:
                    logger.warning(
                        "Center update rejected: invalid operating hours "
                        "center_id=%s",
                        center_id,
                    )
                    return send_response(
                        data=None,
                        status_code=400,
                        message="Opening time must be earlier than closing time",
                    )

                if "latitude" in updates or "longitude" in updates:
                    updates["geohash"] = calculate_geohash(
                        latitude=updates.get("latitude", center.latitude),
                        longitude=updates.get("longitude", center.longitude),
                    )

                center = self.center_repository.update_center(
                    center=center,
                    updates=updates,
                    session=session,
                )

                session.commit()
                session.refresh(center)
                logger.info("Center updated: center_id=%s", center_id)
                return send_response(
                    data=serialize_model(center),
                    status_code=200,
                    message="Diagnostic center updated successfully",
                )
            except Exception as e:
                session.rollback()
                logger.error(
                    "Center update failed: center_id=%s error_type=%s",
                    center_id,
                    type(e).__name__,
                )
                return send_response(
                    data=None,
                    status_code=500,
                    message="Failed to update diagnostic center",
                    error=str(e),
                )

    def get_centers_in_radius(
        self,
        request: SearchCentersRequest,
    ):
        try:
            test_id = UUID(request.test_id) if request.test_id is not None else None
        except ValueError:
            return send_response(
                data=None,
                status_code=400,
                message="test_id must be a valid UUID",
            )

        if request.sort_by == "test_price" and test_id is None:
            return send_response(
                data=None,
                status_code=400,
                message="test_id is required when sorting by test price",
            )

        with SessionLocal() as session:
            try:
                prefixes = geohashes_for_radius(
                    latitude=request.latitude,
                    longitude=request.longitude,
                    radius_km=request.radius,
                )
                page = request.page if request.view == "list" else None
                page_size = request.page_size if request.view == "list" else None
                centers, total = self.center_repository.get_centers_by_geohash_prefixes(
                    prefixes=prefixes,
                    session=session,
                    test_id=test_id,
                    sort_by_test_price=request.sort_by == "test_price",
                    sort_order=request.sort_order,
                    latitude=request.latitude,
                    longitude=request.longitude,
                    radius_km=request.radius,
                    page=page,
                    page_size=page_size,
                )
                if request.view == "list":
                    pagination = {
                        "page": request.page,
                        "page_size": request.page_size,
                        "total_pages": (total + request.page_size - 1)
                        // request.page_size,
                    }
                else:
                    pagination = None

                logger.info(
                    "Center search completed: view=%s results=%s total=%s",
                    request.view,
                    len(centers),
                    total,
                )
                return send_response(
                    data={
                        "items": [serialize_model(center) for center in centers],
                        "view": request.view,
                        "total": total,
                        "pagination": pagination,
                    },
                    status_code=200,
                    message="Diagnostic centers fetched successfully",
                )

            except Exception as e:
                logger.error(
                    "Center search failed: error_type=%s",
                    type(e).__name__,
                )
                return send_response(
                    data=None,
                    status_code=500,
                    message="Failed to fetch diagnostic centers",
                    error=str(e),
                )
