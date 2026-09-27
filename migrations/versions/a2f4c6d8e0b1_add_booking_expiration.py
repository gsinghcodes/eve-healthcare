"""Add pending booking expiration timestamps.

Revision ID: a2f4c6d8e0b1
Revises: f6a1c2d3e4b5
Create Date: 2026-09-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a2f4c6d8e0b1"
down_revision: Union[str, Sequence[str], None] = "f6a1c2d3e4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bookings",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE bookings SET expires_at = created_at WHERE expires_at IS NULL")
    op.alter_column("bookings", "expires_at", nullable=False)
    op.create_index("ix_bookings_expires_at", "bookings", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_bookings_expires_at", table_name="bookings")
    op.drop_column("bookings", "expires_at")