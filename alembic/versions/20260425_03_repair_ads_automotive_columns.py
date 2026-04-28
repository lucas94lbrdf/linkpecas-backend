"""repair ads automotive columns

Revision ID: 20260425_03
Revises: 20260425_02
Create Date: 2026-04-25 10:25:00
"""

from alembic import op


revision = "20260425_03"
down_revision = "20260425_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS manufacturers (
            id UUID PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            slug VARCHAR(100) NOT NULL UNIQUE,
            logo_url VARCHAR(500),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS vehicle_models (
            id UUID PRIMARY KEY,
            manufacturer_id UUID NOT NULL REFERENCES manufacturers(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            slug VARCHAR(100) NOT NULL,
            vehicle_type VARCHAR(50) DEFAULT 'car',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS vehicle_years (
            id UUID PRIMARY KEY,
            model_id UUID NOT NULL REFERENCES vehicle_models(id) ON DELETE CASCADE,
            year INTEGER NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (model_id, year)
        )
        """
    )

    op.execute("ALTER TABLE ads ADD COLUMN IF NOT EXISTS is_universal BOOLEAN")
    op.execute("ALTER TABLE ads ADD COLUMN IF NOT EXISTS manufacturer_id UUID")
    op.execute("ALTER TABLE ads ADD COLUMN IF NOT EXISTS model_id UUID")
    op.execute("ALTER TABLE ads ADD COLUMN IF NOT EXISTS year_start INTEGER")
    op.execute("ALTER TABLE ads ADD COLUMN IF NOT EXISTS year_end INTEGER")
    op.execute("ALTER TABLE ads ADD COLUMN IF NOT EXISTS engine VARCHAR(80)")

    op.execute("UPDATE ads SET is_universal = TRUE WHERE is_universal IS NULL")
    op.execute("ALTER TABLE ads ALTER COLUMN is_universal SET DEFAULT TRUE")
    op.execute("ALTER TABLE ads ALTER COLUMN is_universal SET NOT NULL")

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_ads_manufacturer_id_manufacturers'
            ) THEN
                ALTER TABLE ads
                ADD CONSTRAINT fk_ads_manufacturer_id_manufacturers
                FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id) ON DELETE SET NULL;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_ads_model_id_vehicle_models'
            ) THEN
                ALTER TABLE ads
                ADD CONSTRAINT fk_ads_model_id_vehicle_models
                FOREIGN KEY (model_id) REFERENCES vehicle_models(id) ON DELETE SET NULL;
            END IF;
        END $$;
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_ads_is_universal_status ON ads (is_universal, status)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ads_vehicle_lookup ON ads (manufacturer_id, model_id, year_start, year_end, status)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_ads_vehicle_lookup")
    op.execute("DROP INDEX IF EXISTS ix_ads_is_universal_status")
