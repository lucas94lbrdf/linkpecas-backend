"""enrich click_events and search_logs with attribution fields

Revision ID: 20260506_track
Revises: e303dc0229c2
Create Date: 2026-05-06
"""

from alembic import op
import sqlalchemy as sa


revision = '20260506_track'
down_revision = 'e303dc0229c2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── click_events ─────────────────────────────────────────────────────────
    op.add_column('click_events', sa.Column('source_category', sa.String(length=50), nullable=True))
    op.add_column('click_events', sa.Column('utm_source', sa.String(length=100), nullable=True))
    op.add_column('click_events', sa.Column('utm_medium', sa.String(length=100), nullable=True))
    op.add_column('click_events', sa.Column('utm_campaign', sa.String(length=100), nullable=True))
    op.add_column('click_events', sa.Column('browser', sa.String(length=50), nullable=True))
    op.add_column('click_events', sa.Column('os', sa.String(length=50), nullable=True))
    op.add_column('click_events', sa.Column('country', sa.String(length=50), nullable=True))
    op.add_column('click_events', sa.Column('ip_address', sa.String(length=64), nullable=True))

    op.create_index('ix_click_events_clicked_at', 'click_events', ['clicked_at'])
    op.create_index('ix_click_events_marketplace', 'click_events', ['marketplace'])
    op.create_index('ix_click_events_source_category', 'click_events', ['source_category'])

    # ── search_logs ─────────────────────────────────────────────────────────
    op.add_column('search_logs', sa.Column('source_category', sa.String(length=50), nullable=True))
    op.add_column('search_logs', sa.Column('referrer', sa.Text(), nullable=True))
    op.add_column('search_logs', sa.Column('user_agent', sa.Text(), nullable=True))
    op.add_column('search_logs', sa.Column('device', sa.String(length=50), nullable=True))
    op.add_column('search_logs', sa.Column('browser', sa.String(length=50), nullable=True))
    op.add_column('search_logs', sa.Column('os', sa.String(length=50), nullable=True))
    op.add_column('search_logs', sa.Column('city', sa.String(length=100), nullable=True))
    op.add_column('search_logs', sa.Column('state', sa.String(length=50), nullable=True))
    op.add_column('search_logs', sa.Column('ip_address', sa.String(length=64), nullable=True))
    op.add_column('search_logs', sa.Column('ip_hash', sa.String(length=64), nullable=True))

    op.create_index('ix_search_logs_created_at', 'search_logs', ['created_at'])
    op.create_index('ix_search_logs_results_found', 'search_logs', ['results_found'])

    # ── ads.link_status: backfill 'pending_review' → 'active' (default novo) ─
    op.execute(
        "UPDATE ads SET link_status = 'active' "
        "WHERE link_status IS NULL OR link_status = 'pending_review'"
    )


def downgrade() -> None:
    op.drop_index('ix_search_logs_results_found', table_name='search_logs')
    op.drop_index('ix_search_logs_created_at', table_name='search_logs')
    op.drop_column('search_logs', 'ip_hash')
    op.drop_column('search_logs', 'ip_address')
    op.drop_column('search_logs', 'state')
    op.drop_column('search_logs', 'city')
    op.drop_column('search_logs', 'os')
    op.drop_column('search_logs', 'browser')
    op.drop_column('search_logs', 'device')
    op.drop_column('search_logs', 'user_agent')
    op.drop_column('search_logs', 'referrer')
    op.drop_column('search_logs', 'source_category')

    op.drop_index('ix_click_events_source_category', table_name='click_events')
    op.drop_index('ix_click_events_marketplace', table_name='click_events')
    op.drop_index('ix_click_events_clicked_at', table_name='click_events')
    op.drop_column('click_events', 'ip_address')
    op.drop_column('click_events', 'country')
    op.drop_column('click_events', 'os')
    op.drop_column('click_events', 'browser')
    op.drop_column('click_events', 'utm_campaign')
    op.drop_column('click_events', 'utm_medium')
    op.drop_column('click_events', 'utm_source')
    op.drop_column('click_events', 'source_category')
