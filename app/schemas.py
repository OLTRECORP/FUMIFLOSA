import uuid
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import UserRole, BranchClassification, AreaType


# ----------------------------------------------------------------------------
# Auth & Super Usuario Login
# ----------------------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str = Field(..., description="Usuario o Email (ej. FOSM630329EA5 o admin@fumiflosa.mx)")
    password: str = Field(..., description="Contraseña de acceso")


class AuthUserInfo(BaseModel):
    id: uuid.UUID
    username: Optional[str] = None
    email: str
    full_name: str
    role: UserRole


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserInfo


# ----------------------------------------------------------------------------
# Company Config (Configuración de la Empresa Base y Datos Fiscales)
# ----------------------------------------------------------------------------
class CompanyConfigBase(BaseModel):
    company_name: str = Field(default="FUMIFLOSA S.A. DE C.V.", max_length=255)
    trade_name: str = Field(default="FUMIFLOSA - Control de Plagas Urbanas", max_length=255)
    rfc: str = Field(default="FUM200101XYZ", max_length=13)
    tax_regime: Optional[str] = Field(default="601 - General de Ley Personas Morales", max_length=100)
    fiscal_address: str = Field(default="Av. Insurgentes Sur 1200, Benito Juárez, CDMX, C.P. 03100", max_length=500)
    phone: str = Field(default="55-1234-5678", max_length=50)
    email: str = Field(default="contacto@fumiflosa.mx", max_length=255)
    website: Optional[str] = Field(default="https://fumiflosa.mx", max_length=255)
    sanitary_license_number: str = Field(default="2023-15A-099", max_length=100)
    sanitary_responsible_name: str = Field(default="Biól. Roberto Sánchez Martínez", max_length=255)
    sanitary_responsible_id: Optional[str] = Field(default="CED-8849201", max_length=100)
    stps_registration_number: Optional[str] = Field(default="FUM-STPS-DC3-2023", max_length=100)
    logo_url: Optional[str] = Field(default=None, max_length=500)
    sintox_emergency_phones: str = Field(default="01-800-0092800 / 800-009-2800 / CDMX 55-5598-6659", max_length=255)
    default_reentry_hours: int = Field(default=2, ge=0)
    default_validity_days: int = Field(default=30, ge=1)
    terms_and_notes: Optional[str] = None


class CompanyConfigUpdate(BaseModel):
    company_name: Optional[str] = None
    trade_name: Optional[str] = None
    rfc: Optional[str] = None
    tax_regime: Optional[str] = None
    fiscal_address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    sanitary_license_number: Optional[str] = None
    sanitary_responsible_name: Optional[str] = None
    sanitary_responsible_id: Optional[str] = None
    stps_registration_number: Optional[str] = None
    logo_url: Optional[str] = None
    sintox_emergency_phones: Optional[str] = None
    default_reentry_hours: Optional[int] = None
    default_validity_days: Optional[int] = None
    terms_and_notes: Optional[str] = None


