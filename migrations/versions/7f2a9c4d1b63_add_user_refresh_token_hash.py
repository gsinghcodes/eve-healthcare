"""Add refresh token hash to users.

Revision ID: 7f2a9c4d1b63
Revises: 10593261e249
Create Date: 2026-09-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7f2a9c4d1b63"
down_revision: Union[str, Sequence[str], None] = "10593261e249"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "refresh_token_hash")