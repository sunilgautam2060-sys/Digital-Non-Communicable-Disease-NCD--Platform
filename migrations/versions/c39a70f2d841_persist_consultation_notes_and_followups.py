"""Persist optional appointment links and date-only follow-ups.

Revision ID: c39a70f2d841
Revises: b7c4d2e91a63
Create Date: 2026-11-21
"""
from alembic import op
import sqlalchemy as sa


revision = "c39a70f2d841"
down_revision = "b7c4d2e91a63"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("consultation_note", sa.Column("appointment_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_consultation_note_appointment",
        "consultation_note",
        "appointment",
        ["appointment_id"],
        ["id"],
    )
    op.add_column("follow_up", sa.Column("appointment_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_follow_up_appointment",
        "follow_up",
        "appointment",
        ["appointment_id"],
        ["id"],
    )
    op.alter_column(
        "follow_up",
        "follow_up_time",
        existing_type=sa.Time(),
        nullable=True,
    )


def downgrade():
    op.alter_column(
        "follow_up",
        "follow_up_time",
        existing_type=sa.Time(),
        nullable=False,
    )
    op.drop_constraint("fk_follow_up_appointment", "follow_up", type_="foreignkey")
    op.drop_column("follow_up", "appointment_id")
    op.drop_constraint("fk_consultation_note_appointment", "consultation_note", type_="foreignkey")
    op.drop_column("consultation_note", "appointment_id")