class CompanyConfigResponse(CompanyConfigBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------------------------------------------
# Users
# ----------------------------------------------------------------------------
class UserBase(BaseModel):
    username: Optional[str] = None
    email: EmailStr
    full_name: str = Field(..., max_length=255)
    role: UserRole = UserRole.TECNICO_CAMPO
    is_active: bool = True
    stps_dc3_file_url: Optional[str] = None
    stps_registration_number: Optional[str] = None
    client_id: Optional[uuid.UUID] = None
    branch_id: Optional[uuid.UUID] = None


class UserCreate(UserBase):
    password: Optional[str] = Field("Fumiflosa2026*", min_length=6)


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    stps_dc3_file_url: Optional[str] = None
    stps_registration_number: Optional[str] = None
    client_id: Optional[uuid.UUID] = None
    branch_id: Optional[uuid.UUID] = None


class UserResponse(UserBase):
    id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------------------------------------------
# Clients (Matriz) & Portal Permanente
# ----------------------------------------------------------------------------
class ClientBase(BaseModel):
    legal_name: str = Field(..., max_length=255)
    rfc: str = Field(..., max_length=13)
    master_contract_number: Optional[str] = None
    tax_regime: Optional[str] = None


class ClientCreate(ClientBase):
    portal_slug: Optional[str] = None
    portal_password: Optional[str] = None


class ClientUpdate(BaseModel):
    legal_name: Optional[str] = None
    rfc: Optional[str] = None
    master_contract_number: Optional[str] = None
    tax_regime: Optional[str] = None
    portal_slug: Optional[str] = None
    portal_password: Optional[str] = None
    portal_is_enabled: Optional[bool] = None


class ClientPortalConfigUpdate(BaseModel):
    portal_slug: Optional[str] = Field(None, description="Slug estático único para URL")
    portal_password: Optional[str] = Field(None, description="Contraseña opcional (vacío para acceso libre)")
    portal_is_enabled: bool = True


class ClientResponse(ClientBase):
    id: uuid.UUID
    portal_slug: str
    portal_has_password: bool = False
    portal_is_enabled: bool = True
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------------------------------------------
# Branches (Sucursal)
# ----------------------------------------------------------------------------
class BranchBase(BaseModel):
    client_id: uuid.UUID
    name: str = Field(..., max_length=255)
    unit_code: Optional[str] = None
    address: str = Field(..., max_length=500)
    phone: str = Field(..., max_length=50)
    classification: BranchClassification = BranchClassification.COMERCIAL
    responsible_contact_name: str = Field(..., max_length=255)
    responsible_contact_email: Optional[str] = None


class BranchCreate(BranchBase):
    pass


class BranchUpdate(BaseModel):
    client_id: Optional[uuid.UUID] = None
    name: Optional[str] = None
    unit_code: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    classification: Optional[BranchClassification] = None
    responsible_contact_name: Optional[str] = None
    responsible_contact_email: Optional[str] = None


class AssociateBranchesRequest(BaseModel):
    branch_ids: List[uuid.UUID]


class BranchResponse(BranchBase):
    id: uuid.UUID
    created_at: datetime
    client: Optional[ClientResponse] = None
    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------------------------------------------
# Chemicals
# ----------------------------------------------------------------------------
class ChemicalBase(BaseModel):
    commercial_name: str = Field(..., max_length=255)
    active_ingredient: str = Field(..., max_length=255)
    cicoplafest_number: str = Field(..., max_length=100)
    authorized_dose_per_liter: str = Field(..., max_length=100)
    safety_interval_hours: int = Field(default=2, ge=0)
    compatible_methods: str = Field(..., max_length=255)
    toxicological_category: str = Field(..., max_length=50)
    technical_sheet_url: Optional[str] = None
    safety_sheet_url: Optional[str] = None


class ChemicalCreate(ChemicalBase):
    pass


class ChemicalUpdate(BaseModel):
    commercial_name: Optional[str] = None
    active_ingredient: Optional[str] = None
    cicoplafest_number: Optional[str] = None
    authorized_dose_per_liter: Optional[str] = None
    safety_interval_hours: Optional[int] = None
    compatible_methods: Optional[str] = None
    toxicological_category: Optional[str] = None
    technical_sheet_url: Optional[str] = None
    safety_sheet_url: Optional[str] = None


class ChemicalResponse(ChemicalBase):
    id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------------------------------------------
# Certificate Chemicals (Pivot)
# ----------------------------------------------------------------------------
class CertificateChemicalCreate(BaseModel):
    chemical_id: uuid.UUID
    dose_applied: str
    area_type: AreaType
    treated_zones_description: str
    application_method: str


class CertificateChemicalResponse(CertificateChemicalCreate):
    id: uuid.UUID
    chemical: ChemicalResponse
    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------------------------------------------
# Certificates
# ----------------------------------------------------------------------------
class CertificateCancelRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500, description="Motivo justificado de la cancelación")


class CertificateResponse(BaseModel):
    id: uuid.UUID
    certificate_folio: str
    issue_date: date
    validity_start_date: date
    validity_end_date: date
    sanitary_license_number: str
    sanitary_responsible_name: str
    sanitary_responsible_id: Optional[str] = None
    is_cancelled: bool = False
    cancellation_reason: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    applied_chemicals: List[CertificateChemicalResponse] = []
    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------------------------------------------
# Service Orders & Scheduling
# ----------------------------------------------------------------------------
class ScheduleServiceRequest(BaseModel):
    branch_id: uuid.UUID
    technician_id: Optional[uuid.UUID] = None
    scheduled_for: datetime
    estimated_duration_minutes: Optional[int] = 60
    linked_order_id: Optional[uuid.UUID] = None
    target_pests: Optional[str] = None
    notes: Optional[str] = None


