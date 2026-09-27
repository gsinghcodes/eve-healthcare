"""Add center ownership.

Revision ID: d3f8a1c6b9e2
Revises: f6a1c2d3e4b5
Create Date: 2026-09-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d3f8a1c6b9e2"
down_revision: Union[str, Sequence[str], None] = "f6a1c2d3e4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "diagnostic_centers",
        sa.Column("owner_user_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_diagnostic_centers_owner_user_id_users",
        "diagnostic_centers",
        "users",
        ["owner_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_diagnostic_centers_owner_user_id",
        "diagnostic_centers",
        ["owner_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_diagnostic_centers_owner_user_id",
        table_name="diagnostic_centers",
    )
    op.drop_constraint(
        "fk_diagnostic_centers_owner_user_id_users",
        "diagnostic_centers",
        type_="foreignkey",
    )
    op.drop_column("diagnostic_centers", "owner_user_id")