"""Add per-center operating hours.

Revision ID: f6a1c2d3e4b5
Revises: e7f4b2a19c6d
Create Date: 2026-09-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a1c2d3e4b5"
down_revision: Union[str, Sequence[str], None] = "e7f4b2a19c6d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "diagnostic_centers",
        sa.Column(
            "opening_time",
            sa.Time(),
            server_default=sa.text("'09:00:00'"),
            nullable=False,
        ),
    )
    op.add_column(
        "diagnostic_centers",
        sa.Column(
            "closing_time",
            sa.Time(),
            server_default=sa.text("'17:00:00'"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("diagnostic_centers", "closing_time")
    op.drop_column("diagnostic_centers", "opening_time")
