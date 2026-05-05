"""link_check_and_scraping_configs

Revision ID: e303dc0229c2
Revises: 20260505_notif
Create Date: 2026-05-05 18:40:30.796237
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e303dc0229c2'
down_revision = '20260505_notif'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('scraping_configs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('marketplace', sa.String(length=50), nullable=False),
    sa.Column('base_url_pattern', sa.String(length=255), nullable=True),
    sa.Column('selectors_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('rate_limit_per_minute', sa.Integer(), nullable=True),
    sa.Column('requires_headless', sa.Boolean(), nullable=True),
    sa.Column('user_agent_pool', postgresql.ARRAY(sa.String()), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('marketplace')
    )
    op.create_table('link_checks',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('ad_id', sa.UUID(), nullable=False),
    sa.Column('external_url', sa.String(length=1000), nullable=False),
    sa.Column('marketplace', sa.String(length=50), nullable=False),
    sa.Column('http_status', sa.Integer(), nullable=True),
    sa.Column('is_available', sa.Boolean(), nullable=False),
    sa.Column('signals_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('price_found', sa.Float(), nullable=True),
    sa.Column('price_previous', sa.Float(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('check_duration_ms', sa.Integer(), nullable=True),
    sa.Column('checked_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['ad_id'], ['ads.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_link_checks_ad_id'), 'link_checks', ['ad_id'], unique=False)
    op.add_column('ads', sa.Column('last_link_check_at', sa.DateTime(), nullable=True))
    op.add_column('ads', sa.Column('link_status', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('ads', 'link_status')
    op.drop_column('ads', 'last_link_check_at')
    op.drop_index(op.f('ix_link_checks_ad_id'), table_name='link_checks')
    op.drop_table('link_checks')
    op.drop_table('scraping_configs')
    # ### end Alembic commands ###
