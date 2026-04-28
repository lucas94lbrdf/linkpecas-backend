"""add stripe columns to users

Revision ID: 20260425_04
Revises: 20260425_03_repair_ads_automotive_columns
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa

revision = "20260425_04"
down_revision = "20260425_03"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("stripe_customer_id", sa.String(255), nullable=True, unique=True))
    op.add_column("users", sa.Column("stripe_subscription_id", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("subscription_status", sa.String(30), nullable=True))


def downgrade():
    op.drop_column("users", "subscription_status")
    op.drop_column("users", "stripe_subscription_id")
    op.drop_column("users", "stripe_customer_id")
