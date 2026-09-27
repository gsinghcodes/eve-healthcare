import logging
from uuid import UUID

from database.session import SessionLocal
from database.repositories.user_repo import UserRepository
from utils.responses import send_response
from utils.model_utils import serialize_model

logger = logging.getLogger(__name__)


class UserService:

    def __init__(self):
        self.user_repository = UserRepository()

    def get_user_by_id(self, user_id: UUID):
        with SessionLocal() as session:
            user = self.user_repository.get_user_by_id(
                user_id=user_id,
                session=session,
            )

            if not user:
                logger.info("User lookup by ID returned no result: user_id=%s", user_id)
                return send_response(
                    data=None,
                    status_code=404,
                    message="User not found",
                )

            return send_response(
                data=serialize_model(user),
                status_code=200,
                message="User fetched successfully",
            )

    def get_user_by_phone(self, phone_number: str):
        with SessionLocal() as session:
            user = self.user_repository.get_user_by_phone(
                phone_number=phone_number,
                session=session,
            )

            if not user:
                return send_response(
                    data=None,
                    status_code=404,
                    message="User not found",
                )

            return send_response(
                data=serialize_model(user),
                status_code=200,
                message="User fetched successfully",
            )

    def create_user(self, phone_number: str):
        with SessionLocal() as session:
            user_id = None
            try:
                user = self.user_repository.create_user(
                    phone_number=phone_number,
                    session=session,
                )
                user_id = user.id

                session.commit()
                session.refresh(user)
                logger.info("User created: user_id=%s", user_id)

                return send_response(
                    data=serialize_model(user),
                    status_code=201,
                    message="User created successfully",
                )

            except Exception as e:
                session.rollback()
                logger.error(
                    "User creation failed: user_id=%s error_type=%s",
                    user_id,
                    type(e).__name__,
                )

                return send_response(
                    data=None,
                    status_code=500,
                    message="Failed to create user",
                    error=str(e),
                )