class RSCOSearchResult(BaseModel):
    commercial_name: str
    active_ingredient: str
    cicoplafest_number: str
    authorized_dose_per_liter: str
    safety_interval_hours: int = 2
    compatible_methods: str
    toxicological_category: str
    in_local_catalog: bool = False
    local_id: Optional[uuid.UUID] = None
    technical_sheet_url: Optional[str] = None
    safety_sheet_url: Optional[str] = None


class ServiceOrderCreate(BaseModel):
    branch_id: uuid.UUID
    technician_id: uuid.UUID
    folio_prefix: Optional[str] = Field("IMSS", description="Prefijo institucional")
    service_start_date: datetime
    service_end_date: datetime
    
    # Plagas
    pest_crawling_insects: bool = False
    pest_rodents: bool = False
    pest_flying_insects: bool = False
    pest_others: Optional[str] = None
    
    # Procedimientos
    proc_aspersion: bool = False
    proc_baits: bool = False
    proc_traps: bool = False
    proc_gels: bool = False
    proc_ulv_fogging: bool = False
    proc_thermofogging: bool = False
    
    results_summary: Optional[str] = None
    observations: Optional[str] = None
    client_signature_data: Optional[str] = None
    
    # Datos de Certificación (NOM-256)
    sanitary_license_number: Optional[str] = None
    sanitary_responsible_name: Optional[str] = None
    sanitary_responsible_id: Optional[str] = None
    chemicals_applied: List[CertificateChemicalCreate]


class ServiceOrderUpdate(BaseModel):
    folio: Optional[str] = None
    status: Optional[str] = None
    scheduled_for: Optional[datetime] = None
    service_start_date: Optional[datetime] = None
    service_end_date: Optional[datetime] = None
    branch_id: Optional[uuid.UUID] = None
    technician_id: Optional[uuid.UUID] = None
    results_summary: Optional[str] = None
    observations: Optional[str] = None
    
    # Certificado NOM-256
    certificate_folio: Optional[str] = None
    issue_date: Optional[date] = None
    validity_start_date: Optional[date] = None
    validity_end_date: Optional[date] = None
    sanitary_license_number: Optional[str] = None
    sanitary_responsible_name: Optional[str] = None
    sanitary_responsible_id: Optional[str] = None
    chemicals_applied: Optional[List[CertificateChemicalCreate]] = None


class ServiceOrderResponse(BaseModel):
    id: uuid.UUID
    folio: str
    status: str = "completed"
    scheduled_for: Optional[datetime] = None
    branch_id: uuid.UUID
    technician_id: uuid.UUID
    service_start_date: datetime
    service_end_date: datetime
    pest_crawling_insects: bool
    pest_rodents: bool
    pest_flying_insects: bool
    pest_others: Optional[str]
    proc_aspersion: bool
    proc_baits: bool
    proc_traps: bool
    proc_gels: bool
    proc_ulv_fogging: bool
    proc_thermofogging: bool
    results_summary: Optional[str]
    observations: Optional[str]
    branch: Optional[BranchResponse] = None
    technician: Optional[UserResponse] = None
    certificate: Optional[CertificateResponse] = None
    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------------------------------------------
# Expiraciones Dashboard
# ----------------------------------------------------------------------------
class ExpirationDetail(BaseModel):
    certificate_id: uuid.UUID
    certificate_folio: str
    service_order_id: uuid.UUID
    branch_id: uuid.UUID
    branch_name: str
    branch_unit_code: Optional[str] = None
    issue_date: Optional[date] = None
    validity_end_date: date
    days_until_expiration: int
    is_valid: bool = True
    status_label: str = "Vigente"


class ClientExpirationsGroup(BaseModel):
    client_id: uuid.UUID
    legal_name: str
    rfc: str
    portal_slug: str
    expiring_7_days: List[ExpirationDetail] = []
    expiring_15_days: List[ExpirationDetail] = []
    expiring_30_days: List[ExpirationDetail] = []
    expired: List[ExpirationDetail] = []


class DashboardExpirationsResponse(BaseModel):
    report_generated_at: datetime
    clients: List[ClientExpirationsGroup]


class DashboardSummaryStats(BaseModel):
    total_clients: int
    total_branches: int
    total_technicians: int
    total_orders: int
    total_chemicals: int
    expiring_7_days: int
    expiring_30_days: int


