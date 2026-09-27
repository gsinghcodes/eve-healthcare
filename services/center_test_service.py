import logging
from uuid import UUID

from database.session import SessionLocal
from database.repositories.center_test_repo import CenterTestRepository
from database.repositories.center_repo import CenterRepository
from database.repositories.diagnostic_test_repo import DiagnosticTestRepository
from utils.model_utils import serialize_model
from utils.responses import send_response

logger = logging.getLogger(__name__)


class CenterTestService:

    def __init__(self):
        self.center_test_repository = CenterTestRepository()
        self.center_repository = CenterRepository()
        self.test_repository = DiagnosticTestRepository()

    def create_center_test(
        self,
        center_id,
        test_id,
        price,
        user_id: UUID,
        is_admin: bool,
        title_override=None,
        description_override=None,
        image_url_override=None,
    ):
        with SessionLocal() as session:
            try:
                center = self.center_repository.get_center_by_id(
                    center_id=center_id,
                    session=session,
                )

                if not center:
                    logger.warning(
                        "Center-test creation rejected: center not found "
                        "center_id=%s test_id=%s",
                        center_id,
                        test_id,
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

                test = self.test_repository.get_test_by_id(
                    test_id=test_id,
                    session=session,
                )

                if not test:
                    logger.warning(
                        "Center-test creation rejected: test not found "
                        "center_id=%s test_id=%s",
                        center_id,
                        test_id,
                    )
                    return send_response(
                        data=None,
                        status_code=404,
                        message="Diagnostic test not found",
                    )

                existing = self.center_test_repository.get_by_center_and_test(
                    center_id=center_id,
                    test_id=test_id,
                    session=session,
                )

                if existing:
                    logger.warning(
                        "Center-test creation rejected: offer already exists "
                        "center_id=%s test_id=%s center_test_id=%s",
                        center_id,
                        test_id,
                        existing.id,
                    )
                    return send_response(
                        data=None,
                        status_code=409,
                        message="Test is already offered by this diagnostic center",
                    )

                if price < 0:
                    logger.warning(
                        "Center-test creation rejected: negative price "
                        "center_id=%s test_id=%s",
                        center_id,
                        test_id,
                    )
                    return send_response(
                        data=None,
                        status_code=400,
                        message="Price cannot be negative",
                    )

                center_test = self.center_test_repository.create(
                    center_id=center_id,
                    test_id=test_id,
                    price=price,
                    title_override=title_override,
                    description_override=description_override,
                    image_url_override=image_url_override,
                    session=session,
                )

                session.commit()
                session.refresh(center_test)
                logger.info(
                    "Center-test created: center_test_id=%s center_id=%s "
                    "test_id=%s",
                    center_test.id,
                    center_id,
                    test_id,
                )

                return send_response(
                    data=serialize_model(center_test),
                    status_code=201,
                    message="Diagnostic test added to center successfully",
                )

            except Exception as e:
                session.rollback()
                logger.error(
                    "Center-test creation failed: center_id=%s test_id=%s "
                    "error_type=%s",
                    center_id,
                    test_id,
                    type(e).__name__,
                )

                return send_response(
                    data=None,
                    status_code=500,
                    message="Failed to add diagnostic test to center",
                    error=str(e),
                )

    def update_center_test(
        self,
        center_test_id,
        price,
        user_id: UUID,
        is_admin: bool,
        title_override=None,
        description_override=None,
        image_url_override=None,
        is_active=True,
    ):
        with SessionLocal() as session:
            try:
                center_test = self.center_test_repository.get_by_id(
                    center_test_id=center_test_id,
                    session=session,
                )
                if not center_test:
                    logger.warning(
                        "Center-test update rejected: record not found "
                        "center_test_id=%s",
                        center_test_id,
                    )
                    return send_response(
                        data=None,
                        status_code=404,
                        message="Center test not found",
                    )

                center = self.center_repository.get_center_by_id(
                    center_id=center_test.center_id,
                    session=session,
                )
                if not center:
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

                if price < 0:
                    logger.warning(
                        "Center-test update rejected: negative price "
                        "center_test_id=%s",
                        center_test_id,
                    )
                    return send_response(
                        data=None,
                        status_code=400,
                        message="Price cannot be negative",
                    )

                center_test = self.center_test_repository.update(
                    center_test=center_test,
                    price=price,
                    title_override=title_override,
                    description_override=description_override,
                    image_url_override=image_url_override,
                    is_active=is_active,
                    session=session,
                )
                session.commit()
                session.refresh(center_test)
                logger.info("Center-test updated: center_test_id=%s", center_test_id)
                return send_response(
                    data=serialize_model(center_test),
                    status_code=200,
                    message="Center test updated successfully",
                )
            except Exception as e:
                session.rollback()
                logger.error(
                    "Center-test update failed: center_test_id=%s error_type=%s",
                    center_test_id,
                    type(e).__name__,
                )
                return send_response(
                    data=None,
                    status_code=500,
                    message="Failed to update center test",
                    error=str(e),
                )
