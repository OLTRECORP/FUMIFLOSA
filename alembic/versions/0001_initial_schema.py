"""0001_initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-28 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Clientes
    op.create_table(
        'clients',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('legal_name', sa.String(255), nullable=False),
        sa.Column('rfc', sa.String(13), nullable=False, unique=True),
        sa.Column('master_contract_number', sa.String(100), nullable=True),
        sa.Column('tax_regime', sa.String(100), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_clients_legal_name', 'clients', ['legal_name'])
    op.create_index('ix_clients_rfc', 'clients', ['rfc'])
    op.create_index('ix_clients_is_deleted', 'clients', ['is_deleted'])

    # 2. Sucursales
    branch_enum = sa.Enum('Habitacional', 'Comercial', 'Industrial', 'Oficinas', 'Hospitalaria', name='branchclassification')
    op.create_table(
        'branches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('unit_code', sa.String(50), nullable=True),
        sa.Column('address', sa.String(500), nullable=False),
        sa.Column('phone', sa.String(50), nullable=False),
        sa.Column('classification', branch_enum, nullable=False),
        sa.Column('responsible_contact_name', sa.String(255), nullable=False),
        sa.Column('responsible_contact_email', sa.String(255), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_branches_client_id', 'branches', ['client_id'])
    op.create_index('ix_branches_unit_code', 'branches', ['unit_code'])
    op.create_index('ix_branches_is_deleted', 'branches', ['is_deleted'])

    # 3. Usuarios
    role_enum = sa.Enum('SuperAdmin', 'TecnicoCampo', 'ClienteMatriz', 'ClienteSucursal', name='userrole')
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('role', role_enum, nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('stps_dc3_file_url', sa.String(500), nullable=True),
        sa.Column('stps_registration_number', sa.String(100), nullable=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id'), nullable=True),
        sa.Column('branch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('branches.id'), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_is_deleted', 'users', ['is_deleted'])

    # 4. Químicos
    op.create_table(
        'chemicals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('commercial_name', sa.String(255), nullable=False),
        sa.Column('active_ingredient', sa.String(255), nullable=False),
        sa.Column('cicoplafest_number', sa.String(100), nullable=False, unique=True),
        sa.Column('authorized_dose_per_liter', sa.String(100), nullable=False),
        sa.Column('safety_interval_hours', sa.Integer(), nullable=False, default=2),
        sa.Column('compatible_methods', sa.String(255), nullable=False),
        sa.Column('toxicological_category', sa.String(50), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_chemicals_commercial_name', 'chemicals', ['commercial_name'])
    op.create_index('ix_chemicals_cicoplafest_number', 'chemicals', ['cicoplafest_number'])
    op.create_index('ix_chemicals_is_deleted', 'chemicals', ['is_deleted'])

    # 5. Órdenes de Servicio
    op.create_table(
        'service_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('folio', sa.String(100), nullable=False, unique=True),
        sa.Column('branch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('branches.id'), nullable=False),
        sa.Column('technician_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('service_start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('service_end_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('pest_crawling_insects', sa.Boolean(), nullable=False, default=False),
        sa.Column('pest_rodents', sa.Boolean(), nullable=False, default=False),
        sa.Column('pest_flying_insects', sa.Boolean(), nullable=False, default=False),
        sa.Column('pest_others', sa.String(255), nullable=True),
        sa.Column('proc_aspersion', sa.Boolean(), nullable=False, default=False),
        sa.Column('proc_baits', sa.Boolean(), nullable=False, default=False),
        sa.Column('proc_traps', sa.Boolean(), nullable=False, default=False),
        sa.Column('proc_gels', sa.Boolean(), nullable=False, default=False),
        sa.Column('proc_ulv_fogging', sa.Boolean(), nullable=False, default=False),
        sa.Column('proc_thermofogging', sa.Boolean(), nullable=False, default=False),
        sa.Column('results_summary', sa.Text(), nullable=True),
        sa.Column('observations', sa.Text(), nullable=True),
        sa.Column('client_signature_data', sa.Text(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_service_orders_folio', 'service_orders', ['folio'])
    op.create_index('ix_service_orders_branch_id', 'service_orders', ['branch_id'])
    op.create_index('ix_service_orders_technician_id', 'service_orders', ['technician_id'])
    op.create_index('ix_service_orders_is_deleted', 'service_orders', ['is_deleted'])

    # 6. Certificados
    op.create_table(
        'certificates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('service_order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('service_orders.id'), nullable=False, unique=True),
        sa.Column('certificate_folio', sa.String(100), nullable=False, unique=True),
        sa.Column('issue_date', sa.Date(), nullable=False),
        sa.Column('validity_start_date', sa.Date(), nullable=False),
        sa.Column('validity_end_date', sa.Date(), nullable=False),
        sa.Column('sanitary_license_number', sa.String(100), nullable=False),
        sa.Column('sanitary_responsible_name', sa.String(255), nullable=False),
        sa.Column('sanitary_responsible_id', sa.String(100), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_certificates_certificate_folio', 'certificates', ['certificate_folio'])
    op.create_index('ix_certificates_validity_end_date', 'certificates', ['validity_end_date'])
    op.create_index('ix_certificates_is_deleted', 'certificates', ['is_deleted'])

    # 7. Químicos Aplicados (Pivote)
    area_enum = sa.Enum('Interior', 'Exterior', 'Perimetral', name='areatype')
    op.create_table(
        'certificate_chemicals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('certificate_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('certificates.id'), nullable=False),
        sa.Column('chemical_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('chemicals.id'), nullable=False),
        sa.Column('dose_applied', sa.String(100), nullable=False),
        sa.Column('area_type', area_enum, nullable=False),
        sa.Column('treated_zones_description', sa.String(255), nullable=False),
        sa.Column('application_method', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_certificate_chemicals_certificate_id', 'certificate_chemicals', ['certificate_id'])
    op.create_index('ix_certificate_chemicals_chemical_id', 'certificate_chemicals', ['chemical_id'])


def downgrade() -> None:
    op.drop_table('certificate_chemicals')
    op.drop_table('certificates')
    op.drop_table('service_orders')
    op.drop_table('chemicals')
    op.drop_table('users')
    op.drop_table('branches')
    op.drop_table('clients')