# ----------------------------------------------------------------------------
# Métricas y Analytics Avanzados de Fumigación
# ----------------------------------------------------------------------------
class AdvancedAnalyticsResponse(BaseModel):
    total_services: int
    total_clients: int
    total_branches: int
    compliance_rate: float
    
    # Tendencia mensual
    monthly_trend: List[Dict[str, Any]]
    
    # Plagas atendidas
    pest_breakdown: Dict[str, int]
    
    # Métodos de aplicación
    procedure_breakdown: Dict[str, int]
    
    # Químicos más utilizados
    top_chemicals: List[Dict[str, Any]]
    
    # Distribución por clasificación de sucursal
    classification_breakdown: Dict[str, int]
    
    # Estado de vigencias
    validity_health: Dict[str, int]
    
    # Top clientes con mayor número de servicios
    top_clients: List[Dict[str, Any]]


# ----------------------------------------------------------------------------
# Portal Permanente de Cliente (Público/Privado)
# ----------------------------------------------------------------------------
class ClientPortalAuthRequest(BaseModel):
    password: Optional[str] = None


class ClientPortalDataResponse(BaseModel):
    client_id: uuid.UUID
    legal_name: str
    rfc: str
    master_contract_number: Optional[str]
    portal_slug: str
    portal_has_password: bool
    total_branches: int
    total_services: int
    branches: List[BranchResponse]
    services: List[ServiceOrderResponse]
    company_info: CompanyConfigResponse


# ----------------------------------------------------------------------------
# Respaldo y Restauración del Sistema (Backup & Restore)
# ----------------------------------------------------------------------------
class CloudRestoreRequest(BaseModel):
    backup_url: str = Field(..., description="URL pública o accesible del archivo de respaldo JSON o ZIP")
    mode: str = Field(default="merge", description="Modo de restauración: 'merge' (ignora duplicados existentes) o 'overwrite'")


class RestoreSummaryResponse(BaseModel):
    status: str
    mode: str
    restored_at: datetime
    company_config_restored: bool
    users_restored: int
    chemicals_restored: int
    clients_restored: int
    branches_restored: int
    orders_restored: int
    certificates_restored: int
    certificate_chemicals_restored: int
    message: str


# ----------------------------------------------------------------------------
# Catálogo Oficial RSCO / CICOPLAFEST en Línea
# ----------------------------------------------------------------------------
class RSCOItemBase(BaseModel):
    commercial_name: str = Field(..., max_length=255)
    active_ingredient: str = Field(..., max_length=255)
    cicoplafest_number: str = Field(..., max_length=100)
    formulation: str = Field(default="Suspensión Concentrada", max_length=100)
    manufacturer: str = Field(default="N/A", max_length=255)
    authorized_dose: str = Field(default="10 a 20 ml / L de agua", max_length=150)
    target_pests: str = Field(default="Cucarachas, Chinches, Hormigas, Moscas", max_length=500)
    toxicological_category: str = Field(default="Banda Verde / Precaución", max_length=100)
    safety_interval_hours: int = Field(default=2, ge=0)
    is_active: bool = True
    technical_sheet_url: Optional[str] = None
    safety_sheet_url: Optional[str] = None


class RSCOItemCreate(RSCOItemBase):
    pass


class RSCOItemUpdate(BaseModel):
    commercial_name: Optional[str] = None
    active_ingredient: Optional[str] = None
    cicoplafest_number: Optional[str] = None
    formulation: Optional[str] = None
    manufacturer: Optional[str] = None
    authorized_dose: Optional[str] = None
    target_pests: Optional[str] = None
    toxicological_category: Optional[str] = None
    safety_interval_hours: Optional[int] = None
    is_active: Optional[bool] = None
    technical_sheet_url: Optional[str] = None
    safety_sheet_url: Optional[str] = None


