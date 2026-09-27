from uuid import UUID
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.user_model import User


class UserRepository:

    def get_user_by_id(self, user_id: UUID, session: Session) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        return session.scalar(stmt)

    def get_user_by_phone(self, phone_number: str, session: Session) -> Optional[User]:
        stmt = select(User).where(User.phone_number == phone_number)
        return session.scalar(stmt)

    def create_user(self, phone_number: str, session: Session) -> User:
        user = User(
            phone_number=phone_number,
            is_verified=False,
        )

        session.add(user)
        session.flush()

        return user

    def mark_user_verified(self, user: User, session: Session) -> User:
        user.is_verified = True
        session.flush()

        return user
