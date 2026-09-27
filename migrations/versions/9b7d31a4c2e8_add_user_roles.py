"""Add user roles for center management authorization.

Revision ID: 9b7d31a4c2e8
Revises: 7f2a9c4d1b63
Create Date: 2026-09-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9b7d31a4c2e8"
down_revision: Union[str, Sequence[str], None] = "7f2a9c4d1b63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=32), server_default="user", nullable=False),
    )
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('user', 'center_manager', 'admin')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_column("users", "role")