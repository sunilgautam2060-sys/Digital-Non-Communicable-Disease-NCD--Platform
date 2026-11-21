"""Add patient medication tracking and daily intake logs.

Revision ID: 2f8c1a6d4e90
Revises: 1d6e8c3f4a20
Create Date: 2026-11-21
"""
from alembic import op
import sqlalchemy as sa


revision = "2f8c1a6d4e90"
down_revision = "1d6e8c3f4a20"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "medication",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("dose", sa.String(length=80), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patient.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_medication_patient_id", "medication", ["patient_id"])
    op.create_table(
        "medication_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("medication_id", sa.Integer(), nullable=False),
        sa.Column("intake_date", sa.Date(), nullable=False),
        sa.Column("taken_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["medication_id"], ["medication.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("medication_id", "intake_date", name="uq_medication_log_medication_date"),
    )
    op.create_index("ix_medication_log_medication_id", "medication_log", ["medication_id"])


def downgrade():
    op.drop_index("ix_medication_log_medication_id", table_name="medication_log")
    op.drop_table("medication_log")
    op.drop_index("ix_medication_patient_id", table_name="medication")
    op.drop_table("medication")
