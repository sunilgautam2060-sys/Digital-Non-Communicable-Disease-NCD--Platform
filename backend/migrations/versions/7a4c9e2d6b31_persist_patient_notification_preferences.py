"""Persist patient notification preferences.

Revision ID: 7a4c9e2d6b31
Revises: 2f8c1a6d4e90
Create Date: 2026-11-21
"""
from alembic import op
import sqlalchemy as sa


revision = "7a4c9e2d6b31"
down_revision = "2f8c1a6d4e90"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "patient",
        sa.Column("notification_preferences", sa.JSON(), nullable=True),
    )


def downgrade():
    op.drop_column("patient", "notification_preferences")
