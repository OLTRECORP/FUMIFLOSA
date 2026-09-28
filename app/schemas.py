import uuid
from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import UserRole, BranchClassification, AreaType


# ----------------------------------------------------------------------------
# Users
# ----------------------------------------------------------------------------
class UserBase(BaseModel):
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
# Clients (Matriz)
# ----------------------------------------------------------------------------
class ClientBase(BaseModel):
    legal_name: str = Field(..., max_length=255)
    rfc: str = Field(..., max_length=13)
    master_contract_number: Optional[str] = None
    tax_regime: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    legal_name: Optional[str] = None
    rfc: Optional[str] = None
    master_contract_number: Optional[str] = None
    tax_regime: Optional[str] = None


class ClientResponse(ClientBase):
    id: uuid.UUID
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
    name: Optional[str] = None
    unit_code: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    classification: Optional[BranchClassification] = None
    responsible_contact_name: Optional[str] = None
    responsible_contact_email: Optional[str] = None


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
class CertificateResponse(BaseModel):
    id: uuid.UUID
    certificate_folio: str
    issue_date: date
    validity_start_date: date
    validity_end_date: date
    sanitary_license_number: str
    sanitary_responsible_name: str
    sanitary_responsible_id: Optional[str] = None
    applied_chemicals: List[CertificateChemicalResponse] = []
    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------------------------------------------
# Service Orders
# ----------------------------------------------------------------------------
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
    sanitary_license_number: str
    sanitary_responsible_name: str
    sanitary_responsible_id: Optional[str] = None
    chemicals_applied: List[CertificateChemicalCreate]


class ServiceOrderResponse(BaseModel):
    id: uuid.UUID
    folio: str
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
    branch_unit_code: Optional[str]
    validity_end_date: date
    days_until_expiration: int


class ClientExpirationsGroup(BaseModel):
    client_id: uuid.UUID
    legal_name: str
    rfc: str
    expiring_7_days: List[ExpirationDetail] = []
    expiring_15_days: List[ExpirationDetail] = []
    expiring_30_days: List[ExpirationDetail] = []


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
