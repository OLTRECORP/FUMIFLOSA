import uuid
from datetime import datetime, date, timezone
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import (
    String, Boolean, Text, Integer, Date, DateTime, 
    ForeignKey, Enum
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
# 0. CONFIGURACIÓN DE LA EMPRESA BASE Y DATOS FISCALES
# ============================================================================
class CompanyConfig(Base, TimestampMixin):
    """Configuración y datos fiscales de la empresa de fumigación prestadora de servicios."""
    __tablename__ = "company_config"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, default="FUMIFLOSA S.A. DE C.V.") # Razón Social
    trade_name: Mapped[str] = mapped_column(String(255), nullable=False, default="FUMIFLOSA - Control de Plagas Urbanas") # Nombre Comercial
    rfc: Mapped[str] = mapped_column(String(13), nullable=False, default="FUM200101XYZ")
    tax_regime: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default="601 - General de Ley Personas Morales")
    fiscal_address: Mapped[str] = mapped_column(String(500), nullable=False, default="Av. Insurgentes Sur 1200, Benito Juárez, CDMX, C.P. 03100")
    phone: Mapped[str] = mapped_column(String(50), nullable=False, default="55-1234-5678")
    email: Mapped[str] = mapped_column(String(255), nullable=False, default="contacto@fumiflosa.mx")
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default="https://fumiflosa.mx")
    
    # Datos Sanitarios y Normativos NOM-256
    sanitary_license_number: Mapped[str] = mapped_column(String(100), nullable=False, default="2023-15A-099")
    sanitary_responsible_name: Mapped[str] = mapped_column(String(255), nullable=False, default="Biól. Roberto Sánchez Martínez")
    sanitary_responsible_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default="CED-8849201")
    stps_registration_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default="FUM-STPS-DC3-2023")
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    sintox_emergency_phones: Mapped[str] = mapped_column(
        String(255), nullable=False, default="01-800-0092800 / 800-009-2800 / CDMX 55-5598-6659"
    )
    default_reentry_hours: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    default_validity_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    terms_and_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# ============================================================================
# 1. USUARIOS Y ROLES (INCLUYE SUPER USUARIO MASTER)
# ============================================================================
class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True, index=True) # ej. FOSM630329EA5
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, values_callable=lambda x: [e.value for e in x], name="userrole"),
        nullable=False,
        default=UserRole.TECNICO_CAMPO
    )
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
# 2. CLIENTES Y SUCURSALES (Jerarquía Institucional y Portal Permanente)
# ============================================================================
def generate_portal_slug():
    return uuid.uuid4().hex[:10]


class Client(Base, TimestampMixin, SoftDeleteMixin):
    """Cliente Corporativo / Matriz (ej. IMSS Órgano de Operación Administrativa)."""
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # Razón Social
    rfc: Mapped[str] = mapped_column(String(13), unique=True, nullable=False, index=True)
    master_contract_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tax_regime: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Portal Permanente Público/Privado para Clientes (URL estática)
    portal_slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False, default=generate_portal_slug)
    portal_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # Contraseña opcional
    portal_is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
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
        Enum(BranchClassification, values_callable=lambda x: [e.value for e in x], name="branchclassification"),
        default=BranchClassification.COMERCIAL,
        nullable=False
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
    technical_sheet_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # URL oficial Ficha Técnica
    safety_sheet_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # URL oficial Hoja de Seguridad HDS


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
    
    # Estado Operativo y Agendamiento de Servicios
    status: Mapped[str] = mapped_column(String(50), default="completed", nullable=False) # completed, scheduled, cancelled
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

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

    # Cancelación de Certificados
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

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
    area_type: Mapped[AreaType] = mapped_column(
        Enum(AreaType, values_callable=lambda x: [e.value for e in x], name="areatype"),
        nullable=False
    )
    treated_zones_description: Mapped[str] = mapped_column(String(255), nullable=False) # ej. "Cocina, Almacén, Sótanos"
    application_method: Mapped[str] = mapped_column(String(100), nullable=False) # ej. "Aspersión Manual"

    # Relaciones
    certificate: Mapped["Certificate"] = relationship("Certificate", back_populates="applied_chemicals")
    chemical: Mapped["Chemical"] = relationship("Chemical")


# ============================================================================
# 6. CATÁLOGO DINÁMICO EN LÍNEA RSCO / CICOPLAFEST
# ============================================================================
class RSCOItem(Base, TimestampMixin, SoftDeleteMixin):
    """Catálogo Oficial RSCO / CICOPLAFEST actualizable en línea."""
    __tablename__ = "rsco_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    commercial_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    active_ingredient: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cicoplafest_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    formulation: Mapped[str] = mapped_column(String(100), nullable=False, default="Suspensión Concentrada")
    manufacturer: Mapped[str] = mapped_column(String(255), nullable=False, default="N/A")
    authorized_dose: Mapped[str] = mapped_column(String(150), nullable=False, default="10 a 20 ml / L de agua")
    target_pests: Mapped[str] = mapped_column(String(500), nullable=False, default="Cucarachas, Chinches, Hormigas, Moscas")
    toxicological_category: Mapped[str] = mapped_column(String(100), nullable=False, default="Banda Verde / Precaución")
    safety_interval_hours: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    technical_sheet_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    safety_sheet_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


