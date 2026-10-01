"""0005_add_rsco_and_bitacoras

Revision ID: 0005_add_rsco_and_bitacoras
Revises: 0004_add_cancellation_and_scheduling
Create Date: 2026-09-30 19:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005_add_rsco_and_bitacoras'
down_revision: Union[str, None] = '0004_cancel_and_schedule'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tabla de Catálogo RSCO en Línea
    op.execute("""
    CREATE TABLE IF NOT EXISTS rsco_items (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        commercial_name VARCHAR(255) NOT NULL,
        active_ingredient VARCHAR(255) NOT NULL,
        cicoplafest_number VARCHAR(100) UNIQUE NOT NULL,
        formulation VARCHAR(100) NOT NULL DEFAULT 'Suspensión Concentrada',
        manufacturer VARCHAR(255) NOT NULL DEFAULT 'N/A',
        authorized_dose VARCHAR(150) NOT NULL DEFAULT '10 a 20 ml / L de agua',
        target_pests VARCHAR(500) NOT NULL DEFAULT 'Cucarachas, Chinches, Hormigas, Moscas',
        toxicological_category VARCHAR(100) NOT NULL DEFAULT 'Banda Verde / Precaución',
        safety_interval_hours INTEGER NOT NULL DEFAULT 2,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
        deleted_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS ix_rsco_items_commercial_name ON rsco_items (commercial_name);
    CREATE INDEX IF NOT EXISTS ix_rsco_items_active_ingredient ON rsco_items (active_ingredient);
    CREATE INDEX IF NOT EXISTS ix_rsco_items_cicoplafest ON rsco_items (cicoplafest_number);
    """)

    # 2. Bitácora de Entrega y Mantenimiento de EPP
    op.execute("""
    CREATE TABLE IF NOT EXISTS epp_logs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        technician_name VARCHAR(255) NOT NULL,
        equipment_category VARCHAR(100) NOT NULL,
        equipment_item VARCHAR(255) NOT NULL,
        condition_type VARCHAR(50) NOT NULL DEFAULT 'NUEVO',
        delivery_date DATE NOT NULL DEFAULT CURRENT_DATE,
        change_date DATE,
        change_interval VARCHAR(50),
        change_time VARCHAR(50),
        responsible_signature VARCHAR(255),
        notes TEXT,
        is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
        deleted_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS ix_epp_logs_technician ON epp_logs (technician_name);
    """)

    # 3. Matriz Anual de EPP por Técnico
    op.execute("""
    CREATE TABLE IF NOT EXISTS epp_annual_matrix (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        technician_name VARCHAR(255) NOT NULL,
        year INTEGER NOT NULL DEFAULT 2026,
        epp_item VARCHAR(150) NOT NULL,
        frequency VARCHAR(100) NOT NULL,
        jan_date VARCHAR(50),
        jan_signed BOOLEAN NOT NULL DEFAULT FALSE,
        feb_date VARCHAR(50),
        feb_signed BOOLEAN NOT NULL DEFAULT FALSE,
        mar_date VARCHAR(50),
        mar_signed BOOLEAN NOT NULL DEFAULT FALSE,
        apr_date VARCHAR(50),
        apr_signed BOOLEAN NOT NULL DEFAULT FALSE,
        may_date VARCHAR(50),
        may_signed BOOLEAN NOT NULL DEFAULT FALSE,
        jun_date VARCHAR(50),
        jun_signed BOOLEAN NOT NULL DEFAULT FALSE,
        jul_date VARCHAR(50),
        jul_signed BOOLEAN NOT NULL DEFAULT FALSE,
        aug_date VARCHAR(50),
        aug_signed BOOLEAN NOT NULL DEFAULT FALSE,
        sep_date VARCHAR(50),
        sep_signed BOOLEAN NOT NULL DEFAULT FALSE,
        oct_date VARCHAR(50),
        oct_signed BOOLEAN NOT NULL DEFAULT FALSE,
        nov_date VARCHAR(50),
        nov_signed BOOLEAN NOT NULL DEFAULT FALSE,
        dec_date VARCHAR(50),
        dec_signed BOOLEAN NOT NULL DEFAULT FALSE,
        is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
        deleted_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS ix_epp_annual_tech_year ON epp_annual_matrix (technician_name, year);
    """)

    # 4. Bitácora de Calibración de Equipos de Aplicación
    op.execute("""
    CREATE TABLE IF NOT EXISTS equipment_calibration_logs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        equipment_name VARCHAR(255) NOT NULL,
        serial_number VARCHAR(100),
        nozzle_type VARCHAR(100) NOT NULL DEFAULT 'Abanico Plano 8002',
        working_pressure_psi VARCHAR(50) DEFAULT '40 psi',
        flow_rate_lpm VARCHAR(50) DEFAULT '0.75 L/min',
        status VARCHAR(50) NOT NULL DEFAULT 'OPERATIVO',
        calibration_date DATE NOT NULL DEFAULT CURRENT_DATE,
        next_calibration_date DATE,
        technician_name VARCHAR(255) NOT NULL,
        observations TEXT,
        is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
        deleted_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """)

    # 5. Bitácora de Monitoreo de Estaciones y Cebaderos
    op.execute("""
    CREATE TABLE IF NOT EXISTS station_monitoring_logs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        branch_name VARCHAR(255) NOT NULL,
        station_number VARCHAR(50) NOT NULL,
        station_type VARCHAR(100) NOT NULL DEFAULT 'Cebadero de Roedor',
        zone VARCHAR(150) NOT NULL DEFAULT 'Exterior - Perímetro',
        bait_consumption_percent INTEGER NOT NULL DEFAULT 0,
        pest_activity_detected BOOLEAN NOT NULL DEFAULT FALSE,
        pest_count INTEGER NOT NULL DEFAULT 0,
        pest_type VARCHAR(150),
        corrective_action VARCHAR(255),
        monitoring_date DATE NOT NULL DEFAULT CURRENT_DATE,
        technician_name VARCHAR(255) NOT NULL,
        is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
        deleted_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """)

    # 6. Bitácora de Residuos Peligrosos y Triple Lavado
    op.execute("""
    CREATE TABLE IF NOT EXISTS hazardous_waste_logs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        chemical_name VARCHAR(255) NOT NULL,
        active_ingredient VARCHAR(255) NOT NULL,
        containers_count INTEGER NOT NULL DEFAULT 1,
        container_capacity VARCHAR(100) NOT NULL DEFAULT '1 Litro',
        triple_wash_performed BOOLEAN NOT NULL DEFAULT TRUE,
        containers_perforated BOOLEAN NOT NULL DEFAULT TRUE,
        wash_date DATE NOT NULL DEFAULT CURRENT_DATE,
        temporary_storage_location VARCHAR(255) NOT NULL DEFAULT 'Área de Residuos FUMIFLOSA',
        disposal_manifest_number VARCHAR(150),
        responsible_name VARCHAR(255) NOT NULL,
        is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
        deleted_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """)


def downgrade() -> None:
    op.drop_table('hazardous_waste_logs')
    op.drop_table('station_monitoring_logs')
    op.drop_table('equipment_calibration_logs')
    op.drop_table('epp_annual_matrix')
    op.drop_table('epp_logs')
    op.drop_table('rsco_items')
