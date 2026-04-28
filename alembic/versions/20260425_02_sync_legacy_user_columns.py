"""sync legacy user columns

Revision ID: 20260425_02
Revises: 20260425_01
Create Date: 2026-04-25 10:05:00
"""

from alembic import op


revision = "20260425_02"
down_revision = "20260425_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS status VARCHAR(30) DEFAULT 'active'")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS plan VARCHAR(30) DEFAULT 'free'")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS shop_name VARCHAR(255)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS shop_slug VARCHAR(255)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS shop_description VARCHAR(500)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS shop_location VARCHAR(255)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS shop_logo VARCHAR(500)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_shop_slug_unique ON users (shop_slug)")

    op.execute("UPDATE users SET status = 'active' WHERE status IS NULL")
    op.execute("UPDATE users SET plan = 'free' WHERE plan IS NULL")
    op.execute("UPDATE users SET email_verified = FALSE WHERE email_verified IS NULL")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_shop_slug_unique")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS shop_logo")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS shop_location")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS shop_description")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS shop_slug")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS shop_name")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS email_verified")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS plan")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS status")