class RSCOItemResponse(RSCOItemBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------------------------------------------
# Bitácoras NOM-256 / STPS / Manejo Integral de Plagas (MIP)
# ----------------------------------------------------------------------------
class EPPLogBase(BaseModel):
    technician_name: str = Field(..., max_length=255)
    equipment_category: str = Field(..., max_length=100) # MASCARILLA, GOGLES, GUANTES, VESTIMENTA, etc.
    equipment_item: str = Field(..., max_length=255) # Filtros, Cartuchos, etc.
    condition_type: str = Field(default="NUEVO", max_length=50) # NUEVO, USADO
    delivery_date: date = Field(default_factory=date.today)
    change_date: Optional[date] = None
    change_interval: Optional[str] = Field(None, max_length=50) # 1 SEM, 2 SEM, 3 SEM, MENSUAL
    change_time: Optional[str] = Field(None, max_length=50)
    responsible_signature: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None


class EPPLogCreate(EPPLogBase):
    pass


class EPPLogResponse(EPPLogBase):
    id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EPPAnnualMatrixRow(BaseModel):
    id: Optional[uuid.UUID] = None
    technician_name: str
    year: int = 2026
    epp_item: str
    frequency: str
    jan_date: Optional[str] = None
    jan_signed: bool = False
    feb_date: Optional[str] = None
    feb_signed: bool = False
    mar_date: Optional[str] = None
    mar_signed: bool = False
    apr_date: Optional[str] = None
    apr_signed: bool = False
    may_date: Optional[str] = None
    may_signed: bool = False
    jun_date: Optional[str] = None
    jun_signed: bool = False
    jul_date: Optional[str] = None
    jul_signed: bool = False
    aug_date: Optional[str] = None
    aug_signed: bool = False
    sep_date: Optional[str] = None
    sep_signed: bool = False
    oct_date: Optional[str] = None
    oct_signed: bool = False
    nov_date: Optional[str] = None
    nov_signed: bool = False
    dec_date: Optional[str] = None
    dec_signed: bool = False
    model_config = ConfigDict(from_attributes=True)


class EPPAnnualMatrixBatch(BaseModel):
    technician_name: str
    year: int = 2026
    rows: List[EPPAnnualMatrixRow]


class EPPAnnualRowCreate(BaseModel):
    technician_name: str
    year: int = 2026
    epp_item: str
    frequency: str = "MENSUAL"


class EquipmentCalibrationBase(BaseModel):
    equipment_name: str = Field(..., max_length=255)
    serial_number: Optional[str] = Field(None, max_length=100)
    nozzle_type: str = Field(default="Abanico Plano 8002", max_length=100)
    working_pressure_psi: Optional[str] = Field(default="40 psi", max_length=50)
    flow_rate_lpm: Optional[str] = Field(default="0.75 L/min", max_length=50)
    status: str = Field(default="OPERATIVO", max_length=50)
    calibration_date: date = Field(default_factory=date.today)
    next_calibration_date: Optional[date] = None
    technician_name: str = Field(..., max_length=255)
    observations: Optional[str] = None


class EquipmentCalibrationCreate(EquipmentCalibrationBase):
    pass


class EquipmentCalibrationResponse(EquipmentCalibrationBase):
    id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class StationMonitoringBase(BaseModel):
    branch_name: str = Field(..., max_length=255)
    station_number: str = Field(..., max_length=50)
    station_type: str = Field(default="Cebadero de Roedor", max_length=100)
    zone: str = Field(default="Exterior - Perímetro", max_length=150)
    bait_consumption_percent: int = Field(default=0, ge=0, le=100)
    pest_activity_detected: bool = False
    pest_count: int = Field(default=0, ge=0)
    pest_type: Optional[str] = Field(None, max_length=150)
    corrective_action: Optional[str] = Field(None, max_length=255)
    monitoring_date: date = Field(default_factory=date.today)
    technician_name: str = Field(..., max_length=255)


class StationMonitoringCreate(StationMonitoringBase):
    pass


class StationMonitoringResponse(StationMonitoringBase):
    id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class HazardousWasteBase(BaseModel):
    chemical_name: str = Field(..., max_length=255)
    active_ingredient: str = Field(..., max_length=255)
    containers_count: int = Field(default=1, ge=1)
    container_capacity: str = Field(default="1 Litro", max_length=100)
    triple_wash_performed: bool = True
    containers_perforated: bool = True
    wash_date: date = Field(default_factory=date.today)
    temporary_storage_location: str = Field(default="Área de Residuos FUMIFLOSA", max_length=255)
    disposal_manifest_number: Optional[str] = Field(None, max_length=150)
    responsible_name: str = Field(..., max_length=255)


class HazardousWasteCreate(HazardousWasteBase):
    pass


class HazardousWasteResponse(HazardousWasteBase):
    id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------------------------------------------
# 12. Audit Log Schemas (Log de Auditoría, Modificaciones e Inicios de Sesión)
# ----------------------------------------------------------------------------
class AuditLogResponse(BaseModel):
    id: uuid.UUID
    action_type: str
    module: str
    description: str
    user_id: Optional[uuid.UUID] = None
    username: Optional[str] = None
    user_role: Optional[str] = None
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    changes_payload: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogPaginationResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    logs: List[AuditLogResponse]


