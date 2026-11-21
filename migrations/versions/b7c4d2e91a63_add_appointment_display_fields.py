"""Add service and location to appointments.

Revision ID: b7c4d2e91a63
Revises: 80e02a7b45bd
Create Date: 2026-11-21
"""
from alembic import op
import sqlalchemy as sa


revision = "b7c4d2e91a63"
down_revision = "80e02a7b45bd"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("appointment", sa.Column("service", sa.String(length=80), nullable=True))
    op.add_column("appointment", sa.Column("location", sa.String(length=200), nullable=True))


def downgrade():
    op.drop_column("appointment", "location")
    op.drop_column("appointment", "service")
