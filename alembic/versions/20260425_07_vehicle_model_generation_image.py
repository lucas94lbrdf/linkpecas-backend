"""add generation and image_url to vehicle_models

Revision ID: 20260425_07
Revises: 20260425_06
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa

revision = "20260425_07"
down_revision = "20260425_06"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("vehicle_models", sa.Column("generation", sa.String(100), nullable=True))
    op.add_column("vehicle_models", sa.Column("image_url",  sa.String(500), nullable=True))


def downgrade():
    op.drop_column("vehicle_models", "image_url")
    op.drop_column("vehicle_models", "generation")
