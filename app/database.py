from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Ajustar compatibilidad de URL en caso de que Render use postgres:// en lugar de postgresql://
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

if "sqlite" in db_url:
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False}
    )
else:
    # Intentar conexión con PostgreSQL y auto-fallback a SQLite si la base de datos local no está disponible
    try:
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10
        )
        with engine.connect() as test_conn:
            pass
    except Exception as pg_err:
        print(f"[DATABASE ADAPTER]: PostgreSQL no disponible ({pg_err}). Activando SQLite de respaldo 'sqlite:///./fumiflosa.db'.")
        sqlite_url = "sqlite:///./fumiflosa.db"
        engine = create_engine(
            sqlite_url,
            connect_args={"check_same_thread": False}
        )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def auto_migrate_schema(db_engine=None):
    """Ejecuta migraciones automáticas idempotentes para garantizar que todas las tablas y columnas existan en PostgreSQL / SQLite."""
    if db_engine is None:
        db_engine = engine
    try:
        from app.models import Base
        Base.metadata.create_all(bind=db_engine)
        if db_engine.dialect.name == "postgresql":
            migration_statements = [
                "ALTER TABLE IF EXISTS alembic_version ALTER COLUMN version_num TYPE VARCHAR(128);",
                
                # company_configs
                "ALTER TABLE IF EXISTS company_configs ADD COLUMN IF NOT EXISTS trade_name VARCHAR(255);",
                "ALTER TABLE IF EXISTS company_configs ADD COLUMN IF NOT EXISTS legal_name VARCHAR(255);",
                "ALTER TABLE IF EXISTS company_configs ADD COLUMN IF NOT EXISTS rfc VARCHAR(13);",
                "ALTER TABLE IF EXISTS company_configs ADD COLUMN IF NOT EXISTS sanitary_license_number VARCHAR(100);",
                "ALTER TABLE IF EXISTS company_configs ADD COLUMN IF NOT EXISTS sanitary_responsible_name VARCHAR(255);",
                "ALTER TABLE IF EXISTS company_configs ADD COLUMN IF NOT EXISTS sanitary_responsible_id VARCHAR(100);",
                "ALTER TABLE IF EXISTS company_configs ADD COLUMN IF NOT EXISTS tax_regime VARCHAR(100);",
                "ALTER TABLE IF EXISTS company_configs ADD COLUMN IF NOT EXISTS fiscal_address VARCHAR(500);",
                "ALTER TABLE IF EXISTS company_configs ADD COLUMN IF NOT EXISTS phone VARCHAR(50);",
                "ALTER TABLE IF EXISTS company_configs ADD COLUMN IF NOT EXISTS email VARCHAR(255);",
                "ALTER TABLE IF EXISTS company_configs ADD COLUMN IF NOT EXISTS sintox_phone VARCHAR(50);",
                "ALTER TABLE IF EXISTS company_configs ADD COLUMN IF NOT EXISTS stps_approval_number VARCHAR(100);",
                "ALTER TABLE IF EXISTS company_configs ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE IF EXISTS company_configs ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;",

                # company_settings (FIEL / e.firma)
                "ALTER TABLE IF EXISTS company_settings ADD COLUMN IF NOT EXISTS company_name VARCHAR(255) DEFAULT 'FUMIFLOSA - CONTROL INTEGRAL DE PLAGAS';",
                "ALTER TABLE IF EXISTS company_settings ADD COLUMN IF NOT EXISTS company_rfc VARCHAR(13) DEFAULT 'FUM200101XYZ';",
                "ALTER TABLE IF EXISTS company_settings ADD COLUMN IF NOT EXISTS sanitary_license_number VARCHAR(100) DEFAULT '2023-15A-099';",
                "ALTER TABLE IF EXISTS company_settings ADD COLUMN IF NOT EXISTS sanitary_responsible_name VARCHAR(255) DEFAULT 'Biól. Roberto Sánchez Martínez';",
                "ALTER TABLE IF EXISTS company_settings ADD COLUMN IF NOT EXISTS sanitary_responsible_id VARCHAR(100) DEFAULT 'CED-8849201';",
                "ALTER TABLE IF EXISTS company_settings ADD COLUMN IF NOT EXISTS fiel_certificate_der BYTEA;",
                "ALTER TABLE IF EXISTS company_settings ADD COLUMN IF NOT EXISTS fiel_private_key_der BYTEA;",
                "ALTER TABLE IF EXISTS company_settings ADD COLUMN IF NOT EXISTS fiel_serial_number VARCHAR(100);",
                "ALTER TABLE IF EXISTS company_settings ADD COLUMN IF NOT EXISTS fiel_valid_from TIMESTAMPTZ;",
                "ALTER TABLE IF EXISTS company_settings ADD COLUMN IF NOT EXISTS fiel_valid_to TIMESTAMPTZ;",
                "ALTER TABLE IF EXISTS company_settings ADD COLUMN IF NOT EXISTS fiel_rfc VARCHAR(20);",
                "ALTER TABLE IF EXISTS company_settings ADD COLUMN IF NOT EXISTS fiel_holder_name VARCHAR(255);",
                "ALTER TABLE IF EXISTS company_settings ADD COLUMN IF NOT EXISTS is_fiel_active BOOLEAN DEFAULT FALSE;",

                # users
                "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS username VARCHAR(100);",
                "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS email VARCHAR(255);",
                "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255);",
                "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255);",
                "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS role VARCHAR(50);",
                "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
                "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS stps_dc3_file_url VARCHAR(500);",
                "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS stps_registration_number VARCHAR(100);",
                "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS client_id UUID;",
                "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS branch_id UUID;",
                "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;",
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username);",

                # clients
                "ALTER TABLE IF EXISTS clients ADD COLUMN IF NOT EXISTS legal_name VARCHAR(255);",
                "ALTER TABLE IF EXISTS clients ADD COLUMN IF NOT EXISTS rfc VARCHAR(13);",
                "ALTER TABLE IF EXISTS clients ADD COLUMN IF NOT EXISTS master_contract_number VARCHAR(100);",
                "ALTER TABLE IF EXISTS clients ADD COLUMN IF NOT EXISTS tax_regime VARCHAR(100);",
                "ALTER TABLE IF EXISTS clients ADD COLUMN IF NOT EXISTS portal_slug VARCHAR(100);",
                "ALTER TABLE IF EXISTS clients ADD COLUMN IF NOT EXISTS portal_password VARCHAR(255);",
                "ALTER TABLE IF EXISTS clients ADD COLUMN IF NOT EXISTS portal_is_enabled BOOLEAN DEFAULT TRUE;",
                "ALTER TABLE IF EXISTS clients ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE IF EXISTS clients ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;",
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_clients_portal_slug ON clients (portal_slug);",

                # branches
                "ALTER TABLE IF EXISTS branches ADD COLUMN IF NOT EXISTS name VARCHAR(255);",
                "ALTER TABLE IF EXISTS branches ADD COLUMN IF NOT EXISTS unit_code VARCHAR(50);",
                "ALTER TABLE IF EXISTS branches ADD COLUMN IF NOT EXISTS address VARCHAR(500);",
                "ALTER TABLE IF EXISTS branches ADD COLUMN IF NOT EXISTS phone VARCHAR(50);",
                "ALTER TABLE IF EXISTS branches ADD COLUMN IF NOT EXISTS classification VARCHAR(50) DEFAULT 'COMERCIAL';",
                "ALTER TABLE IF EXISTS branches ADD COLUMN IF NOT EXISTS responsible_contact_name VARCHAR(255);",
                "ALTER TABLE IF EXISTS branches ADD COLUMN IF NOT EXISTS responsible_contact_email VARCHAR(255);",
                "ALTER TABLE IF EXISTS branches ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE IF EXISTS branches ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;",

                # chemicals
                "ALTER TABLE IF EXISTS chemicals ADD COLUMN IF NOT EXISTS commercial_name VARCHAR(255);",
                "ALTER TABLE IF EXISTS chemicals ADD COLUMN IF NOT EXISTS active_ingredient VARCHAR(255);",
                "ALTER TABLE IF EXISTS chemicals ADD COLUMN IF NOT EXISTS cicoplafest_number VARCHAR(100);",
                "ALTER TABLE IF EXISTS chemicals ADD COLUMN IF NOT EXISTS authorized_dose_per_liter VARCHAR(100);",
                "ALTER TABLE IF EXISTS chemicals ADD COLUMN IF NOT EXISTS safety_interval_hours INTEGER DEFAULT 2;",
                "ALTER TABLE IF EXISTS chemicals ADD COLUMN IF NOT EXISTS compatible_methods VARCHAR(255);",
                "ALTER TABLE IF EXISTS chemicals ADD COLUMN IF NOT EXISTS toxicological_category VARCHAR(50);",
                "ALTER TABLE IF EXISTS chemicals ADD COLUMN IF NOT EXISTS technical_sheet_url VARCHAR(500);",
                "ALTER TABLE IF EXISTS chemicals ADD COLUMN IF NOT EXISTS safety_sheet_url VARCHAR(500);",
                "ALTER TABLE IF EXISTS chemicals ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE IF EXISTS chemicals ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;",

                # rsco_items
                "ALTER TABLE IF EXISTS rsco_items ADD COLUMN IF NOT EXISTS commercial_name VARCHAR(255);",
                "ALTER TABLE IF EXISTS rsco_items ADD COLUMN IF NOT EXISTS active_ingredient VARCHAR(255);",
                "ALTER TABLE IF EXISTS rsco_items ADD COLUMN IF NOT EXISTS cicoplafest_number VARCHAR(100);",
                "ALTER TABLE IF EXISTS rsco_items ADD COLUMN IF NOT EXISTS formulation VARCHAR(100);",
                "ALTER TABLE IF EXISTS rsco_items ADD COLUMN IF NOT EXISTS manufacturer VARCHAR(255);",
                "ALTER TABLE IF EXISTS rsco_items ADD COLUMN IF NOT EXISTS authorized_dose VARCHAR(150);",
                "ALTER TABLE IF EXISTS rsco_items ADD COLUMN IF NOT EXISTS target_pests VARCHAR(500);",
                "ALTER TABLE IF EXISTS rsco_items ADD COLUMN IF NOT EXISTS toxicological_category VARCHAR(100);",
                "ALTER TABLE IF EXISTS rsco_items ADD COLUMN IF NOT EXISTS safety_interval_hours INTEGER DEFAULT 2;",
                "ALTER TABLE IF EXISTS rsco_items ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
                "ALTER TABLE IF EXISTS rsco_items ADD COLUMN IF NOT EXISTS technical_sheet_url VARCHAR(500);",
                "ALTER TABLE IF EXISTS rsco_items ADD COLUMN IF NOT EXISTS safety_sheet_url VARCHAR(500);",
                "ALTER TABLE IF EXISTS rsco_items ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE IF EXISTS rsco_items ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;",

                # service_orders
                "ALTER TABLE IF EXISTS service_orders ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'completed';",
                "ALTER TABLE IF EXISTS service_orders ADD COLUMN IF NOT EXISTS scheduled_for TIMESTAMPTZ;",
                "ALTER TABLE IF EXISTS service_orders ADD COLUMN IF NOT EXISTS pest_crawling_insects BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE IF EXISTS service_orders ADD COLUMN IF NOT EXISTS pest_rodents BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE IF EXISTS service_orders ADD COLUMN IF NOT EXISTS pest_flying_insects BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE IF EXISTS service_orders ADD COLUMN IF NOT EXISTS pest_others VARCHAR(255);",
                "ALTER TABLE IF EXISTS service_orders ADD COLUMN IF NOT EXISTS proc_aspersion BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE IF EXISTS service_orders ADD COLUMN IF NOT EXISTS proc_baits BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE IF EXISTS service_orders ADD COLUMN IF NOT EXISTS proc_traps BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE IF EXISTS service_orders ADD COLUMN IF NOT EXISTS proc_gels BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE IF EXISTS service_orders ADD COLUMN IF NOT EXISTS proc_ulv_fogging BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE IF EXISTS service_orders ADD COLUMN IF NOT EXISTS proc_thermofogging BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE IF EXISTS service_orders ADD COLUMN IF NOT EXISTS results_summary TEXT;",
                "ALTER TABLE IF EXISTS service_orders ADD COLUMN IF NOT EXISTS observations TEXT;",
                "ALTER TABLE IF EXISTS service_orders ADD COLUMN IF NOT EXISTS client_signature_data TEXT;",
                "ALTER TABLE IF EXISTS service_orders ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE IF EXISTS service_orders ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;",

                # certificates
                "ALTER TABLE IF EXISTS certificates ADD COLUMN IF NOT EXISTS certificate_folio VARCHAR(100);",
                "ALTER TABLE IF EXISTS certificates ADD COLUMN IF NOT EXISTS issue_date DATE;",
                "ALTER TABLE IF EXISTS certificates ADD COLUMN IF NOT EXISTS validity_start_date DATE;",
                "ALTER TABLE IF EXISTS certificates ADD COLUMN IF NOT EXISTS validity_end_date DATE;",
                "ALTER TABLE IF EXISTS certificates ADD COLUMN IF NOT EXISTS sanitary_license_number VARCHAR(100);",
                "ALTER TABLE IF EXISTS certificates ADD COLUMN IF NOT EXISTS sanitary_responsible_name VARCHAR(255);",
                "ALTER TABLE IF EXISTS certificates ADD COLUMN IF NOT EXISTS sanitary_responsible_id VARCHAR(100);",
                "ALTER TABLE IF EXISTS certificates ADD COLUMN IF NOT EXISTS is_signed BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE IF EXISTS certificates ADD COLUMN IF NOT EXISTS signed_at TIMESTAMPTZ;",
                "ALTER TABLE IF EXISTS certificates ADD COLUMN IF NOT EXISTS digital_signature_seal TEXT;",
                "ALTER TABLE IF EXISTS certificates ADD COLUMN IF NOT EXISTS certificate_serial_number VARCHAR(100);",
                "ALTER TABLE IF EXISTS certificates ADD COLUMN IF NOT EXISTS original_chain TEXT;",
                "ALTER TABLE IF EXISTS certificates ADD COLUMN IF NOT EXISTS signed_by_name VARCHAR(255);",
                "ALTER TABLE IF EXISTS certificates ADD COLUMN IF NOT EXISTS signed_by_rfc VARCHAR(20);",
                "ALTER TABLE IF EXISTS certificates ADD COLUMN IF NOT EXISTS verification_uuid VARCHAR(100);",
                "ALTER TABLE IF EXISTS certificates ADD COLUMN IF NOT EXISTS is_cancelled BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE IF EXISTS certificates ADD COLUMN IF NOT EXISTS cancellation_reason VARCHAR(500);",
                "ALTER TABLE IF EXISTS certificates ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;",
                "ALTER TABLE IF EXISTS certificates ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE IF EXISTS certificates ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;",

                # certificate_chemicals
                "ALTER TABLE IF EXISTS certificate_chemicals ADD COLUMN IF NOT EXISTS dose_applied VARCHAR(100);",
                "ALTER TABLE IF EXISTS certificate_chemicals ADD COLUMN IF NOT EXISTS area_type VARCHAR(50);",
                "ALTER TABLE IF EXISTS certificate_chemicals ADD COLUMN IF NOT EXISTS treated_zones_description VARCHAR(255);",
                "ALTER TABLE IF EXISTS certificate_chemicals ADD COLUMN IF NOT EXISTS application_method VARCHAR(100);"
            ]

            with db_engine.begin() as conn:
                for stmt in migration_statements:
                    try:
                        conn.execute(text(stmt))
                    except Exception as col_err:
                        print(f"[SCHEMA AUTO-MIGRATE WARNING]: {stmt} -> {col_err}")

    except Exception as e:
        print(f"[SCHEMA AUTO-MIGRATE ERROR]: {e}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
