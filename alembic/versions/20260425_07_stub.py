"""stub for existing migration 20260425_07

This migration already exists in the database but the file was lost.
This stub allows Alembic to track the chain correctly.

Revision ID: 20260425_07
Revises: 
Create Date: 2026-04-25
"""

from alembic import op
import sqlalchemy as sa

revision = '20260425_07'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Already applied — no-op stub
    pass


def downgrade():
    pass
