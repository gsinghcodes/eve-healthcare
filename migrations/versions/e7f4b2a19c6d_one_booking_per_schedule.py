"""Add schedule lifecycle status and enforce one booking per schedule.

Revision ID: e7f4b2a19c6d
Revises: c4e8a1f2d7b3
Create Date: 2026-09-26

"""
from datetime import datetime
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision: str = "e7f4b2a19c6d"
down_revision: Union[str, Sequence[str], None] = "c4e8a1f2d7b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_schedule_center_test_start",
        "schedules",
        type_="unique",
    )
    op.add_column(
        "schedules",
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="PENDING",
            nullable=False,
        ),
    )

    # Legacy data could contain several bookings at the same timestamp. Give
    # each legacy booking its own schedule before adding the one-to-one rule.
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            """
            SELECT b.id AS booking_id, b.schedule_id,
                   s.center_test_id, s.starts_at, s.ends_at, s.status
            FROM bookings AS b
            JOIN schedules AS s ON s.id = b.schedule_id
            ORDER BY b.schedule_id, b.id
            """
        )
    ).mappings().all()

    seen_schedules: set[str] = set()
    for row in rows:
        schedule_id = str(row["schedule_id"])
        if schedule_id not in seen_schedules:
            seen_schedules.add(schedule_id)
            continue

        replacement_id = uuid4()
        connection.execute(
            sa.text(
                """
                INSERT INTO schedules
                    (id, center_test_id, starts_at, ends_at, status)
                VALUES
                    (:id, :center_test_id, :starts_at, :ends_at, :status)
                """
            ),
            {
                "id": replacement_id,
                "center_test_id": row["center_test_id"],
                "starts_at": row["starts_at"],
                "ends_at": row["ends_at"],
                "status": row["status"],
            },
        )
        connection.execute(
            sa.text(
                "UPDATE bookings SET schedule_id = :schedule_id WHERE id = :booking_id"
            ),
            {"schedule_id": replacement_id, "booking_id": row["booking_id"]},
        )

    op.drop_column("schedules", "capacity")
    op.create_index(
        "uq_active_schedule_slot",
        "schedules",
        ["center_test_id", "starts_at"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING', 'CONFIRMED')"),
    )
    op.create_unique_constraint(
        "uq_booking_schedule",
        "bookings",
        ["schedule_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_booking_schedule", "bookings", type_="unique")
    op.drop_index("uq_active_schedule_slot", table_name="schedules")
    op.add_column(
        "schedules",
        sa.Column("capacity", sa.Integer(), server_default="1", nullable=False),
    )
    op.drop_column("schedules", "status")