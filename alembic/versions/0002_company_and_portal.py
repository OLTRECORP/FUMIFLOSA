"""0002_company_and_portal

Revision ID: 0002_company_and_portal
Revises: 0001_initial_schema
Create Date: 2026-09-29 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0002_company_and_portal'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Agregar columnas a clients para portal estático
    op.add_column('clients', sa.Column('portal_slug', sa.String(100), nullable=True))
    op.add_column('clients', sa.Column('portal_password', sa.String(255), nullable=True))
    op.add_column('clients', sa.Column('portal_is_enabled', sa.Boolean(), nullable=False, server_default='true'))
    
    # Generar slugs para clientes existentes
    op.execute("UPDATE clients SET portal_slug = substring(md5(random()::text) from 1 for 10) WHERE portal_slug IS NULL")
    
    op.alter_column('clients', 'portal_slug', nullable=False)
    op.create_index('ix_clients_portal_slug', 'clients', ['portal_slug'], unique=True)

    # 2. Crear tabla company_config
    op.create_table(
        'company_config',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('company_name', sa.String(255), nullable=False, server_default='FUMIFLOSA S.A. DE C.V.'),
        sa.Column('trade_name', sa.String(255), nullable=False, server_default='FUMIFLOSA - Control de Plagas Urbanas'),
        sa.Column('rfc', sa.String(13), nullable=False, server_default='FUM200101XYZ'),
        sa.Column('tax_regime', sa.String(100), nullable=True, server_default='601 - General de Ley Personas Morales'),
        sa.Column('fiscal_address', sa.String(500), nullable=False, server_default='Av. Insurgentes Sur 1200, Benito Juárez, CDMX, C.P. 03100'),
        sa.Column('phone', sa.String(50), nullable=False, server_default='55-1234-5678'),
        sa.Column('email', sa.String(255), nullable=False, server_default='contacto@fumiflosa.mx'),
        sa.Column('website', sa.String(255), nullable=True, server_default='https://fumiflosa.mx'),
        sa.Column('sanitary_license_number', sa.String(100), nullable=False, server_default='2023-15A-099'),
        sa.Column('sanitary_responsible_name', sa.String(255), nullable=False, server_default='Biól. Roberto Sánchez Martínez'),
        sa.Column('sanitary_responsible_id', sa.String(100), nullable=True, server_default='CED-8849201'),
        sa.Column('stps_registration_number', sa.String(100), nullable=True, server_default='FUM-STPS-DC3-2023'),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('sintox_emergency_phones', sa.String(255), nullable=False, server_default='01-800-0092800 / 800-009-2800 / CDMX 55-5598-6659'),
        sa.Column('default_reentry_hours', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('default_validity_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('terms_and_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    )


def downgrade() -> None:
    op.drop_table('company_config')
    op.drop_index('ix_clients_portal_slug', 'clients')
    op.drop_column('clients', 'portal_is_enabled')
    op.drop_column('clients', 'portal_password')
    op.drop_column('clients', 'portal_slug')
