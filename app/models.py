import uuid
from datetime import datetime, date, timezone
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import (
    String, Boolean, Text, Integer, Date, DateTime, 
    ForeignKey, Enum, LargeBinary
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class SoftDeleteMixin:
    """Mixin para auditoría y eliminación lógica estricta."""
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc), 
        nullable=False
    )


class UserRole(str, PyEnum):
    SUPERADMIN = "SuperAdmin"
    TECNICO_CAMPO = "TecnicoCampo"
    CLIENTE_MATRIZ = "ClienteMatriz"
    CLIENTE_SUCURSAL = "ClienteSucursal"


class BranchClassification(str, PyEnum):
    HABITACIONAL = "Habitacional"
    COMERCIAL = "Comercial"
    INDUSTRIAL = "Industrial"
    OFICINAS = "Oficinas"
    HOSPITALARIA = "Hospitalaria"


class AreaType(str, PyEnum):
    INTERIOR = "Interior"
    EXTERIOR = "Exterior"
    PERIMETRAL = "Perimetral"


# ============================================================================
# 1. USUARIOS Y ROLES
# ============================================================================
class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.TECNICO_CAMPO)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Requerimientos STPS para Técnicos
    stps_dc3_file_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    stps_registration_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Asignación de Cliente (para usuarios B2B)
    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)
    branch_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True)

    # Relaciones
    assigned_orders: Mapped[List["ServiceOrder"]] = relationship("ServiceOrder", back_populates="technician")
    client: Mapped[Optional["Client"]] = relationship("Client", foreign_keys=[client_id])
    branch: Mapped[Optional["Branch"]] = relationship("Branch", foreign_keys=[branch_id])


# ============================================================================
# 2. CLIENTES Y SUCURSALES (Jerarquía Institucional)
# ============================================================================
class Client(Base, TimestampMixin, SoftDeleteMixin):
    """Cliente Corporativo / Matriz (ej. IMSS Órgano de Operación Administrativa)."""
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # Razón Social
    rfc: Mapped[str] = mapped_column(String(13), unique=True, nullable=False, index=True)
    master_contract_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tax_regime: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Relaciones
    branches: Mapped[List["Branch"]] = relationship("Branch", back_populates="client", cascade="all, delete-orphan")


class Branch(Base, TimestampMixin, SoftDeleteMixin):
    """Sucursal o Unidad Operativa (ej. HGZ No. 1, UMF No. 22)."""
    __tablename__ = "branches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)  # Clave presupuestal / ID
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    classification: Mapped[BranchClassification] = mapped_column(
        Enum(BranchClassification), default=BranchClassification.COMERCIAL, nullable=False
    )
    responsible_contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    responsible_contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relaciones
    client: Mapped["Client"] = relationship("Client", back_populates="branches")
    service_orders: Mapped[List["ServiceOrder"]] = relationship("ServiceOrder", back_populates="branch")


# ============================================================================
# 3. CATÁLOGO DE QUÍMICOS (Regulado COFEPRIS / CICOPLAFEST)
# ============================================================================
class Chemical(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "chemicals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    commercial_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    active_ingredient: Mapped[str] = mapped_column(String(255), nullable=False)
    cicoplafest_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    authorized_dose_per_liter: Mapped[str] = mapped_column(String(100), nullable=False)
    safety_interval_hours: Mapped[int] = mapped_column(Integer, default=2, nullable=False)  # Tiempo de reentrada
    compatible_methods: Mapped[str] = mapped_column(String(255), nullable=False)  # ej. "Aspersión, Nebulización UBV"
    toxicological_category: Mapped[str] = mapped_column(String(50), nullable=False)  # ej. "Banda Verde / Precaución"


# ============================================================================
# 4. ÓRDENES DE SERVICIO
# ============================================================================
class ServiceOrder(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "service_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    folio: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    
    branch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False, index=True)
    technician_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    service_start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    service_end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Plagas a controlar (NOM-256)
    pest_crawling_insects: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pest_rodents: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pest_flying_insects: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pest_others: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Procedimientos técnicos aplicados
    proc_aspersion: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    proc_baits: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    proc_traps: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    proc_gels: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    proc_ulv_fogging: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    proc_thermofogging: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    results_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    observations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    client_signature_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Base64 o S3 URL

    # Relaciones
    branch: Mapped["Branch"] = relationship("Branch", back_populates="service_orders")
    technician: Mapped["User"] = relationship("User", back_populates="assigned_orders")
    certificate: Mapped[Optional["Certificate"]] = relationship(
        "Certificate", back_populates="service_order", uselist=False, cascade="all, delete-orphan"
    )


# ============================================================================
# 5. CERTIFICADOS DE SERVICIO Y PIVOTE DE QUÍMICOS
# ============================================================================
class Certificate(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "certificates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_orders.id"), unique=True, nullable=False, index=True
    )
    certificate_folio: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    validity_start_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    validity_end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    # Obligaciones Sanitarias NOM-256
    sanitary_license_number: Mapped[str] = mapped_column(String(100), nullable=False)
    sanitary_responsible_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sanitary_responsible_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True) # Cédula Profesional

    # Firma Electrónica Avanzada (FIEL / e.firma del SAT)
    is_signed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    signed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    digital_signature_seal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Sello Digital Base64
    certificate_serial_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True) # No. Serie Certificado SAT
    original_chain: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # Cadena Original
    signed_by_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    signed_by_rfc: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    verification_uuid: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Relaciones
    service_order: Mapped["ServiceOrder"] = relationship("ServiceOrder", back_populates="certificate")
    applied_chemicals: Mapped[List["CertificateChemical"]] = relationship(
        "CertificateChemical", back_populates="certificate", cascade="all, delete-orphan"
    )


class CertificateChemical(Base, TimestampMixin):
    """Pivote de químicos dosificados por certificado."""
    __tablename__ = "certificate_chemicals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    certificate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("certificates.id"), nullable=False, index=True
    )
    chemical_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chemicals.id"), nullable=False, index=True
    )
    
    dose_applied: Mapped[str] = mapped_column(String(100), nullable=False)  # ej. "10 ml / Litro"
    area_type: Mapped[AreaType] = mapped_column(Enum(AreaType), nullable=False)
    treated_zones_description: Mapped[str] = mapped_column(String(255), nullable=False) # ej. "Cocina, Almacén, Sótanos"
    application_method: Mapped[str] = mapped_column(String(100), nullable=False) # ej. "Aspersión Manual"

    # Relaciones
    certificate: Mapped["Certificate"] = relationship("Certificate", back_populates="applied_chemicals")
    chemical: Mapped["Chemical"] = relationship("Chemical")


# ============================================================================
# 6. CONFIGURACIÓN DE EMPRESA Y FIEL / E.FIRMA SAT
# ============================================================================
class CompanySettings(Base, TimestampMixin):
    __tablename__ = "company_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, default="FUMIFLOSA - CONTROL INTEGRAL DE PLAGAS")
    company_rfc: Mapped[str] = mapped_column(String(13), nullable=False, default="FUM200101XYZ")
    sanitary_license_number: Mapped[str] = mapped_column(String(100), nullable=False, default="2023-15A-099")
    sanitary_responsible_name: Mapped[str] = mapped_column(String(255), nullable=False, default="Biól. Roberto Sánchez Martínez")
    sanitary_responsible_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default="CED-8849201")
    
    # Almacenamiento Seguro de FIEL / e.firma
    fiel_certificate_der: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    fiel_private_key_der: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    fiel_serial_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fiel_valid_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    fiel_valid_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    fiel_rfc: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    fiel_holder_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_fiel_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
