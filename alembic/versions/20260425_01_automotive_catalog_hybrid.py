"""automotive catalog hybrid support

Revision ID: 20260425_01
Revises: None
Create Date: 2026-04-25 09:40:00
"""

from alembic import op


revision = "20260425_01"
down_revision = None
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

    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_manufacturers_slug ON manufacturers (slug)")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_vehicle_models_manufacturer_slug ON vehicle_models (manufacturer_id, slug)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_vehicle_models_manufacturer ON vehicle_models (manufacturer_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_vehicle_years_model ON vehicle_years (model_id)")

    op.execute("ALTER TABLE ads ADD COLUMN IF NOT EXISTS is_universal BOOLEAN")
    op.execute("ALTER TABLE ads ADD COLUMN IF NOT EXISTS manufacturer_id UUID")
    op.execute("ALTER TABLE ads ADD COLUMN IF NOT EXISTS model_id UUID")
    op.execute("ALTER TABLE ads ADD COLUMN IF NOT EXISTS year_start INTEGER")
    op.execute("ALTER TABLE ads ADD COLUMN IF NOT EXISTS year_end INTEGER")
    op.execute("ALTER TABLE ads ADD COLUMN IF NOT EXISTS engine VARCHAR(80)")

    op.execute("UPDATE ads SET is_universal = TRUE WHERE is_universal IS NULL")
    op.execute(
        """
        UPDATE ads
        SET is_universal = TRUE,
            manufacturer_id = NULL,
            model_id = NULL,
            year_start = NULL,
            year_end = NULL,
            engine = NULL
        WHERE manufacturer_id IS NULL OR model_id IS NULL
        """
    )

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

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'ck_ads_year_start_min'
            ) THEN
                ALTER TABLE ads
                ADD CONSTRAINT ck_ads_year_start_min
                CHECK (year_start IS NULL OR year_start >= 1900);
            END IF;
        END $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'ck_ads_year_end_gte_year_start'
            ) THEN
                ALTER TABLE ads
                ADD CONSTRAINT ck_ads_year_end_gte_year_start
                CHECK (year_end IS NULL OR year_start IS NULL OR year_end >= year_start);
            END IF;
        END $$;
        """
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ads_vehicle_lookup ON ads (manufacturer_id, model_id, year_start, year_end, status)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_ads_is_universal_status ON ads (is_universal, status)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_ads_is_universal_status")
    op.execute("DROP INDEX IF EXISTS ix_ads_vehicle_lookup")

    op.execute("ALTER TABLE ads DROP CONSTRAINT IF EXISTS ck_ads_year_end_gte_year_start")
    op.execute("ALTER TABLE ads DROP CONSTRAINT IF EXISTS ck_ads_year_start_min")
    op.execute("ALTER TABLE ads DROP CONSTRAINT IF EXISTS fk_ads_model_id_vehicle_models")
    op.execute("ALTER TABLE ads DROP CONSTRAINT IF EXISTS fk_ads_manufacturer_id_manufacturers")

    op.execute("ALTER TABLE ads DROP COLUMN IF EXISTS engine")
    op.execute("ALTER TABLE ads DROP COLUMN IF EXISTS year_end")
    op.execute("ALTER TABLE ads DROP COLUMN IF EXISTS year_start")
    op.execute("ALTER TABLE ads DROP COLUMN IF EXISTS model_id")
    op.execute("ALTER TABLE ads DROP COLUMN IF EXISTS manufacturer_id")
    op.execute("ALTER TABLE ads DROP COLUMN IF EXISTS is_universal")

    op.execute("DROP INDEX IF EXISTS ix_vehicle_years_model")
    op.execute("DROP INDEX IF EXISTS ix_vehicle_models_manufacturer")
    op.execute("DROP INDEX IF EXISTS uq_vehicle_models_manufacturer_slug")
    op.execute("DROP INDEX IF EXISTS uq_manufacturers_slug")

    op.execute("DROP TABLE IF EXISTS vehicle_years")
    op.execute("DROP TABLE IF EXISTS vehicle_models")
    op.execute("DROP TABLE IF EXISTS manufacturers")