# ============================================================================
# 7. BITÁCORAS DEL MANUAL INTEGRAL DE CONTROL DE PLAGAS (NOM-256 / STPS)
# ============================================================================
class EPPLog(Base, TimestampMixin, SoftDeleteMixin):
    """Bitácora de Entrega y Mantenimiento de Equipo de Protección Personal (EPP)."""
    __tablename__ = "epp_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    technician_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    equipment_category: Mapped[str] = mapped_column(String(100), nullable=False) # MASCARILLA, GOGLES, GUANTES, VESTIMENTA, etc.
    equipment_item: Mapped[str] = mapped_column(String(255), nullable=False) # Filtros, Cartuchos, Cintas de ajuste, Micas, Overol, Botas, etc.
    condition_type: Mapped[str] = mapped_column(String(50), nullable=False, default="NUEVO") # NUEVO, USADO
    delivery_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    change_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    change_interval: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # 1 SEM, 2 SEM, 3 SEM, MENSUAL
    change_time: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # ej. "08:30 hrs"
    responsible_signature: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class EPPAnnualMatrix(Base, TimestampMixin, SoftDeleteMixin):
    """Bitácora Anual de EPP por Técnico conforme a matriz de dotación mensual."""
    __tablename__ = "epp_annual_matrix"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    technician_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, default=2026, index=True)
    epp_item: Mapped[str] = mapped_column(String(150), nullable=False) # ej. "PLAYERA POLO", "MASCARILLA COMPLETA"
    frequency: Mapped[str] = mapped_column(String(100), nullable=False) # ej. "ANUAL", "MENSUAL (8 PZAS.)", "SEMESTRAL"
    
    # 12 Meses: fecha de entrega o check, y firma
    jan_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    jan_signed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    feb_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    feb_signed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mar_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    mar_signed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    apr_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    apr_signed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    may_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    may_signed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    jun_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    jun_signed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    jul_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    jul_signed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    aug_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    aug_signed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sep_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sep_signed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    oct_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    oct_signed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    nov_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    nov_signed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dec_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    dec_signed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class EquipmentCalibrationLog(Base, TimestampMixin, SoftDeleteMixin):
    """Bitácora de Mantenimiento y Calibración de Equipos de Aplicación (NOM-256)."""
    __tablename__ = "equipment_calibration_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    equipment_name: Mapped[str] = mapped_column(String(255), nullable=False)
    serial_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    nozzle_type: Mapped[str] = mapped_column(String(100), nullable=False, default="Abanico Plano 8002")
    working_pressure_psi: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="40 psi")
    flow_rate_lpm: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="0.75 L/min")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="OPERATIVO") # OPERATIVO, MANTENIMIENTO, FUERA DE SERVICIO
    calibration_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    next_calibration_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    technician_name: Mapped[str] = mapped_column(String(255), nullable=False)
    observations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class StationMonitoringLog(Base, TimestampMixin, SoftDeleteMixin):
    """Bitácora de Inspección y Monitoreo de Estaciones, Cebaderos y Trampas (MIP)."""
    __tablename__ = "station_monitoring_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    branch_name: Mapped[str] = mapped_column(String(255), nullable=False)
    station_number: Mapped[str] = mapped_column(String(50), nullable=False) # ej. "CEB-01", "UV-02"
    station_type: Mapped[str] = mapped_column(String(100), nullable=False, default="Cebadero de Roedor")
    zone: Mapped[str] = mapped_column(String(150), nullable=False, default="Exterior - Perímetro")
    bait_consumption_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0) # 0, 25, 50, 75, 100
    pest_activity_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pest_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pest_type: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    corrective_action: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    monitoring_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    technician_name: Mapped[str] = mapped_column(String(255), nullable=False)


class HazardousWasteLog(Base, TimestampMixin, SoftDeleteMixin):
    """Bitácora de Residuos Peligrosos y Triple Lavado de Envases (NOM-256 / SEMARNAT)."""
    __tablename__ = "hazardous_waste_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chemical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    active_ingredient: Mapped[str] = mapped_column(String(255), nullable=False)
    containers_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    container_capacity: Mapped[str] = mapped_column(String(100), nullable=False, default="1 Litro")
    triple_wash_performed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    containers_perforated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    wash_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    temporary_storage_location: Mapped[str] = mapped_column(String(255), nullable=False, default="Área de Residuos FUMIFLOSA")
    disposal_manifest_number: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    responsible_name: Mapped[str] = mapped_column(String(255), nullable=False)

