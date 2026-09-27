"""Replace booking timestamps with persisted schedule slots.

Revision ID: c4e8a1f2d7b3
Revises: 9b7d31a4c2e8
Create Date: 2026-09-26

"""
from typing import Sequence, Union
from datetime import timedelta
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision: str = "c4e8a1f2d7b3"
down_revision: Union[str, Sequence[str], None] = "9b7d31a4c2e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "schedules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("center_test_id", sa.UUID(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("ends_at > starts_at", name="ck_schedule_end_after_start"),
        sa.CheckConstraint("capacity > 0", name="ck_schedule_capacity_positive"),
        sa.ForeignKeyConstraint(
            ["center_test_id"], ["center_tests.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "center_test_id",
            "starts_at",
            name="uq_schedule_center_test_start",
        ),
    )
    op.create_index(
        op.f("ix_schedules_center_test_id"),
        "schedules",
        ["center_test_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_schedules_starts_at"),
        "schedules",
        ["starts_at"],
        unique=False,
    )

    op.add_column("bookings", sa.Column("schedule_id", sa.UUID(), nullable=True))

    connection = op.get_bind()
    old_bookings = connection.execute(
        sa.text(
            """
            SELECT center_test_id, appointment_at, COUNT(*) AS booking_count
            FROM bookings
            GROUP BY center_test_id, appointment_at
            """
        )
    ).mappings()

    for booking in old_bookings:
        schedule_id = uuid4()
        connection.execute(
            sa.text(
                """
                INSERT INTO schedules
                    (id, center_test_id, starts_at, ends_at, capacity)
                VALUES
                    (:id, :center_test_id, :starts_at, :ends_at, :capacity)
                """
            ),
            {
                "id": schedule_id,
                "center_test_id": booking["center_test_id"],
                "starts_at": booking["appointment_at"],
                "ends_at": booking["appointment_at"] + timedelta(minutes=30),
                "capacity": max(1, booking["booking_count"]),
            },
        )
        connection.execute(
            sa.text(
                """
                UPDATE bookings
                SET schedule_id = :schedule_id
                WHERE center_test_id = :center_test_id
                  AND appointment_at = :appointment_at
                """
            ),
            {
                "schedule_id": schedule_id,
                "center_test_id": booking["center_test_id"],
                "appointment_at": booking["appointment_at"],
            },
        )

    op.alter_column("bookings", "schedule_id", nullable=False)
    op.create_foreign_key(
        "fk_bookings_schedule_id",
        "bookings",
        "schedules",
        ["schedule_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(op.f("ix_bookings_schedule_id"), "bookings", ["schedule_id"])
    op.drop_index(op.f("ix_bookings_center_test_id"), table_name="bookings")
    op.drop_index(op.f("ix_bookings_appointment_at"), table_name="bookings")
    op.drop_column("bookings", "center_test_id")
    op.drop_column("bookings", "appointment_at")


def downgrade() -> None:
    op.add_column(
        "bookings",
        sa.Column("center_test_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "bookings",
        sa.Column("appointment_at", sa.DateTime(timezone=True), nullable=True),
    )
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE bookings AS b
            SET center_test_id = s.center_test_id,
                appointment_at = s.starts_at
            FROM schedules AS s
            WHERE b.schedule_id = s.id
            """
        )
    )
    op.alter_column("bookings", "center_test_id", nullable=False)
    op.alter_column("bookings", "appointment_at", nullable=False)
    op.create_index(op.f("ix_bookings_center_test_id"), "bookings", ["center_test_id"])
    op.create_index(op.f("ix_bookings_appointment_at"), "bookings", ["appointment_at"])
    op.drop_index(op.f("ix_bookings_schedule_id"), table_name="bookings")
    op.drop_constraint("fk_bookings_schedule_id", "bookings", type_="foreignkey")
    op.drop_column("bookings", "schedule_id")
    op.drop_index(op.f("ix_schedules_starts_at"), table_name="schedules")
    op.drop_index(op.f("ix_schedules_center_test_id"), table_name="schedules")
    op.drop_table("schedules")