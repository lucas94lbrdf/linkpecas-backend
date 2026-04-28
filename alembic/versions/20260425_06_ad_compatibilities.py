"""create ad_compatibilities table

Revision ID: 20260425_06
Revises: 20260425_05
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "20260425_06"
down_revision = "20260425_05"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ad_compatibilities",
        sa.Column("id",              UUID(as_uuid=True), primary_key=True),
        sa.Column("ad_id",           UUID(as_uuid=True), sa.ForeignKey("ads.id",              ondelete="CASCADE"),   nullable=False),
        sa.Column("manufacturer_id", UUID(as_uuid=True), sa.ForeignKey("manufacturers.id",    ondelete="SET NULL"),  nullable=True),
        sa.Column("model_id",        UUID(as_uuid=True), sa.ForeignKey("vehicle_models.id",   ondelete="SET NULL"),  nullable=True),
        sa.Column("year_start",  sa.Integer,     nullable=True),
        sa.Column("year_end",    sa.Integer,     nullable=True),
        sa.Column("engine",      sa.String(80),  nullable=True),
        sa.Column("note",        sa.String(255), nullable=True),
        sa.Column("created_at",  sa.DateTime,    server_default=sa.func.now()),
    )
    op.create_index("ix_ad_compatibilities_ad_id", "ad_compatibilities", ["ad_id"])

    # Migra compatibilidades já existentes nas ads (manufacturer_id/model_id preenchidos)
    op.execute("""
        INSERT INTO ad_compatibilities (id, ad_id, manufacturer_id, model_id, year_start, year_end, engine)
        SELECT gen_random_uuid(), id, manufacturer_id, model_id, year_start, year_end, engine
        FROM ads
        WHERE is_universal = false
          AND manufacturer_id IS NOT NULL
          AND model_id IS NOT NULL
    """)


def downgrade():
    op.drop_index("ix_ad_compatibilities_ad_id", "ad_compatibilities")
    op.drop_table("ad_compatibilities")
