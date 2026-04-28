from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from app.db.session import DATABASE_URL


load_dotenv(Path(__file__).resolve().parent / ".env")


STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS manufacturers (
        id UUID PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        slug VARCHAR(100) NOT NULL UNIQUE,
        logo_url VARCHAR(500),
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
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
    """,
    """
    CREATE TABLE IF NOT EXISTS vehicle_years (
        id UUID PRIMARY KEY,
        model_id UUID NOT NULL REFERENCES vehicle_models(id) ON DELETE CASCADE,
        year INTEGER NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (model_id, year)
    )
    """,
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS status VARCHAR(30) DEFAULT 'active'",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS plan VARCHAR(30) DEFAULT 'free'",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS shop_name VARCHAR(255)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS shop_slug VARCHAR(255)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS shop_description VARCHAR(500)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS shop_location VARCHAR(255)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS shop_logo VARCHAR(500)",
    "ALTER TABLE ads ADD COLUMN IF NOT EXISTS is_universal BOOLEAN",
    "ALTER TABLE ads ADD COLUMN IF NOT EXISTS manufacturer_id UUID",
    "ALTER TABLE ads ADD COLUMN IF NOT EXISTS model_id UUID",
    "ALTER TABLE ads ADD COLUMN IF NOT EXISTS year_start INTEGER",
    "ALTER TABLE ads ADD COLUMN IF NOT EXISTS year_end INTEGER",
    "ALTER TABLE ads ADD COLUMN IF NOT EXISTS engine VARCHAR(80)",
    "UPDATE users SET status = 'active' WHERE status IS NULL",
    "UPDATE users SET plan = 'free' WHERE plan IS NULL",
    "UPDATE users SET email_verified = FALSE WHERE email_verified IS NULL",
    "UPDATE ads SET is_universal = TRUE WHERE is_universal IS NULL",
    "ALTER TABLE ads ALTER COLUMN is_universal SET DEFAULT TRUE",
    "ALTER TABLE ads ALTER COLUMN is_universal SET NOT NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_shop_slug_unique ON users (shop_slug)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_manufacturers_slug ON manufacturers (slug)",
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_vehicle_models_manufacturer_slug
    ON vehicle_models (manufacturer_id, slug)
    """,
    "CREATE INDEX IF NOT EXISTS ix_vehicle_models_manufacturer ON vehicle_models (manufacturer_id)",
    "CREATE INDEX IF NOT EXISTS ix_vehicle_years_model ON vehicle_years (model_id)",
    "CREATE INDEX IF NOT EXISTS ix_ads_is_universal_status ON ads (is_universal, status)",
    """
    CREATE INDEX IF NOT EXISTS ix_ads_vehicle_lookup
    ON ads (manufacturer_id, model_id, year_start, year_end, status)
    """,
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
    """,
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
    """,
    "CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)",
    "DELETE FROM alembic_version",
    "INSERT INTO alembic_version (version_num) VALUES ('20260425_03')",
]


def main() -> None:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    with engine.begin() as connection:
        for statement in STATEMENTS:
            connection.execute(text(statement))
    print("Schema automotivo reparado com sucesso.")


if __name__ == "__main__":
    main()
