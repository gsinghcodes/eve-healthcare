import logging

from database.session import SessionLocal
from database.repositories.diagnostic_test_repo import DiagnosticTestRepository
from utils.model_utils import serialize_model
from utils.responses import send_response

logger = logging.getLogger(__name__)


class DiagnosticTestService:

    def __init__(self):
        self.test_repository = DiagnosticTestRepository()

    def create_test(
        self,
        name: str,
        description: str,
        image_url: str | None = None,
    ):
        with SessionLocal() as session:
            try:
                existing_test = self.test_repository.get_test_by_name(
                    name=name,
                    session=session,
                )

                if existing_test:
                    logger.warning(
                        "Diagnostic-test creation rejected: duplicate test_id=%s",
                        existing_test.id,
                    )
                    return send_response(
                        data=None,
                        status_code=409,
                        message="Diagnostic test already exists",
                    )

                test = self.test_repository.create_test(
                    name=name,
                    description=description,
                    image_url=image_url,
                    session=session,
                )

                session.commit()
                session.refresh(test)
                logger.info("Diagnostic test created: test_id=%s", test.id)

                return send_response(
                    data=serialize_model(test),
                    status_code=201,
                    message="Diagnostic test created successfully",
                )

            except Exception as e:
                session.rollback()
                logger.error(
                    "Diagnostic-test creation failed: error_type=%s",
                    type(e).__name__,
                )

                return send_response(
                    data=None,
                    status_code=500,
                    message="Failed to create diagnostic test",
                    error=str(e),
                )

    def get_test(self, test_id):
        with SessionLocal() as session:
            try:
                test = self.test_repository.get_test_by_id(
                    test_id=test_id,
                    session=session,
                )

                if not test:
                    logger.warning(
                        "Diagnostic-test fetch rejected: test not found test_id=%s",
                        test_id,
                    )
                    return send_response(
                        data=None,
                        status_code=404,
                        message="Diagnostic test not found",
                    )

                return send_response(
                    data=serialize_model(test),
                    status_code=200,
                    message="Diagnostic test fetched successfully",
                )

            except Exception as e:
                logger.error(
                    "Diagnostic-test fetch failed: test_id=%s error_type=%s",
                    test_id,
                    type(e).__name__,
                )
                return send_response(
                    data=None,
                    status_code=500,
                    message="Failed to fetch diagnostic test",
                    error=str(e),
                )

    def get_global_tests(self):
        with SessionLocal() as session:
            try:
                tests = self.test_repository.get_global_tests(
                    session=session,
                )

                return send_response(
                    data=[serialize_model(test) for test in tests],
                    status_code=200,
                    message="Diagnostic tests fetched successfully",
                )

            except Exception as e:
                logger.error(
                    "Global diagnostic-test fetch failed: error_type=%s",
                    type(e).__name__,
                )
                return send_response(
                    data=None,
                    status_code=500,
                    message="Failed to fetch diagnostic tests",
                    error=str(e),
                )
