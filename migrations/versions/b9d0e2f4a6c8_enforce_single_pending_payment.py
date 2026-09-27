"""Enforce one pending payment per booking.

Revision ID: b9d0e2f4a6c8
Revises: a2f4c6d8e0b1
Create Date: 2026-09-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b9d0e2f4a6c8"
down_revision: Union[str, Sequence[str], None] = "a2f4c6d8e0b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            WITH ranked_pending_payments AS (
                SELECT id,
                       row_number() OVER (
                           PARTITION BY booking_id
                           ORDER BY created_at DESC, id DESC
                       ) AS payment_rank
                FROM payments
                WHERE status = 'PENDING'
            )
            UPDATE payments
            SET status = 'FAILED'
            FROM ranked_pending_payments
            WHERE payments.id = ranked_pending_payments.id
              AND ranked_pending_payments.payment_rank > 1
            """
        )
    )
    op.create_index(
        "uq_pending_payment_per_booking",
        "payments",
        ["booking_id"],
        unique=True,
        postgresql_where=sa.text("status = 'PENDING'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_pending_payment_per_booking",
        table_name="payments",
    )