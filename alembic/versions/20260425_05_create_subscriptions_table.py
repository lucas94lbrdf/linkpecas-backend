"""subscriptions table already exists - no-op

Revision ID: 20260425_05
Revises: 20260425_04
Create Date: 2026-04-25
"""
from alembic import op

revision = "20260425_05"
down_revision = "20260425_04"
branch_labels = None
depends_on = None


def upgrade():
    pass  # tabela subscriptions já existe no banco


def downgrade():
    pass
