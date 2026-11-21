"""Persist provider availability settings.

Revision ID: 1d6e8c3f4a20
Revises: c39a70f2d841
Create Date: 2026-11-21
"""
from alembic import op
import sqlalchemy as sa


revision = "1d6e8c3f4a20"
down_revision = "c39a70f2d841"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "provider_settings",
        sa.Column("availability_config", sa.JSON(), nullable=True),
    )


def downgrade():
    op.drop_column("provider_settings", "availability_config")
