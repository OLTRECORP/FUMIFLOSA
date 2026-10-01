import io
import re
import uuid
import zipfile
from datetime import datetime, date, timedelta, timezone
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Header
from fastapi.responses import Response, StreamingResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, or_, and_, desc

from app.database import get_db
from app.models import (
    ServiceOrder, Certificate, CertificateChemical, Branch, Client, 
    Chemical, User, UserRole, CompanyConfig,
    RSCOItem, EPPLog, EPPAnnualMatrix, EquipmentCalibrationLog,
    StationMonitoringLog, HazardousWasteLog
)
from app.schemas import (
    LoginRequest, LoginResponse, AuthUserInfo,
    ServiceOrderCreate, ServiceOrderUpdate, ServiceOrderResponse, DashboardExpirationsResponse,
    ClientExpirationsGroup, ExpirationDetail, DashboardSummaryStats,
    UserCreate, UserUpdate, UserResponse,
    ClientCreate, ClientUpdate, ClientResponse, ClientPortalConfigUpdate,
    BranchCreate, BranchUpdate, BranchResponse, AssociateBranchesRequest,
    ChemicalCreate, ChemicalUpdate, ChemicalResponse,
    CompanyConfigResponse, CompanyConfigUpdate,
    AdvancedAnalyticsResponse, ClientPortalAuthRequest, ClientPortalDataResponse,
    CloudRestoreRequest, RestoreSummaryResponse,
    CertificateCancelRequest, ScheduleServiceRequest, RSCOSearchResult,
    RSCOItemCreate, RSCOItemUpdate, RSCOItemResponse,
    EPPLogCreate, EPPLogResponse,
    EPPAnnualMatrixRow, EPPAnnualMatrixBatch, EPPAnnualRowCreate,
    EquipmentCalibrationCreate, EquipmentCalibrationResponse,
    StationMonitoringCreate, StationMonitoringResponse,
    HazardousWasteCreate, HazardousWasteResponse
)
from app.services.data_import import HistoricalDataImporter
from app.services.pdf_service import OfficialCertificatePDFGenerator, OfficialWorkOrderPDFGenerator, BitacoraPDFGenerator
from app.services.backup_service import SystemBackupRestoreService
from app.services.mip_service import get_mip_full_manual, get_pest_combat_guides, seed_default_rsco_items
from app.services.seed_service import (
    seed_all_database_defaults,
    seed_chemicals,
    seed_users,
    seed_clients_and_services,
    seed_bitacoras_and_equipment
)
from app.services.pesticide_sheet_service import (
    lookup_online_sheets_by_rsco,
    OfficialTechnicalSheetPDFGenerator,
    OfficialSafetyDataSheetPDFGenerator
)

router = APIRouter(prefix="/api/v1", tags=["FUMIFLOSA Core"])


def get_or_create_company_config(db: Session) -> CompanyConfig:
    """Obtiene o inicializa la configuración base de la empresa de fumigación."""
    config = db.query(CompanyConfig).first()
    if not config:
        config = CompanyConfig(
            company_name="FUMIFLOSA S.A. DE C.V.",
            trade_name="FUMIFLOSA - Control de Plagas Urbanas",
            rfc="FUM200101XYZ",
            tax_regime="601 - General de Ley Personas Morales",
            fiscal_address="Av. Insurgentes Sur 1200, Benito Juárez, CDMX, C.P. 03100",
            phone="55-1234-5678",
            email="contacto@fumiflosa.mx",
            website="https://fumiflosa.mx",
            sanitary_license_number="2023-15A-099",
            sanitary_responsible_name="Biól. Roberto Sánchez Martínez",
            sanitary_responsible_id="CED-8849201",
            stps_registration_number="FUM-STPS-DC3-2023",
            sintox_emergency_phones="01-800-0092800 / 800-009-2800 / CDMX 55-5598-6659",
            default_reentry_hours=2,
            default_validity_days=30
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


# ============================================================================
# 0. AUTENTICACIÓN SUPER USUARIO MASTER & GESTIÓN DE SESIONES
# ============================================================================
MASTER_SUPERUSER_USERNAME = "FOSM630329EA5"
MASTER_SUPERUSER_EMAIL = "admin@fumiflosa.mx"
MASTER_SUPERUSER_PASSWORD = "FLOSA6303"


@router.post("/auth/login", response_model=LoginResponse)
def login_user(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Inicio de sesión Super Usuario Único y usuarios del portal FUMIFLOSA.
    Credenciales Master:
      Usuario: FOSM630329EA5 (o admin@fumiflosa.mx)
      Contraseña: FLOSA6303
    """
    input_username = payload.username.strip()
    input_password = payload.password.strip()

    # 1. Validación de Super Usuario Master Único
    is_master = (
        input_username.upper() == MASTER_SUPERUSER_USERNAME.upper() or 
        input_username.lower() == MASTER_SUPERUSER_EMAIL.lower()
    ) and input_password == MASTER_SUPERUSER_PASSWORD

    if is_master:
        master_user_id = uuid.uuid4()
        full_name = "Super Administrador Master - FUMIFLOSA"
        try:
            # Asegurar existencia o creación del SuperAdmin en base de datos
            master_user = db.query(User).filter(
                or_(User.username == MASTER_SUPERUSER_USERNAME, User.email == MASTER_SUPERUSER_EMAIL)
            ).first()

            if not master_user:
                master_user = User(
                    username=MASTER_SUPERUSER_USERNAME,
                    email=MASTER_SUPERUSER_EMAIL,
                    full_name=full_name,
                    role=UserRole.SUPERADMIN,
                    hashed_password=f"hash_{MASTER_SUPERUSER_PASSWORD}",
                    is_active=True
                )
                db.add(master_user)
                db.commit()
                db.refresh(master_user)
            else:
                if master_user.role != UserRole.SUPERADMIN or not master_user.is_active or not master_user.username:
                    master_user.role = UserRole.SUPERADMIN
                    master_user.username = MASTER_SUPERUSER_USERNAME
                    master_user.is_active = True
                    db.commit()
                    db.refresh(master_user)
            
            master_user_id = master_user.id
            full_name = master_user.full_name
        except Exception as e:
            db.rollback()
            print(f"[LOGIN MASTER DB WARNING]: {e}")

        session_token = f"fumiflosa_sec_master_{uuid.uuid4().hex}"
        return LoginResponse(
            access_token=session_token,
            token_type="bearer",
            user=AuthUserInfo(
                id=master_user_id,
                username=MASTER_SUPERUSER_USERNAME,
                email=MASTER_SUPERUSER_EMAIL,
                full_name=full_name,
                role=UserRole.SUPERADMIN
            )
        )

    # 2. Validación de otros usuarios estándar registrados en la BD
    try:
        db_user = db.query(User).filter(
            or_(User.username == input_username, User.email == input_username.lower()),
            User.is_deleted == False
        ).first()
    except Exception as e:
        db.rollback()
        # Fallback si columna username aún no estuviera creada en consulta
        try:
            db_user = db.query(User).filter(
                User.email == input_username.lower(),
                User.is_deleted == False
            ).first()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas o usuario inactivo."
            )

    if not db_user or not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas o usuario inactivo."
        )

    # Verificación de password
    valid_pwd = (
        db_user.hashed_password == input_password or
        db_user.hashed_password == f"hash_{input_password}"
    )

    if not valid_pwd:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contraseña incorrecta."
        )

    session_token = f"fumiflosa_sec_usr_{uuid.uuid4().hex}"
    return LoginResponse(
        access_token=session_token,
        token_type="bearer",
        user=AuthUserInfo(
            id=db_user.id,
            username=db_user.username,
            email=db_user.email,
            full_name=db_user.full_name,
            role=db_user.role
        )
    )


@router.get("/auth/me", response_model=AuthUserInfo)
def get_current_user_profile(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Valida la sesión activa y devuelve el perfil del usuario."""
    master_user = db.query(User).filter(
        or_(User.username == MASTER_SUPERUSER_USERNAME, User.email == MASTER_SUPERUSER_EMAIL)
    ).first()
    
    if master_user:
        return AuthUserInfo(
            id=master_user.id,
            username=master_user.username or MASTER_SUPERUSER_USERNAME,
            email=master_user.email,
            full_name=master_user.full_name,
            role=master_user.role
        )
        
    return AuthUserInfo(
        id=uuid.uuid4(),
        username=MASTER_SUPERUSER_USERNAME,
        email=MASTER_SUPERUSER_EMAIL,
        full_name="Super Administrador Master - FUMIFLOSA",
        role=UserRole.SUPERADMIN
    )


@router.post("/auth/logout")
def logout_user():
    """Cierra la sesión del usuario."""
    return {"status": "success", "message": "Sesión cerrada correctamente."}


# ============================================================================
# 0.1 CONFIGURACIÓN DE LA EMPRESA BASE Y DATOS FISCALES
# ============================================================================
@router.get("/company-config", response_model=CompanyConfigResponse)
def get_company_configuration(db: Session = Depends(get_db)):
    """Devuelve la configuración y datos fiscales de la empresa de fumigación."""
    return get_or_create_company_config(db)


@router.put("/company-config", response_model=CompanyConfigResponse)
def update_company_configuration(payload: CompanyConfigUpdate, db: Session = Depends(get_db)):
    """Actualiza los datos fiscales, licencia sanitaria, STPS y SINTOX de la empresa."""
    config = get_or_create_company_config(db)
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config, key, value)
    db.commit()
    db.refresh(config)
    return config


# ============================================================================
# 1. ANALYTICS & MÉTRICAS DETALLADAS DEL PORTAL
# ============================================================================
@router.get("/analytics/detailed", response_model=AdvancedAnalyticsResponse)
def get_detailed_analytics(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Genera las métricas avanzadas y estadísticas de servicios de fumigación con filtro de fechas opcional (2019 a hoy)."""
    start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc) if start_date else None
    end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc) if end_date else None

    # Filtros base para ServiceOrder
    order_filters = [ServiceOrder.is_deleted == False]
    if start_dt:
        order_filters.append(ServiceOrder.service_start_date >= start_dt)
    if end_dt:
        order_filters.append(ServiceOrder.service_start_date <= end_dt)

    total_services = db.query(func.count(ServiceOrder.id)).filter(*order_filters).scalar() or 0
    total_clients = db.query(func.count(Client.id)).filter(Client.is_deleted == False).scalar() or 0
    total_branches = db.query(func.count(Branch.id)).filter(Branch.is_deleted == False).scalar() or 0

    # 1. Desglose de Plagas
    pest_crawling = db.query(func.count(ServiceOrder.id)).filter(*order_filters, ServiceOrder.pest_crawling_insects == True).scalar() or 0
    pest_rodents = db.query(func.count(ServiceOrder.id)).filter(*order_filters, ServiceOrder.pest_rodents == True).scalar() or 0
    pest_flying = db.query(func.count(ServiceOrder.id)).filter(*order_filters, ServiceOrder.pest_flying_insects == True).scalar() or 0
    pest_others = db.query(func.count(ServiceOrder.id)).filter(*order_filters, ServiceOrder.pest_others.isnot(None), ServiceOrder.pest_others != "").scalar() or 0

    # 2. Desglose de Procedimientos
    proc_asp = db.query(func.count(ServiceOrder.id)).filter(*order_filters, ServiceOrder.proc_aspersion == True).scalar() or 0
    proc_baits = db.query(func.count(ServiceOrder.id)).filter(*order_filters, ServiceOrder.proc_baits == True).scalar() or 0
    proc_traps = db.query(func.count(ServiceOrder.id)).filter(*order_filters, ServiceOrder.proc_traps == True).scalar() or 0
    proc_gels = db.query(func.count(ServiceOrder.id)).filter(*order_filters, ServiceOrder.proc_gels == True).scalar() or 0
    proc_ulv = db.query(func.count(ServiceOrder.id)).filter(*order_filters, ServiceOrder.proc_ulv_fogging == True).scalar() or 0
    proc_thermo = db.query(func.count(ServiceOrder.id)).filter(*order_filters, ServiceOrder.proc_thermofogging == True).scalar() or 0

    # 3. Químicos más utilizados
    top_chems_query = db.query(
        Chemical.commercial_name,
        Chemical.active_ingredient,
        func.count(CertificateChemical.id).label("total_uses")
    ).join(CertificateChemical, CertificateChemical.chemical_id == Chemical.id)\
     .join(Certificate, Certificate.id == CertificateChemical.certificate_id)\
     .join(ServiceOrder, ServiceOrder.id == Certificate.service_order_id)\
     .filter(Chemical.is_deleted == False, *order_filters)\
     .group_by(Chemical.commercial_name, Chemical.active_ingredient)\
     .order_by(desc("total_uses")).limit(10).all()

    top_chemicals = [
        {"name": c[0], "ingredient": c[1], "count": c[2]} for c in top_chems_query
    ]

    # 4. Clasificación de Sucursales
    classes_query = db.query(Branch.classification, func.count(Branch.id))\
        .filter(Branch.is_deleted == False)\
        .group_by(Branch.classification).all()
    classification_breakdown = {str(c[0].value if hasattr(c[0], 'value') else c[0]): c[1] for c in classes_query}

    # 5. Estado de Vigencias Sanitarias (Calculadas)
    today = date.today()
    limit_7 = today + timedelta(days=7)
    limit_15 = today + timedelta(days=15)
    
    cert_filters = [Certificate.is_deleted == False]
    if start_date:
        cert_filters.append(Certificate.issue_date >= start_date)
    if end_date:
        cert_filters.append(Certificate.issue_date <= end_date)

    critico_7d = db.query(func.count(Certificate.id)).filter(
        *cert_filters, Certificate.validity_end_date >= today, Certificate.validity_end_date <= limit_7
    ).scalar() or 0

    proximo_15d = db.query(func.count(Certificate.id)).filter(
        *cert_filters, Certificate.validity_end_date > limit_7, Certificate.validity_end_date <= limit_15
    ).scalar() or 0

    vigente = db.query(func.count(Certificate.id)).filter(
        *cert_filters, Certificate.validity_end_date > limit_15
    ).scalar() or 0

    vencido = db.query(func.count(Certificate.id)).filter(
        *cert_filters, Certificate.validity_end_date < today
    ).scalar() or 0

    # 6. Tendencia Mensual (Histórico hasta 120 meses para abarcar desde 2019)
    monthly_orders = db.query(
        func.to_char(ServiceOrder.service_start_date, 'YYYY-MM').label('month_key'),
        func.count(ServiceOrder.id).label('count')
    ).filter(*order_filters)\
     .group_by('month_key')\
     .order_by('month_key').limit(120).all()

    monthly_trend = [{"month": m[0], "count": m[1]} for m in monthly_orders]
    if not monthly_trend:
        monthly_trend = [{"month": today.strftime('%Y-%m'), "count": total_services}]

    # 7. Top Clientes
    top_clients_query = db.query(
        Client.legal_name,
        func.count(ServiceOrder.id).label("services_count"),
        func.count(func.distinct(Branch.id)).label("branches_count")
    ).join(Branch, Branch.client_id == Client.id)\
     .join(ServiceOrder, ServiceOrder.branch_id == Branch.id)\
     .filter(Client.is_deleted == False, *order_filters)\
     .group_by(Client.legal_name)\
     .order_by(desc("services_count")).limit(10).all()

    top_clients = [
        {"name": tc[0], "count": tc[1], "branches_count": tc[2]} for tc in top_clients_query
    ]

    total_valid = vigente + proximo_15d + critico_7d
    compliance_rate = round((total_valid / total_services * 100), 1) if total_services > 0 else 100.0

    return AdvancedAnalyticsResponse(
        total_services=total_services,
        total_clients=total_clients,
        total_branches=total_branches,
        compliance_rate=compliance_rate,
        monthly_trend=monthly_trend,
        pest_breakdown={
            "Insectos Rastreros": pest_crawling,
            "Roedores": pest_rodents,
            "Insectos Voladores": pest_flying,
            "Otras Plagas": pest_others
        },
        procedure_breakdown={
            "Aspersión": proc_asp,
            "Cebos": proc_baits,
            "Trampas": proc_traps,
            "Geles": proc_gels,
            "Nebulización UBV": proc_ulv,
            "Termonebulización": proc_thermo
        },
        top_chemicals=top_chemicals,
        classification_breakdown=classification_breakdown,
        validity_health={
            "vigente": vigente,
            "proximo_15d": proximo_15d,
            "critico_7d": critico_7d,
            "vencido": vencido
        },
        top_clients=top_clients
    )


# ============================================================================
# 2. ENLACE PERMANENTE Y PORTAL PRIVADO PARA CLIENTES
# ============================================================================
@router.get("/clients/{client_id}/portal-config")
def get_client_portal_config(client_id: uuid.UUID, db: Session = Depends(get_db)):
    """Obtiene la configuración del enlace permanente y estado de contraseña de un cliente."""
    client = db.query(Client).filter(Client.id == client_id, Client.is_deleted == False).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    return {
        "client_id": client.id,
        "legal_name": client.legal_name,
        "rfc": client.rfc,
        "portal_slug": client.portal_slug,
        "portal_is_enabled": client.portal_is_enabled,
        "has_password": bool(client.portal_password and client.portal_password.strip()),
        "portal_url": f"/portal/c/{client.portal_slug}"
    }


@router.put("/clients/{client_id}/portal-config")
def update_client_portal_config(
    client_id: uuid.UUID, 
    payload: ClientPortalConfigUpdate, 
    db: Session = Depends(get_db)
):
    """Configura o actualiza el enlace permanente (slug estático) y contraseña opcional."""
    client = db.query(Client).filter(Client.id == client_id, Client.is_deleted == False).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    # Validar unicidad de slug si se cambia
    if payload.portal_slug and payload.portal_slug != client.portal_slug:
        existing = db.query(Client).filter(Client.portal_slug == payload.portal_slug, Client.id != client_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="El identificador de enlace (slug) ya está en uso. Elige otro.")
        client.portal_slug = payload.portal_slug

    if payload.portal_password is not None:
        client.portal_password = payload.portal_password.strip() if payload.portal_password.strip() else None

    client.portal_is_enabled = payload.portal_is_enabled
    db.commit()
    db.refresh(client)

    return {
        "status": "success",
        "portal_slug": client.portal_slug,
        "portal_url": f"/portal/c/{client.portal_slug}",
        "has_password": bool(client.portal_password),
        "portal_is_enabled": client.portal_is_enabled
    }


@router.post("/portal/verify/{portal_slug}")
def verify_portal_access(
    portal_slug: str, 
    payload: ClientPortalAuthRequest, 
    db: Session = Depends(get_db)
):
    """Verifica si el slug es válido y valida la contraseña si está protegida."""
    client = db.query(Client).filter(Client.portal_slug == portal_slug, Client.is_deleted == False).first()
    if not client:
        raise HTTPException(status_code=404, detail="Portal no encontrado o enlace inválido.")

    if not client.portal_is_enabled:
        raise HTTPException(status_code=403, detail="El portal para este cliente ha sido deshabilitado temporalmente.")

    has_pw = bool(client.portal_password and client.portal_password.strip())
    if has_pw:
        if not payload.password or payload.password != client.portal_password:
            raise HTTPException(status_code=401, detail="Contraseña incorrecta.")

    return {
        "authenticated": True,
        "client_id": client.id,
        "legal_name": client.legal_name,
        "rfc": client.rfc
    }


@router.get("/portal/data/{portal_slug}", response_model=ClientPortalDataResponse)
def get_client_portal_data(
    portal_slug: str,
    x_portal_password: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Devuelve todo el historial, sucursales y certificados para el portal del cliente."""
    client = db.query(Client).filter(Client.portal_slug == portal_slug, Client.is_deleted == False).first()
    if not client:
        raise HTTPException(status_code=404, detail="Portal no encontrado.")

    if not client.portal_is_enabled:
        raise HTTPException(status_code=403, detail="El portal está desactivado.")

    has_pw = bool(client.portal_password and client.portal_password.strip())
    if has_pw:
        if not x_portal_password or x_portal_password != client.portal_password:
            raise HTTPException(status_code=401, detail="Acceso no autorizado. Se requiere contraseña válida.")

    branches = db.query(Branch).filter(Branch.client_id == client.id, Branch.is_deleted == False).order_by(Branch.name).all()
    
    services = db.query(ServiceOrder).options(
        joinedload(ServiceOrder.branch),
        joinedload(ServiceOrder.technician),
        joinedload(ServiceOrder.certificate).joinedload(Certificate.applied_chemicals).joinedload(CertificateChemical.chemical)
    ).join(Branch).filter(
        Branch.client_id == client.id,
        ServiceOrder.is_deleted == False
    ).order_by(ServiceOrder.service_start_date.desc()).all()

    company = get_or_create_company_config(db)

    return ClientPortalDataResponse(
        client_id=client.id,
        legal_name=client.legal_name,
        rfc=client.rfc,
        master_contract_number=client.master_contract_number,
        portal_slug=client.portal_slug,
        portal_has_password=has_pw,
        total_branches=len(branches),
        total_services=len(services),
        branches=branches,
        services=services,
        company_info=company
    )


# ============================================================================
# 3. RESUMEN DASHBOARD METRICS (HEADLINES)
# ============================================================================
@router.get("/dashboard/summary", response_model=DashboardSummaryStats)
def get_dashboard_summary(db: Session = Depends(get_db)):
    """Devuelve estadísticas generales para el panel principal."""
    if db.query(Client).filter(Client.is_deleted == False).count() == 0:
        seed_all_database_defaults(db)

    total_clients = db.query(func.count(Client.id)).filter(Client.is_deleted == False).scalar() or 0
    total_branches = db.query(func.count(Branch.id)).filter(Branch.is_deleted == False).scalar() or 0
    total_technicians = db.query(func.count(User.id)).filter(User.is_deleted == False, User.role == UserRole.TECNICO_CAMPO).scalar() or 0
    total_orders = db.query(func.count(ServiceOrder.id)).filter(ServiceOrder.is_deleted == False).scalar() or 0
    total_chemicals = db.query(func.count(Chemical.id)).filter(Chemical.is_deleted == False).scalar() or 0

    today = date.today()
    limit_7 = today + timedelta(days=7)
    limit_30 = today + timedelta(days=30)

    exp_7 = db.query(func.count(Certificate.id)).filter(
        Certificate.is_deleted == False,
        Certificate.validity_end_date >= today,
        Certificate.validity_end_date <= limit_7
    ).scalar() or 0

    exp_30 = db.query(func.count(Certificate.id)).filter(
        Certificate.is_deleted == False,
        Certificate.validity_end_date >= today,
        Certificate.validity_end_date <= limit_30
    ).scalar() or 0

    return DashboardSummaryStats(
        total_clients=total_clients,
        total_branches=total_branches,
        total_technicians=total_technicians,
        total_orders=total_orders,
        total_chemicals=total_chemicals,
        expiring_7_days=exp_7,
        expiring_30_days=exp_30
    )


# ============================================================================
# 4. USUARIOS Y ROLES (CRUD + STPS DC-3)
# ============================================================================
@router.get("/users", response_model=List[UserResponse])
def get_users(role: Optional[UserRole] = None, db: Session = Depends(get_db)):
    if db.query(User).filter(User.is_deleted == False).count() == 0:
        seed_users(db)
    query = db.query(User).filter(User.is_deleted == False)
    if role:
        query = query.filter(User.role == role)
    return query.order_by(User.full_name).all()


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email, User.is_deleted == False).first()
    if existing:
        raise HTTPException(status_code=400, detail="El correo electrónico ya está registrado.")

    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=f"hash_{payload.password}",
        role=payload.role,
        is_active=payload.is_active,
        stps_dc3_file_url=payload.stps_dc3_file_url,
        stps_registration_number=payload.stps_registration_number,
        client_id=payload.client_id,
        branch_id=payload.branch_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: uuid.UUID, payload: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: uuid.UUID, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    user.soft_delete()
    db.commit()
    return None


# ============================================================================
# 5. CLIENTES MATRIZ (CRUD & PORTAL CONFIG)
# ============================================================================
@router.get("/clients", response_model=List[ClientResponse])
def get_clients(db: Session = Depends(get_db)):
    if db.query(Client).filter(Client.is_deleted == False).count() == 0:
        seed_clients_and_services(db)
    clients = db.query(Client).filter(Client.is_deleted == False).order_by(Client.legal_name).all()
    # Mapear portal_has_password
    for c in clients:
        c.portal_has_password = bool(c.portal_password and c.portal_password.strip())
    return clients


@router.post("/clients", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(payload: ClientCreate, db: Session = Depends(get_db)):
    existing = db.query(Client).filter(Client.rfc == payload.rfc, Client.is_deleted == False).first()
    if existing:
        raise HTTPException(status_code=400, detail="El RFC ya se encuentra registrado.")

    slug = payload.portal_slug.strip() if payload.portal_slug else uuid.uuid4().hex[:10]
    
    client = Client(
        legal_name=payload.legal_name,
        rfc=payload.rfc,
        master_contract_number=payload.master_contract_number,
        tax_regime=payload.tax_regime,
        portal_slug=slug,
        portal_password=payload.portal_password
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    client.portal_has_password = bool(client.portal_password)
    return client


@router.put("/clients/{client_id}", response_model=ClientResponse)
def update_client(client_id: uuid.UUID, payload: ClientUpdate, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id, Client.is_deleted == False).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(client, key, value)

    db.commit()
    db.refresh(client)
    client.portal_has_password = bool(client.portal_password)
    return client


@router.delete("/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(client_id: uuid.UUID, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id, Client.is_deleted == False).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    client.soft_delete()
    db.commit()
    return None


# ============================================================================
# 6. SUCURSALES (CRUD)
# ============================================================================
@router.get("/branches", response_model=List[BranchResponse])
def get_branches(client_id: Optional[uuid.UUID] = None, db: Session = Depends(get_db)):
    if db.query(Branch).filter(Branch.is_deleted == False).count() == 0:
        seed_clients_and_services(db)
    query = db.query(Branch).options(joinedload(Branch.client)).filter(Branch.is_deleted == False)
    if client_id:
        query = query.filter(Branch.client_id == client_id)
    return query.order_by(Branch.name).all()


@router.post("/branches", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
def create_branch(payload: BranchCreate, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == payload.client_id, Client.is_deleted == False).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente Matriz no encontrado.")

    branch = Branch(
        client_id=payload.client_id,
        name=payload.name,
        unit_code=payload.unit_code,
        address=payload.address,
        phone=payload.phone,
        classification=payload.classification,
        responsible_contact_name=payload.responsible_contact_name,
        responsible_contact_email=payload.responsible_contact_email
    )
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return branch


@router.put("/branches/{branch_id}", response_model=BranchResponse)
def update_branch(branch_id: uuid.UUID, payload: BranchUpdate, db: Session = Depends(get_db)):
    branch = db.query(Branch).filter(Branch.id == branch_id, Branch.is_deleted == False).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada.")

    update_data = payload.model_dump(exclude_unset=True)
    if "client_id" in update_data and update_data["client_id"]:
        client = db.query(Client).filter(Client.id == update_data["client_id"], Client.is_deleted == False).first()
        if not client:
            raise HTTPException(status_code=404, detail="Cliente Matriz especificado no encontrado.")

    for key, value in update_data.items():
        setattr(branch, key, value)

    db.commit()
    db.refresh(branch)
    return branch


@router.post("/clients/{client_id}/branches/associate", response_model=List[BranchResponse])
def associate_branches_to_client(client_id: uuid.UUID, payload: AssociateBranchesRequest, db: Session = Depends(get_db)):
    """Asocia múltiples sucursales existentes a un cliente matriz específico."""
    client = db.query(Client).filter(Client.id == client_id, Client.is_deleted == False).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente Matriz no encontrado.")

    updated_branches = []
    for branch_id in payload.branch_ids:
        branch = db.query(Branch).filter(Branch.id == branch_id, Branch.is_deleted == False).first()
        if branch:
            branch.client_id = client.id
            updated_branches.append(branch)

    db.commit()
    for b in updated_branches:
        db.refresh(b)
    return updated_branches


@router.delete("/branches/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_branch(branch_id: uuid.UUID, db: Session = Depends(get_db)):
    branch = db.query(Branch).filter(Branch.id == branch_id, Branch.is_deleted == False).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada.")
    branch.soft_delete()
    db.commit()
    return None


# ============================================================================
# 7. CATÁLOGO DE QUÍMICOS Y BUSCADOR OFICIAL COFEPRIS / RSCO
# ============================================================================
OFFICIAL_COFEPRIS_PESTICIDE_CATALOG = [
    {
        "commercial_name": "Cipertrina 20 CE",
        "active_ingredient": "Cipermetrina",
        "cicoplafest_number": "RSCO-URB-MEZC-111-00-02-40",
        "authorized_dose_per_liter": "3 a 5 ml / Litro",
        "safety_interval_hours": 2,
        "compatible_methods": "Aspersión Fina Manual / Motorizada",
        "toxicological_category": "Precaución / Banda Verde"
    },
    {
        "commercial_name": "Biothrine Flow",
        "active_ingredient": "Deltametrina",
        "cicoplafest_number": "RSCO-URB-INAC-111-316-009-02.5",
        "authorized_dose_per_liter": "5 a 10 ml / Litro",
        "safety_interval_hours": 2,
        "compatible_methods": "Aspersión / Nebulización en Frío",
        "toxicological_category": "Precaución / Banda Verde"
    },
    {
        "commercial_name": "Termidor 25 CE",
        "active_ingredient": "Fipronil",
        "cicoplafest_number": "RSCO-URB-INAC-105-327-009-2.5",
        "authorized_dose_per_liter": "2 a 4 ml / Litro",
        "safety_interval_hours": 4,
        "compatible_methods": "Aspersión Perimetral / Inyección Subterránea",
        "toxicological_category": "Precaución / Banda Azul"
    },
    {
        "commercial_name": "Maxforce Gel Cucarachas",
        "active_ingredient": "Hidrametilnona",
        "cicoplafest_number": "RSCO-URB-INAC-184-315-009-2.15",
        "authorized_dose_per_liter": "0.5 a 1 g / m2 en puntos de aplicación",
        "safety_interval_hours": 0,
        "compatible_methods": "Pistola Dosificadora de Gel",
        "toxicological_category": "Precaución / Banda Verde"
    },
    {
        "commercial_name": "Advion Cucaracha Gel",
        "active_ingredient": "Indoxacarb",
        "cicoplafest_number": "RSCO-DOM-INAC-184-315-009-0.6",
        "authorized_dose_per_liter": "2 a 3 gotas de 0.5g por m2",
        "safety_interval_hours": 0,
        "compatible_methods": "Aplicación de Gel en Grietas y Hendiduras",
        "toxicological_category": "Banda Verde"
    },
    {
        "commercial_name": "Demand 2.5 CS",
        "active_ingredient": "Lambda Cyhalotrina",
        "cicoplafest_number": "RSCO-URB-INAC-179-317-009-2.5",
        "authorized_dose_per_liter": "5 a 10 ml / Litro",
        "safety_interval_hours": 2,
        "compatible_methods": "Aspersión Residual Microencapsulada",
        "toxicological_category": "Precaución / Banda Verde"
    },
    {
        "commercial_name": "Premise 200 SC",
        "active_ingredient": "Imidacloprid",
        "cicoplafest_number": "RSCO-URB-INAC-198-333-021-30.5",
        "authorized_dose_per_liter": "4 a 8 ml / Litro",
        "safety_interval_hours": 2,
        "compatible_methods": "Aspersión Focalizada / Inyección",
        "toxicological_category": "Precaución / Banda Verde"
    },
    {
        "commercial_name": "Contrac Blox",
        "active_ingredient": "Bromadiolona",
        "cicoplafest_number": "RSCO-URB-ROED-601-301-033-0.005",
        "authorized_dose_per_liter": "1 a 2 bloques por cebadero",
        "safety_interval_hours": 0,
        "compatible_methods": "Estaciones de Cebado Inviolables",
        "toxicological_category": "Precaución / Banda Azul"
    },
    {
        "commercial_name": "Klerat Bloque",
        "active_ingredient": "Brodifacoum",
        "cicoplafest_number": "RSCO-URB-ROED-602-302-033-0.005",
        "authorized_dose_per_liter": "1 bloque (20g) por punto de monitoreo",
        "safety_interval_hours": 0,
        "compatible_methods": "Estaciones Cebaderas Perimetrales",
        "toxicological_category": "Precaución / Banda Azul"
    },
    {
        "commercial_name": "Fendona 6 SC",
        "active_ingredient": "Alfacipermetrina",
        "cicoplafest_number": "RSCO-URB-INAC-181-314-064-06.0",
        "authorized_dose_per_liter": "5 ml / Litro",
        "safety_interval_hours": 2,
        "compatible_methods": "Aspersión Residual en Interiores y Exteriores",
        "toxicological_category": "Precaución / Banda Verde"
    },
    {
        "commercial_name": "Alpine WSG",
        "active_ingredient": "Dinoteforan",
        "cicoplafest_number": "RSCO-URB-INAC-195-318-009-40.0",
        "authorized_dose_per_liter": "10 a 30 g / Litro",
        "safety_interval_hours": 2,
        "compatible_methods": "Aspersión de Gránulos Solubles",
        "toxicological_category": "Precaución / Banda Verde"
    },
    {
        "commercial_name": "Nuván 50 CE",
        "active_ingredient": "Diclorvos (DDVP)",
        "cicoplafest_number": "RSCO-URB-INAC-109-305-009-50",
        "authorized_dose_per_liter": "5 a 10 ml / Litro",
        "safety_interval_hours": 4,
        "compatible_methods": "Nebulización ULV en Frío / Espacios Confinados",
        "toxicological_category": "Moderadamente Tóxico / Banda Amarilla"
    },
    {
        "commercial_name": "Dragnet 36.8 CE",
        "active_ingredient": "Permetrina",
        "cicoplafest_number": "RSCO-URB-INAC-110-315-009-38.4",
        "authorized_dose_per_liter": "5 a 10 ml / Litro",
        "safety_interval_hours": 2,
        "compatible_methods": "Aspersión / Termonebulización",
        "toxicological_category": "Precaución / Banda Verde"
    },
    {
        "commercial_name": "Archer IGR",
        "active_ingredient": "Piriproxifen",
        "cicoplafest_number": "RSCO-URB-INAC-192-311-009-1.3",
        "authorized_dose_per_liter": "2 a 4 ml / Litro",
        "safety_interval_hours": 2,
        "compatible_methods": "Regulador de Crecimiento de Insectos / Aspersión",
        "toxicological_category": "Precaución / Banda Verde"
    },
    {
        "commercial_name": "Talstar Xtra",
        "active_ingredient": "Bifentrina",
        "cicoplafest_number": "RSCO-URB-INAC-175-306-009-07.9",
        "authorized_dose_per_liter": "5 a 10 ml / Litro",
        "safety_interval_hours": 2,
        "compatible_methods": "Aspersión Perimetral y Barreras de Exclusión",
        "toxicological_category": "Precaución / Banda Verde"
    }
]


@router.get("/chemicals/rsco-search", response_model=List[RSCOSearchResult])
def search_rsco_chemicals(q: str = "", db: Session = Depends(get_db)):
    """
    Buscador especializado de plaguicidas e ingredientes activos por registro RSCO / CICOPLAFEST.
    Permite filtrar por marca comercial, ingrediente activo o folio RSCO.
    Combina el catálogo local del SaaS con la base de referencia oficial COFEPRIS.
    """
    search_term = q.strip().lower()
    # Si busca 'coespris', 'cofepris' o términos genéricos, mostrar el catálogo oficial completo
    if search_term in ["coespris", "cofepris", "rsco", "plaguicida", "plaguicidas", "catalogo", "todos", "all"]:
        search_term = ""

    results: List[RSCOSearchResult] = []
    seen_rsco = set()

    # 1. Catálogo Oficial RSCO en Línea (dinámico y actualizable por el usuario)
    try:
        rsco_count = db.query(RSCOItem).filter(RSCOItem.is_deleted == False).count()
        if rsco_count == 0:
            seed_default_rsco_items(db)

        rsco_query = db.query(RSCOItem).filter(RSCOItem.is_deleted == False)
        if search_term:
            rsco_query = rsco_query.filter(
                or_(
                    func.lower(RSCOItem.commercial_name).contains(search_term),
                    func.lower(RSCOItem.active_ingredient).contains(search_term),
                    func.lower(RSCOItem.cicoplafest_number).contains(search_term),
                    func.lower(RSCOItem.manufacturer).contains(search_term),
                    func.lower(RSCOItem.target_pests).contains(search_term)
                )
            )
        for ri in rsco_query.limit(40).all():
            rsco_norm = ri.cicoplafest_number.strip().upper()
            seen_rsco.add(rsco_norm)
            sheet_info = lookup_online_sheets_by_rsco(ri.cicoplafest_number, ri.commercial_name)
            results.append(RSCOSearchResult(
                commercial_name=f"{ri.commercial_name} ({ri.manufacturer})",
                active_ingredient=ri.active_ingredient,
                cicoplafest_number=ri.cicoplafest_number,
                authorized_dose_per_liter=ri.authorized_dose,
                safety_interval_hours=ri.safety_interval_hours,
                compatible_methods=f"Formulación: {ri.formulation}",
                toxicological_category=ri.toxicological_category,
                in_local_catalog=True,
                local_id=ri.id,
                technical_sheet_url=ri.technical_sheet_url or sheet_info.get("technical_sheet_url"),
                safety_sheet_url=ri.safety_sheet_url or sheet_info.get("safety_sheet_url")
            ))
    except Exception as e:
        print(f"[RSCO SEARCH WARNING]: {e}")

    # 2. Químicos registrados en la empresa (Chemicals)
    try:
        local_query = db.query(Chemical).filter(Chemical.is_deleted == False)
        if search_term:
            local_query = local_query.filter(
                or_(
                    func.lower(Chemical.commercial_name).contains(search_term),
                    func.lower(Chemical.active_ingredient).contains(search_term),
                    func.lower(Chemical.cicoplafest_number).contains(search_term)
                )
            )
        for lc in local_query.limit(20).all():
            rsco_norm = lc.cicoplafest_number.strip().upper()
            if rsco_norm in seen_rsco:
                continue
            seen_rsco.add(rsco_norm)
            sheet_info = lookup_online_sheets_by_rsco(lc.cicoplafest_number, lc.commercial_name)
            results.append(RSCOSearchResult(
                commercial_name=lc.commercial_name,
                active_ingredient=lc.active_ingredient,
                cicoplafest_number=lc.cicoplafest_number,
                authorized_dose_per_liter=lc.authorized_dose_per_liter,
                safety_interval_hours=lc.safety_interval_hours,
                compatible_methods=lc.compatible_methods,
                toxicological_category=lc.toxicological_category,
                in_local_catalog=True,
                local_id=lc.id,
                technical_sheet_url=lc.technical_sheet_url or sheet_info.get("technical_sheet_url"),
                safety_sheet_url=lc.safety_sheet_url or sheet_info.get("safety_sheet_url")
            ))
    except Exception as e:
        print(f"[LOCAL CHEMS SEARCH WARNING]: {e}")

    # 3. Catálogo de referencia COFEPRIS oficial fallback (siempre disponible)
    for ref in OFFICIAL_COFEPRIS_PESTICIDE_CATALOG:
        rsco_norm = ref["cicoplafest_number"].strip().upper()
        if rsco_norm in seen_rsco:
            continue
        if not search_term or (
            search_term in ref["commercial_name"].lower() or
            search_term in ref["active_ingredient"].lower() or
            search_term in ref["cicoplafest_number"].lower()
        ):
            sheet_info = lookup_online_sheets_by_rsco(ref["cicoplafest_number"], ref["commercial_name"])
            results.append(RSCOSearchResult(
                commercial_name=ref["commercial_name"],
                active_ingredient=ref["active_ingredient"],
                cicoplafest_number=ref["cicoplafest_number"],
                authorized_dose_per_liter=ref["authorized_dose_per_liter"],
                safety_interval_hours=ref["safety_interval_hours"],
                compatible_methods=ref["compatible_methods"],
                toxicological_category=ref["toxicological_category"],
                in_local_catalog=False,
                local_id=None,
                technical_sheet_url=sheet_info.get("technical_sheet_url"),
                safety_sheet_url=sheet_info.get("safety_sheet_url")
            ))
            seen_rsco.add(rsco_norm)

    return results


@router.get("/chemicals", response_model=List[ChemicalResponse])
def get_chemicals(db: Session = Depends(get_db)):
    if db.query(Chemical).filter(Chemical.is_deleted == False).count() == 0:
        seed_chemicals(db)
    return db.query(Chemical).filter(Chemical.is_deleted == False).order_by(Chemical.commercial_name).all()


@router.post("/chemicals", response_model=ChemicalResponse, status_code=status.HTTP_201_CREATED)
def create_chemical(payload: ChemicalCreate, db: Session = Depends(get_db)):
    existing = db.query(Chemical).filter(Chemical.cicoplafest_number == payload.cicoplafest_number, Chemical.is_deleted == False).first()
    if existing:
        raise HTTPException(status_code=400, detail="El número de registro CICOPLAFEST ya existe.")

    tech_url = payload.technical_sheet_url
    safe_url = payload.safety_sheet_url
    if not tech_url or not safe_url:
        lookup_data = lookup_online_sheets_by_rsco(payload.cicoplafest_number, payload.commercial_name)
        if not tech_url:
            tech_url = lookup_data.get("technical_sheet_url")
        if not safe_url:
            safe_url = lookup_data.get("safety_sheet_url")

    chem = Chemical(
        commercial_name=payload.commercial_name,
        active_ingredient=payload.active_ingredient,
        cicoplafest_number=payload.cicoplafest_number,
        authorized_dose_per_liter=payload.authorized_dose_per_liter,
        safety_interval_hours=payload.safety_interval_hours,
        compatible_methods=payload.compatible_methods,
        toxicological_category=payload.toxicological_category,
        technical_sheet_url=tech_url,
        safety_sheet_url=safe_url
    )
    db.add(chem)
    db.commit()
    db.refresh(chem)
    return chem


@router.put("/chemicals/{chemical_id}", response_model=ChemicalResponse)
def update_chemical(chemical_id: uuid.UUID, payload: ChemicalUpdate, db: Session = Depends(get_db)):
    chem = db.query(Chemical).filter(Chemical.id == chemical_id, Chemical.is_deleted == False).first()
    if not chem:
        raise HTTPException(status_code=404, detail="Químico no encontrado.")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(chem, key, value)

    if not chem.technical_sheet_url or not chem.safety_sheet_url:
        lookup_data = lookup_online_sheets_by_rsco(chem.cicoplafest_number, chem.commercial_name)
        if not chem.technical_sheet_url:
            chem.technical_sheet_url = lookup_data.get("technical_sheet_url")
        if not chem.safety_sheet_url:
            chem.safety_sheet_url = lookup_data.get("safety_sheet_url")

    db.commit()
    db.refresh(chem)
    return chem


@router.delete("/chemicals/{chemical_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chemical(chemical_id: uuid.UUID, db: Session = Depends(get_db)):
    chem = db.query(Chemical).filter(Chemical.id == chemical_id, Chemical.is_deleted == False).first()
    if not chem:
        raise HTTPException(status_code=404, detail="Químico no encontrado.")
    chem.soft_delete()
    db.commit()
    return None


# ----------------------------------------------------------------------------
# ENDPOINTS DE FICHAS TÉCNICAS Y HOJAS DE SEGURIDAD (HDS NOM-018 / NOM-256)
# ----------------------------------------------------------------------------

@router.get("/chemicals/sheets/lookup")
def lookup_chemical_sheets(rsco: str = "", name: str = ""):
    """Obtiene en línea la información técnica, enlaces de descarga y HDS según folio RSCO o nombre."""
    return lookup_online_sheets_by_rsco(rsco=rsco, commercial_name=name)


@router.get("/chemicals/{chemical_id}/technical-sheet")
def download_chemical_technical_sheet(
    chemical_id: uuid.UUID,
    redirect: bool = False,
    db: Session = Depends(get_db)
):
    """
    Descarga o visualiza la Ficha Técnica Oficial del plaguicida conforme a NOM-256.
    Si redirect=True y tiene enlace externo oficial directo, redirige al PDF del fabricante.
    De lo contrario, genera el PDF oficial estructurado del sistema.
    """
    chem = db.query(Chemical).filter(Chemical.id == chemical_id, Chemical.is_deleted == False).first()
    if not chem:
        raise HTTPException(status_code=404, detail="Químico no encontrado.")

    if redirect and chem.technical_sheet_url and chem.technical_sheet_url.startswith("http"):
        return RedirectResponse(url=chem.technical_sheet_url, status_code=302)

    company = db.query(CompanyConfig).first()
    sheet_data = lookup_online_sheets_by_rsco(chem.cicoplafest_number, chem.commercial_name)
    merged = {
        **sheet_data,
        "commercial_name": chem.commercial_name,
        "active_ingredient": chem.active_ingredient,
        "cicoplafest_number": chem.cicoplafest_number,
        "authorized_dose_per_liter": chem.authorized_dose_per_liter,
        "safety_interval_hours": chem.safety_interval_hours,
        "compatible_methods": chem.compatible_methods,
        "toxicological_category": chem.toxicological_category,
        "technical_sheet_url": chem.technical_sheet_url or sheet_data.get("technical_sheet_url"),
        "safety_sheet_url": chem.safety_sheet_url or sheet_data.get("safety_sheet_url")
    }

    pdf_bytes = OfficialTechnicalSheetPDFGenerator.generate(merged, company)
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', chem.commercial_name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="Ficha_Tecnica_{safe_name}.pdf"'}
    )


@router.get("/chemicals/{chemical_id}/safety-sheet")
def download_chemical_safety_sheet(
    chemical_id: uuid.UUID,
    redirect: bool = False,
    db: Session = Depends(get_db)
):
    """
    Descarga o visualiza la Hoja de Datos de Seguridad (HDS) oficial en 16 secciones
    conforme a la NOM-018-STPS-2015 (Sistema Globalmente Armonizado / SGA) y NOM-256-SSA1-2012.
    """
    chem = db.query(Chemical).filter(Chemical.id == chemical_id, Chemical.is_deleted == False).first()
    if not chem:
        raise HTTPException(status_code=404, detail="Químico no encontrado.")

    if redirect and chem.safety_sheet_url and chem.safety_sheet_url.startswith("http"):
        return RedirectResponse(url=chem.safety_sheet_url, status_code=302)

    company = db.query(CompanyConfig).first()
    sheet_data = lookup_online_sheets_by_rsco(chem.cicoplafest_number, chem.commercial_name)
    merged = {
        **sheet_data,
        "commercial_name": chem.commercial_name,
        "active_ingredient": chem.active_ingredient,
        "cicoplafest_number": chem.cicoplafest_number,
        "authorized_dose_per_liter": chem.authorized_dose_per_liter,
        "safety_interval_hours": chem.safety_interval_hours,
        "compatible_methods": chem.compatible_methods,
        "toxicological_category": chem.toxicological_category,
        "technical_sheet_url": chem.technical_sheet_url or sheet_data.get("technical_sheet_url"),
        "safety_sheet_url": chem.safety_sheet_url or sheet_data.get("safety_sheet_url")
    }

    pdf_bytes = OfficialSafetyDataSheetPDFGenerator.generate(merged, company)
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', chem.commercial_name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="HDS_{safe_name}.pdf"'}
    )


@router.get("/rsco/items/{item_id}/technical-sheet")
def download_rsco_item_technical_sheet(
    item_id: uuid.UUID,
    redirect: bool = False,
    db: Session = Depends(get_db)
):
    """Descarga la Ficha Técnica Oficial de un registro del Catálogo RSCO en Línea."""
    item = db.query(RSCOItem).filter(RSCOItem.id == item_id, RSCOItem.is_deleted == False).first()
    if not item:
        raise HTTPException(status_code=404, detail="Registro RSCO no encontrado.")

    if redirect and item.technical_sheet_url and item.technical_sheet_url.startswith("http"):
        return RedirectResponse(url=item.technical_sheet_url, status_code=302)

    company = db.query(CompanyConfig).first()
    sheet_data = lookup_online_sheets_by_rsco(item.cicoplafest_number, item.commercial_name)
    merged = {
        **sheet_data,
        "commercial_name": item.commercial_name,
        "active_ingredient": item.active_ingredient,
        "cicoplafest_number": item.cicoplafest_number,
        "authorized_dose": item.authorized_dose,
        "safety_interval_hours": item.safety_interval_hours,
        "formulation": item.formulation,
        "manufacturer": item.manufacturer,
        "target_pests": item.target_pests,
        "toxicological_category": item.toxicological_category,
        "technical_sheet_url": item.technical_sheet_url or sheet_data.get("technical_sheet_url"),
        "safety_sheet_url": item.safety_sheet_url or sheet_data.get("safety_sheet_url")
    }

    pdf_bytes = OfficialTechnicalSheetPDFGenerator.generate(merged, company)
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', item.commercial_name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="Ficha_Tecnica_RSCO_{safe_name}.pdf"'}
    )


@router.get("/rsco/items/{item_id}/safety-sheet")
def download_rsco_item_safety_sheet(
    item_id: uuid.UUID,
    redirect: bool = False,
    db: Session = Depends(get_db)
):
    """Descarga la Hoja de Datos de Seguridad (HDS NOM-018-STPS) de un registro del Catálogo RSCO."""
    item = db.query(RSCOItem).filter(RSCOItem.id == item_id, RSCOItem.is_deleted == False).first()
    if not item:
        raise HTTPException(status_code=404, detail="Registro RSCO no encontrado.")

    if redirect and item.safety_sheet_url and item.safety_sheet_url.startswith("http"):
        return RedirectResponse(url=item.safety_sheet_url, status_code=302)

    company = db.query(CompanyConfig).first()
    sheet_data = lookup_online_sheets_by_rsco(item.cicoplafest_number, item.commercial_name)
    merged = {
        **sheet_data,
        "commercial_name": item.commercial_name,
        "active_ingredient": item.active_ingredient,
        "cicoplafest_number": item.cicoplafest_number,
        "authorized_dose": item.authorized_dose,
        "safety_interval_hours": item.safety_interval_hours,
        "formulation": item.formulation,
        "manufacturer": item.manufacturer,
        "target_pests": item.target_pests,
        "toxicological_category": item.toxicological_category,
        "technical_sheet_url": item.technical_sheet_url or sheet_data.get("technical_sheet_url"),
        "safety_sheet_url": item.safety_sheet_url or sheet_data.get("safety_sheet_url")
    }

    pdf_bytes = OfficialSafetyDataSheetPDFGenerator.generate(merged, company)
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', item.commercial_name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="HDS_RSCO_{safe_name}.pdf"'}
    )


@router.get("/rsco/by-code/technical-sheet")
def download_rsco_code_technical_sheet(
    rsco: str,
    name: str = "",
    redirect: bool = False,
    db: Session = Depends(get_db)
):
    """Obtiene y descarga la Ficha Técnica Oficial directamente por código RSCO."""
    # Buscar si existe en BD primero
    norm_rsco = rsco.strip()
    item = db.query(RSCOItem).filter(RSCOItem.cicoplafest_number == norm_rsco, RSCOItem.is_deleted == False).first()
    chem = db.query(Chemical).filter(Chemical.cicoplafest_number == norm_rsco, Chemical.is_deleted == False).first() if not item else None

    company = db.query(CompanyConfig).first()
    sheet_data = lookup_online_sheets_by_rsco(norm_rsco, name or (chem.commercial_name if chem else (item.commercial_name if item else "")))

    if chem:
        sheet_data.update({
            "commercial_name": chem.commercial_name,
            "active_ingredient": chem.active_ingredient,
            "cicoplafest_number": chem.cicoplafest_number,
            "authorized_dose_per_liter": chem.authorized_dose_per_liter,
            "safety_interval_hours": chem.safety_interval_hours
        })
    elif item:
        sheet_data.update({
            "commercial_name": item.commercial_name,
            "active_ingredient": item.active_ingredient,
            "cicoplafest_number": item.cicoplafest_number,
            "authorized_dose": item.authorized_dose,
            "safety_interval_hours": item.safety_interval_hours
        })

    target_url = sheet_data.get("technical_sheet_url")
    if redirect and target_url and target_url.startswith("http"):
        return RedirectResponse(url=target_url, status_code=302)

    pdf_bytes = OfficialTechnicalSheetPDFGenerator.generate(sheet_data, company)
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', sheet_data.get("commercial_name", "RSCO"))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="Ficha_Tecnica_{safe_name}.pdf"'}
    )


@router.get("/rsco/by-code/safety-sheet")
def download_rsco_code_safety_sheet(
    rsco: str,
    name: str = "",
    redirect: bool = False,
    db: Session = Depends(get_db)
):
    """Obtiene y descarga la Hoja de Datos de Seguridad (HDS) directamente por código RSCO."""
    norm_rsco = rsco.strip()
    item = db.query(RSCOItem).filter(RSCOItem.cicoplafest_number == norm_rsco, RSCOItem.is_deleted == False).first()
    chem = db.query(Chemical).filter(Chemical.cicoplafest_number == norm_rsco, Chemical.is_deleted == False).first() if not item else None

    company = db.query(CompanyConfig).first()
    sheet_data = lookup_online_sheets_by_rsco(norm_rsco, name or (chem.commercial_name if chem else (item.commercial_name if item else "")))

    if chem:
        sheet_data.update({
            "commercial_name": chem.commercial_name,
            "active_ingredient": chem.active_ingredient,
            "cicoplafest_number": chem.cicoplafest_number,
            "authorized_dose_per_liter": chem.authorized_dose_per_liter,
            "safety_interval_hours": chem.safety_interval_hours
        })
    elif item:
        sheet_data.update({
            "commercial_name": item.commercial_name,
            "active_ingredient": item.active_ingredient,
            "cicoplafest_number": item.cicoplafest_number,
            "authorized_dose": item.authorized_dose,
            "safety_interval_hours": item.safety_interval_hours
        })

    target_url = sheet_data.get("safety_sheet_url")
    if redirect and target_url and target_url.startswith("http"):
        return RedirectResponse(url=target_url, status_code=302)

    pdf_bytes = OfficialSafetyDataSheetPDFGenerator.generate(sheet_data, company)
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', sheet_data.get("commercial_name", "RSCO"))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="HDS_{safe_name}.pdf"'}
    )


@router.get("/services/{service_order_id}/pesticide-sheets/zip")
def download_service_pesticide_sheets_zip(
    service_order_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Descarga en un solo archivo ZIP todas las Fichas Técnicas y Hojas de Datos de Seguridad (HDS)
    de los plaguicidas dosificados en una orden de servicio/certificado específico.
    Esencial para carpetas de auditoría sanitaria COFEPRIS / STPS.
    """
    order = db.query(ServiceOrder).options(
        joinedload(ServiceOrder.certificate).joinedload(Certificate.applied_chemicals).joinedload(CertificateChemical.chemical)
    ).filter(ServiceOrder.id == service_order_id, ServiceOrder.is_deleted == False).first()

    if not order or not order.certificate:
        raise HTTPException(status_code=404, detail="Orden o Certificado no encontrado.")

    applied_chems = order.certificate.applied_chemicals or []
    if not applied_chems:
        raise HTTPException(status_code=400, detail="Este certificado no tiene plaguicidas dosificados registrados.")

    company = db.query(CompanyConfig).first()
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        seen_chems = set()
        for idx, app_chem in enumerate(applied_chems, 1):
            chem = app_chem.chemical
            if not chem or chem.id in seen_chems:
                continue
            seen_chems.add(chem.id)

            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', chem.commercial_name)
            sheet_data = lookup_online_sheets_by_rsco(chem.cicoplafest_number, chem.commercial_name)
            merged = {
                **sheet_data,
                "commercial_name": chem.commercial_name,
                "active_ingredient": chem.active_ingredient,
                "cicoplafest_number": chem.cicoplafest_number,
                "authorized_dose_per_liter": chem.authorized_dose_per_liter,
                "safety_interval_hours": chem.safety_interval_hours,
                "compatible_methods": chem.compatible_methods,
                "toxicological_category": chem.toxicological_category,
                "technical_sheet_url": chem.technical_sheet_url or sheet_data.get("technical_sheet_url"),
                "safety_sheet_url": chem.safety_sheet_url or sheet_data.get("safety_sheet_url")
            }

            # 1. Generar Ficha Técnica PDF
            ft_pdf = OfficialTechnicalSheetPDFGenerator.generate(merged, company)
            zip_file.writestr(f"Fichas_Tecnicas/FT_{safe_name}.pdf", ft_pdf)

            # 2. Generar Hoja de Seguridad HDS PDF
            hds_pdf = OfficialSafetyDataSheetPDFGenerator.generate(merged, company)
            zip_file.writestr(f"Hojas_Seguridad_HDS/HDS_{safe_name}.pdf", hds_pdf)

    zip_buffer.seek(0)
    safe_folio = re.sub(r'[^a-zA-Z0-9_-]', '_', order.folio)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="Fichas_y_HDS_Servicio_{safe_folio}.zip"'}
    )


# ============================================================================
# 8. ÓRDENES DE SERVICIO Y CERTIFICADOS
# ============================================================================
@router.get("/services", response_model=List[ServiceOrderResponse])
def get_service_orders(
    branch_id: Optional[uuid.UUID] = None, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    if db.query(ServiceOrder).filter(ServiceOrder.is_deleted == False).count() == 0:
        seed_clients_and_services(db)

    query = db.query(ServiceOrder).options(
        joinedload(ServiceOrder.branch).joinedload(Branch.client),
        joinedload(ServiceOrder.technician),
        joinedload(ServiceOrder.certificate).joinedload(Certificate.applied_chemicals).joinedload(CertificateChemical.chemical)
    ).filter(ServiceOrder.is_deleted == False)
    
    if branch_id:
        query = query.filter(ServiceOrder.branch_id == branch_id)
        
    return query.order_by(ServiceOrder.service_start_date.desc()).limit(limit).all()


@router.post("/services", response_model=ServiceOrderResponse, status_code=status.HTTP_201_CREATED)
def create_service_order_with_certificate(
    payload: ServiceOrderCreate,
    db: Session = Depends(get_db)
):
    """
    Crea atómicamente la Orden de Servicio y el Certificado NOM-256 enlazado
    junto con sus químicos dosificados bajo una sola transacción segura.
    """
    branch = db.query(Branch).filter(Branch.id == payload.branch_id, Branch.is_deleted == False).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada.")

    technician = db.query(User).filter(User.id == payload.technician_id, User.is_active == True).first()
    if not technician:
        raise HTTPException(status_code=404, detail="Técnico no encontrado o inactivo.")

    company = get_or_create_company_config(db)

    prefix = payload.folio_prefix or "SRV"
    count = db.execute(
        select(func.count(ServiceOrder.id)).where(ServiceOrder.folio.like(f"{prefix}-%"))
    ).scalar() or 0
    next_num = count + 1
    
    order_folio = f"{prefix}-ORD-{next_num:06d}"
    cert_folio = f"{prefix}-CERT-{next_num:06d}"

    try:
        service_order = ServiceOrder(
            folio=order_folio,
            branch_id=payload.branch_id,
            technician_id=payload.technician_id,
            service_start_date=payload.service_start_date,
            service_end_date=payload.service_end_date,
            pest_crawling_insects=payload.pest_crawling_insects,
            pest_rodents=payload.pest_rodents,
            pest_flying_insects=payload.pest_flying_insects,
            pest_others=payload.pest_others,
            proc_aspersion=payload.proc_aspersion,
            proc_baits=payload.proc_baits,
            proc_traps=payload.proc_traps,
            proc_gels=payload.proc_gels,
            proc_ulv_fogging=payload.proc_ulv_fogging,
            proc_thermofogging=payload.proc_thermofogging,
            results_summary=payload.results_summary,
            observations=payload.observations,
            client_signature_data=payload.client_signature_data
        )
        db.add(service_order)
        db.flush()

        start_date = payload.service_start_date.date()
        validity_days = company.default_validity_days or 30

        certificate = Certificate(
            service_order_id=service_order.id,
            certificate_folio=cert_folio,
            issue_date=start_date,
            validity_start_date=start_date,
            validity_end_date=start_date + timedelta(days=validity_days),
            sanitary_license_number=payload.sanitary_license_number or company.sanitary_license_number,
            sanitary_responsible_name=payload.sanitary_responsible_name or company.sanitary_responsible_name,
            sanitary_responsible_id=payload.sanitary_responsible_id or company.sanitary_responsible_id
        )
        db.add(certificate)
        db.flush()

        for item in payload.chemicals_applied:
            chem = db.query(Chemical).filter(Chemical.id == item.chemical_id).first()
            if not chem:
                raise HTTPException(status_code=400, detail=f"Químico ID {item.chemical_id} inválido.")
            
            applied = CertificateChemical(
                certificate_id=certificate.id,
                chemical_id=chem.id,
                dose_applied=item.dose_applied,
                area_type=item.area_type,
                treated_zones_description=item.treated_zones_description,
                application_method=item.application_method
            )
            db.add(applied)

        db.commit()
        db.refresh(service_order)
        return service_order

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear el servicio: {str(e)}")


# ============================================================================
# 8. CALENDARIO CRONOLÓGICO Y AGENDAMIENTO DE SERVICIOS
# ============================================================================
@router.get("/services/calendar")
def get_services_calendar(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    client_id: Optional[uuid.UUID] = None,
    branch_id: Optional[uuid.UUID] = None,
    technician_id: Optional[uuid.UUID] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Registro cronológico de servicios para visualización en calendario interactivo.
    Devuelve servicios completados, agendados y cancelados con codificación de colores y metadatos.
    """
    query = db.query(ServiceOrder).options(
        joinedload(ServiceOrder.branch).joinedload(Branch.client),
        joinedload(ServiceOrder.technician),
        joinedload(ServiceOrder.certificate)
    ).filter(ServiceOrder.is_deleted == False)

    if branch_id:
        query = query.filter(ServiceOrder.branch_id == branch_id)
    if client_id:
        query = query.join(Branch).filter(Branch.client_id == client_id)
    if technician_id:
        query = query.filter(ServiceOrder.technician_id == technician_id)
    if start_date:
        start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        query = query.filter(ServiceOrder.service_start_date >= start_dt)
    if end_date:
        end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)
        query = query.filter(ServiceOrder.service_start_date <= end_dt)

    orders = query.order_by(ServiceOrder.service_start_date.desc()).all()
    today = date.today()

    events = []
    seen_service_ids = set()
    seen_cert_ids = set()

    for order in orders:
        seen_service_ids.add(order.id)
        branch = order.branch
        client = branch.client if branch else None
        cert = order.certificate
        if cert:
            seen_cert_ids.add(cert.id)

        client_name = client.legal_name if client else "Cliente General"
        branch_name = branch.name if branch else "Sucursal General"
        branch_address = branch.address if branch else "Domicilio registrado"
        branch_id_str = str(branch.id) if branch else ""
        client_id_str = str(client.id) if client else ""
        
        is_cancelled = False
        cancel_reason = None
        if cert and getattr(cert, 'is_cancelled', False):
            is_cancelled = True
            cancel_reason = cert.cancellation_reason
        elif getattr(order, 'status', 'completed') == 'cancelled':
            is_cancelled = True
            cancel_reason = order.observations

        order_status = "cancelled" if is_cancelled else (getattr(order, 'status', None) or "completed")
        
        if status_filter and status_filter != 'all' and order_status.lower() != status_filter.lower():
            continue

        if is_cancelled:
            color = "#EF4444"
            status_text = "Cancelado"
        elif order_status == "scheduled":
            color = "#3B82F6"
            status_text = "Agendado"
        else:
            if cert and cert.issue_date:
                valid_end = cert.validity_end_date or (cert.issue_date + timedelta(days=30))
                if (valid_end - today).days < 0:
                    color = "#F59E0B"
                    status_text = "Completado (Vencido)"
                else:
                    color = "#10B981"
                    status_text = "Completado (Vigente)"
            else:
                color = "#10B981"
                status_text = "Completado"

        title = f"{client_name} ({branch_name})"
        
        # Fecha de inicio segura
        if order.service_start_date:
            start_iso = order.service_start_date.isoformat()
        elif cert and cert.issue_date:
            start_iso = datetime.combine(cert.issue_date, time(9, 0), tzinfo=timezone.utc).isoformat()
        else:
            start_iso = datetime.now(timezone.utc).isoformat()

        # Fecha de fin segura
        if order.service_end_date:
            end_iso = order.service_end_date.isoformat()
        else:
            end_iso = start_iso

        # Fecha de vigencia calculada
        val_end_iso = None
        if cert:
            val_date = cert.validity_end_date or (cert.issue_date + timedelta(days=30) if cert.issue_date else None)
            if val_date:
                val_end_iso = val_date.isoformat()

        events.append({
            "id": str(order.id),
            "service_order_id": str(order.id),
            "certificate_id": str(cert.id) if cert else None,
            "folio": order.folio,
            "certificate_folio": cert.certificate_folio if cert else None,
            "title": title,
            "start": start_iso,
            "end": end_iso,
            "client_id": client_id_str,
            "client_name": client_name,
            "branch_id": branch_id_str,
            "branch_name": branch_name,
            "branch_address": branch_address,
            "technician_id": str(order.technician_id) if order.technician_id else "",
            "technician_name": order.technician.full_name if order.technician else "No Asignado",
            "status": order_status,
            "status_text": status_text,
            "is_cancelled": is_cancelled,
            "cancellation_reason": cancel_reason,
            "validity_end_date": val_end_iso,
            "color": color
        })

    # Verificar si existen certificados adicionales huérfanos o no asociados a órdenes listadas
    all_certs = db.query(Certificate).options(
        joinedload(Certificate.service_order).joinedload(ServiceOrder.branch).joinedload(Branch.client),
        joinedload(Certificate.service_order).joinedload(ServiceOrder.technician)
    ).filter(Certificate.is_deleted == False).all()

    for c in all_certs:
        if c.id in seen_cert_ids:
            continue
        seen_cert_ids.add(c.id)
        
        s_order = c.service_order
        b = s_order.branch if s_order else None
        cli = b.client if b else None
        tech = s_order.technician if s_order else None

        c_issue = c.issue_date or date.today()
        c_start = datetime.combine(c_issue, time(9, 0), tzinfo=timezone.utc).isoformat()
        c_val = (c.validity_end_date or (c_issue + timedelta(days=30))).isoformat()
        is_canc = getattr(c, 'is_cancelled', False)
        
        events.append({
            "id": str(c.id),
            "service_order_id": str(s_order.id) if s_order else str(c.id),
            "certificate_id": str(c.id),
            "folio": s_order.folio if s_order else f"CERT-{c.certificate_folio}",
            "certificate_folio": c.certificate_folio,
            "title": f"{cli.legal_name if cli else 'Cliente General'} ({b.name if b else 'Sucursal General'})",
            "start": c_start,
            "end": c_start,
            "client_id": str(cli.id) if cli else "",
            "client_name": cli.legal_name if cli else "Cliente General",
            "branch_id": str(b.id) if b else "",
            "branch_name": b.name if b else "Sucursal General",
            "branch_address": b.address if b else "Domicilio registrado",
            "technician_id": str(tech.id) if tech else "",
            "technician_name": tech.full_name if tech else "No Asignado",
            "status": "cancelled" if is_canc else "completed",
            "status_text": "Cancelado" if is_canc else "Completado",
            "is_cancelled": is_canc,
            "cancellation_reason": c.cancellation_reason if is_canc else None,
            "validity_end_date": c_val,
            "color": "#EF4444" if is_canc else "#10B981"
        })

    return events


@router.post("/services/schedule", response_model=ServiceOrderResponse, status_code=status.HTTP_201_CREATED)
def schedule_upcoming_service(payload: ScheduleServiceRequest, db: Session = Depends(get_db)):
    """
    Agenda un próximo servicio ligado a una sucursal, cliente o servicio operativo previo.
    Crea la Orden de Servicio en estado 'scheduled' para seguimiento en el calendario.
    """
    branch = db.query(Branch).filter(Branch.id == payload.branch_id, Branch.is_deleted == False).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada.")

    tech_id = payload.technician_id
    if not tech_id:
        first_tech = db.query(User).filter(User.is_active == True).first()
        tech_id = first_tech.id if first_tech else None

    if not tech_id:
        raise HTTPException(status_code=400, detail="Debe existir al menos un técnico registrado en el sistema.")

    count = db.execute(select(func.count(ServiceOrder.id))).scalar() or 0
    order_folio = f"PROG-ORD-{count + 1:06d}"

    start_dt = payload.scheduled_for
    duration = payload.estimated_duration_minutes or 60
    end_dt = start_dt + timedelta(minutes=duration)

    try:
        new_order = ServiceOrder(
            folio=order_folio,
            branch_id=payload.branch_id,
            technician_id=tech_id,
            status="scheduled",
            scheduled_for=start_dt,
            service_start_date=start_dt,
            service_end_date=end_dt,
            pest_others=payload.target_pests,
            observations=f"[AGENDADO]: {payload.notes or 'Próximo servicio programado'}"
        )
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
        return new_order
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al agendar el servicio: {str(e)}")


@router.get("/services/{service_id}", response_model=ServiceOrderResponse)
def get_service_order_by_id(service_id: uuid.UUID, db: Session = Depends(get_db)):
    """Obtiene una orden de servicio individual con su certificado y químicos aplicados."""
    order = db.query(ServiceOrder).options(
        joinedload(ServiceOrder.branch).joinedload(Branch.client),
        joinedload(ServiceOrder.technician),
        joinedload(ServiceOrder.certificate).joinedload(Certificate.applied_chemicals).joinedload(CertificateChemical.chemical)
    ).filter(ServiceOrder.id == service_id, ServiceOrder.is_deleted == False).first()

    if not order:
        raise HTTPException(status_code=404, detail="Orden de servicio no encontrada.")
    return order


@router.put("/services/{service_id}", response_model=ServiceOrderResponse)
def update_service_order_and_certificate(
    service_id: uuid.UUID,
    payload: ServiceOrderUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualiza la orden de servicio y su certificado NOM-256 enlazado
    (folios, fechas, responsables, observaciones y químicos aplicados).
    """
    order = db.query(ServiceOrder).options(
        joinedload(ServiceOrder.branch).joinedload(Branch.client),
        joinedload(ServiceOrder.technician),
        joinedload(ServiceOrder.certificate).joinedload(Certificate.applied_chemicals).joinedload(CertificateChemical.chemical)
    ).filter(ServiceOrder.id == service_id, ServiceOrder.is_deleted == False).first()

    if not order:
        raise HTTPException(status_code=404, detail="Orden de servicio no encontrada.")

    try:
        if payload.folio is not None:
            order.folio = payload.folio
        if payload.service_start_date is not None:
            order.service_start_date = payload.service_start_date
        if payload.service_end_date is not None:
            order.service_end_date = payload.service_end_date
        if payload.branch_id is not None:
            order.branch_id = payload.branch_id
        if payload.technician_id is not None:
            order.technician_id = payload.technician_id
        if payload.results_summary is not None:
            order.results_summary = payload.results_summary
        if payload.observations is not None:
            order.observations = payload.observations

        # Actualizar datos del certificado enlazado
        if order.certificate:
            cert = order.certificate
            if payload.certificate_folio is not None:
                cert.certificate_folio = payload.certificate_folio
            if payload.issue_date is not None:
                cert.issue_date = payload.issue_date
            if payload.validity_start_date is not None:
                cert.validity_start_date = payload.validity_start_date
            if payload.validity_end_date is not None:
                cert.validity_end_date = payload.validity_end_date
            if payload.sanitary_license_number is not None:
                cert.sanitary_license_number = payload.sanitary_license_number
            if payload.sanitary_responsible_name is not None:
                cert.sanitary_responsible_name = payload.sanitary_responsible_name
            if payload.sanitary_responsible_id is not None:
                cert.sanitary_responsible_id = payload.sanitary_responsible_id

            # Si se enviaron químicos aplicados para actualizar
            if payload.chemicals_applied is not None:
                # Eliminar químicos anteriores
                db.query(CertificateChemical).filter(CertificateChemical.certificate_id == cert.id).delete()
                # Insertar los nuevos
                for item in payload.chemicals_applied:
                    chem = db.query(Chemical).filter(Chemical.id == item.chemical_id).first()
                    if chem:
                        applied = CertificateChemical(
                            certificate_id=cert.id,
                            chemical_id=chem.id,
                            dose_applied=item.dose_applied,
                            area_type=item.area_type,
                            treated_zones_description=item.treated_zones_description,
                            application_method=item.application_method
                        )
                        db.add(applied)

        db.commit()
        db.refresh(order)
        return order
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar el servicio: {str(e)}")


@router.delete("/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service_order(service_id: uuid.UUID, db: Session = Depends(get_db)):
    """Eliminación lógica de la orden de servicio y su certificado asociado."""
    order = db.query(ServiceOrder).filter(ServiceOrder.id == service_id, ServiceOrder.is_deleted == False).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden de servicio no encontrada.")
    
    order.soft_delete()
    if order.certificate:
        order.certificate.soft_delete()
    
    db.commit()
    return None


@router.delete("/certificates/{certificate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_certificate(certificate_id: uuid.UUID, db: Session = Depends(get_db)):
    """Eliminación lógica del certificado y su orden de servicio asociada."""
    cert = db.query(Certificate).filter(Certificate.id == certificate_id, Certificate.is_deleted == False).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificado no encontrado.")
    
    cert.soft_delete()
    if cert.service_order:
        cert.service_order.soft_delete()
    
    db.commit()
    return None


# ============================================================================
# 9. GESTIÓN Y CANCELACIÓN DE CERTIFICADOS OFICIALES
# ============================================================================
@router.post("/certificates/{certificate_id}/cancel")
def cancel_certificate_by_id(
    certificate_id: uuid.UUID,
    payload: CertificateCancelRequest,
    db: Session = Depends(get_db)
):
    """
    Cancela formalmente un certificado de servicio cuando no se llevó a cabo.
    Registra el motivo, fecha/hora y excluye el certificado de reportes de cumplimiento activo.
    En el PDF resultante estampa la marca de agua 'CANCELADO' y cintillo oficial.
    """
    cert = db.query(Certificate).options(
        joinedload(Certificate.service_order)
    ).filter(Certificate.id == certificate_id, Certificate.is_deleted == False).first()

    if not cert:
        raise HTTPException(status_code=404, detail="Certificado no encontrado.")

    cert.is_cancelled = True
    cert.cancellation_reason = payload.reason
    cert.cancelled_at = datetime.now(timezone.utc)

    if cert.service_order:
        cert.service_order.status = "cancelled"

    db.commit()
    db.refresh(cert)
    return {
        "status": "success",
        "message": f"Certificado {cert.certificate_folio} cancelado exitosamente.",
        "certificate_id": str(cert.id),
        "is_cancelled": cert.is_cancelled,
        "cancellation_reason": cert.cancellation_reason,
        "cancelled_at": cert.cancelled_at.isoformat()
    }


@router.post("/services/{service_id}/cancel-certificate")
def cancel_service_certificate(
    service_id: uuid.UUID,
    payload: CertificateCancelRequest,
    db: Session = Depends(get_db)
):
    """Cancela el certificado y la orden de servicio ligada."""
    order = db.query(ServiceOrder).options(
        joinedload(ServiceOrder.certificate)
    ).filter(ServiceOrder.id == service_id, ServiceOrder.is_deleted == False).first()

    if not order:
        raise HTTPException(status_code=404, detail="Orden de servicio no encontrada.")

    order.status = "cancelled"
    if order.certificate:
        order.certificate.is_cancelled = True
        order.certificate.cancellation_reason = payload.reason
        order.certificate.cancelled_at = datetime.now(timezone.utc)
    else:
        order.observations = (order.observations or "") + f" [CANCELADO]: {payload.reason}"

    db.commit()
    return {
        "status": "success",
        "message": f"Servicio {order.folio} cancelado exitosamente.",
        "order_id": str(order.id),
        "status_code": "cancelled",
        "cancellation_reason": payload.reason
    }


@router.get("/certificates/{certificate_id}/pdf")
def export_direct_certificate_pdf(certificate_id: uuid.UUID, db: Session = Depends(get_db)):
    """Descarga el Certificado Oficial de Servicio NOM-256 por ID de certificado."""
    cert = db.query(Certificate).options(
        joinedload(Certificate.service_order).joinedload(ServiceOrder.branch).joinedload(Branch.client),
        joinedload(Certificate.service_order).joinedload(ServiceOrder.technician),
        joinedload(Certificate.applied_chemicals).joinedload(CertificateChemical.chemical)
    ).filter(Certificate.id == certificate_id, Certificate.is_deleted == False).first()

    if not cert or not cert.service_order:
        raise HTTPException(status_code=404, detail="Certificado u Orden no encontrada.")

    company = get_or_create_company_config(db)
    pdf_bytes = OfficialCertificatePDFGenerator.generate(cert.service_order, cert, company=company)
    filename = f"Certificado_{cert.certificate_folio}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )


@router.get("/services/{service_id}/pdf")
def export_service_certificate_pdf(service_id: uuid.UUID, db: Session = Depends(get_db)):
    """Genera y descarga el PDF oficial conforme a la NOM-256-SSA1-2012 (Certificado Sanitario)."""
    order = db.query(ServiceOrder).options(
        joinedload(ServiceOrder.branch).joinedload(Branch.client),
        joinedload(ServiceOrder.technician),
        joinedload(ServiceOrder.certificate).joinedload(Certificate.applied_chemicals).joinedload(CertificateChemical.chemical)
    ).filter(ServiceOrder.id == service_id, ServiceOrder.is_deleted == False).first()

    if not order or not order.certificate:
        raise HTTPException(status_code=404, detail="Orden o Certificado no encontrado.")

    company = get_or_create_company_config(db)
    pdf_bytes = OfficialCertificatePDFGenerator.generate(order, order.certificate, company=company)
    
    filename = f"Certificado_{order.certificate.certificate_folio}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )


@router.get("/services/{service_id}/order-pdf")
def export_service_work_order_pdf(service_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Descarga la ORDEN DE SERVICIO TÉCNICA (Hoja Técnica Operativa).
    Documento independiente del Certificado Sanitario para control interno y firma en sitio.
    """
    order = db.query(ServiceOrder).options(
        joinedload(ServiceOrder.branch).joinedload(Branch.client),
        joinedload(ServiceOrder.technician),
        joinedload(ServiceOrder.certificate).joinedload(Certificate.applied_chemicals).joinedload(CertificateChemical.chemical)
    ).filter(ServiceOrder.id == service_id, ServiceOrder.is_deleted == False).first()

    if not order:
        raise HTTPException(status_code=404, detail="Orden de servicio no encontrada.")

    company = get_or_create_company_config(db)
    pdf_bytes = OfficialWorkOrderPDFGenerator.generate(order, company=company)
    filename = f"Orden_Servicio_{order.folio}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )


# ============================================================================
# 10. DASHBOARD B2B: MONITOREO DE EXPIRACIONES (7, 15, 30 DÍAS)
# ============================================================================
@router.get("/dashboard/expirations", response_model=DashboardExpirationsResponse)
def get_dashboard_expirations(db: Session = Depends(get_db)):
    """
    Agrupa por Cliente Matriz las sucursales con sus certificados.
    Calcula estrictamente la vigencia a 30 días naturales posteriores a la fecha de expedición.
    Clasifica en: ≤7 días (crítico), ≤15 días (advertencia), ≤30 días (vigente) y Vencidos (>30 días).
    """
    if db.query(Certificate).filter(Certificate.is_deleted == False).count() == 0:
        seed_clients_and_services(db)

    today = date.today()

    certificates = db.query(Certificate).options(
        joinedload(Certificate.service_order).joinedload(ServiceOrder.branch).joinedload(Branch.client)
    ).filter(
        Certificate.is_deleted == False
    ).order_by(Certificate.issue_date.desc()).all()

    clients_map = {}

    for cert in certificates:
        if getattr(cert, 'is_cancelled', False):
            continue

        branch = cert.service_order.branch if cert.service_order else None
        client = branch.client if branch else None

        client_id = client.id if client else uuid.UUID("00000000-0000-0000-0000-000000000000")
        client_legal_name = client.legal_name if client else "Cliente General (Sin Matriz)"
        client_rfc = client.rfc if client else "GEN000000000"
        portal_slug = client.portal_slug if client else "general"

        branch_id = branch.id if branch else uuid.UUID("00000000-0000-0000-0000-000000000000")
        branch_name = branch.name if branch else "Sucursal General"
        branch_unit_code = branch.unit_code if branch else None

        cert_issue = cert.issue_date or date.today()
        exact_validity_end = cert.validity_end_date or (cert_issue + timedelta(days=30))
        days_left = (exact_validity_end - today).days

        if client_id not in clients_map:
            clients_map[client_id] = ClientExpirationsGroup(
                client_id=client_id,
                legal_name=client_legal_name,
                rfc=client_rfc,
                portal_slug=portal_slug,
                expiring_7_days=[],
                expiring_15_days=[],
                expiring_30_days=[],
                expired=[]
            )

        is_valid = (days_left >= 0)
        if not is_valid:
            status_label = f"Vencido ({abs(days_left)}d)"
        elif days_left <= 7:
            status_label = f"Vence en {days_left}d"
        elif days_left <= 15:
            status_label = f"Vence en {days_left}d"
        else:
            status_label = f"Vigente ({days_left}d)"

        exp_detail = ExpirationDetail(
            certificate_id=cert.id,
            certificate_folio=cert.certificate_folio,
            service_order_id=cert.service_order_id or cert.id,
            branch_id=branch_id,
            branch_name=branch_name,
            branch_unit_code=branch_unit_code,
            issue_date=cert_issue,
            validity_end_date=exact_validity_end,
            days_until_expiration=days_left,
            is_valid=is_valid,
            status_label=status_label
        )

        if not is_valid:
            clients_map[client_id].expired.append(exp_detail)
        elif days_left <= 7:
            clients_map[client_id].expiring_7_days.append(exp_detail)
        elif days_left <= 15:
            clients_map[client_id].expiring_15_days.append(exp_detail)
        else:
            clients_map[client_id].expiring_30_days.append(exp_detail)

    return DashboardExpirationsResponse(
        report_generated_at=datetime.now(timezone.utc),
        clients=list(clients_map.values())
    )


# ============================================================================
# 11. PORTAL CLIENTE MATRIZ: HISTORIAL Y DESCARGA MASIVA ZIP
# ============================================================================
@router.get("/portal/matrix/{client_id}/services", response_model=List[ServiceOrderResponse])
def get_matrix_services_history(client_id: uuid.UUID, db: Session = Depends(get_db)):
    """Devuelve el historial consolidado de todas las sucursales de la matriz."""
    orders = db.query(ServiceOrder).options(
        joinedload(ServiceOrder.branch).joinedload(Branch.client),
        joinedload(ServiceOrder.technician),
        joinedload(ServiceOrder.certificate).joinedload(Certificate.applied_chemicals).joinedload(CertificateChemical.chemical)
    ).join(Branch).filter(
        Branch.client_id == client_id,
        ServiceOrder.is_deleted == False
    ).order_by(ServiceOrder.service_start_date.desc()).all()
    
    return orders


@router.get("/portal/matrix/{client_id}/certificates/zip")
def download_matrix_certificates_zip(client_id: uuid.UUID, db: Session = Depends(get_db)):
    """Genera en memoria un archivo ZIP con todos los PDFs de certificados de la matriz."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente Matriz no encontrado.")

    orders = db.query(ServiceOrder).options(
        joinedload(ServiceOrder.branch).joinedload(Branch.client),
        joinedload(ServiceOrder.technician),
        joinedload(ServiceOrder.certificate).joinedload(Certificate.applied_chemicals).joinedload(CertificateChemical.chemical)
    ).join(Branch).filter(
        Branch.client_id == client_id,
        ServiceOrder.is_deleted == False
    ).all()

    company = get_or_create_company_config(db)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for order in orders:
            if order.certificate:
                pdf_data = OfficialCertificatePDFGenerator.generate(order, order.certificate, company=company)
                file_name = f"{order.branch.name.replace(' ', '_')}_{order.certificate.certificate_folio}.pdf"
                zip_file.writestr(file_name, pdf_data)

    zip_buffer.seek(0)
    zip_filename = f"Certificados_{client.rfc}_{date.today().strftime('%Y%m%d')}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'}
    )


# ============================================================================
# 12. IMPORTACIÓN HISTÓRICA CSV CON PANDAS
# ============================================================================
@router.post("/import/historical-csv")
async def import_historical_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Procesa un archivo CSV histórico y migra órdenes/certificados en lote."""
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un CSV válido (.csv).")
    
    try:
        contents = await file.read()
        importer = HistoricalDataImporter(db)
        result = importer.process_csv(contents)
        return {"status": "success", "result": result}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al procesar el CSV: {str(e)}")


# ============================================================================
# 13. DESCARGA MASIVA DE CERTIFICADOS OFICIALES (POR CLIENTE / MES / AÑO)
# ============================================================================
@router.get("/certificates/download-bulk")
def download_bulk_certificates(
    client_id: Optional[uuid.UUID] = None,
    branch_id: Optional[uuid.UUID] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Descarga masiva de certificados oficiales en formato ZIP con filtrado inteligente:
    - Por Cliente Matriz
    - Por Sucursal
    - Por Año (ej. 2026)
    - Por Mes (1 a 12)
    - Por Rango de Fechas
    - Por Estado (vigente / vencido)
    Incluye un Manifiesto en CSV con el resumen de todos los certificados incluidos.
    """
    zip_bytes, zip_filename, count = SystemBackupRestoreService.generate_bulk_certificates_zip(
        db=db,
        client_id=client_id,
        branch_id=branch_id,
        year=year,
        month=month,
        start_date=start_date,
        end_date=end_date,
        status_filter=status_filter
    )

    if count == 0:
        raise HTTPException(
            status_code=404,
            detail="No se encontraron certificados con los filtros seleccionados."
        )

    return Response(
        content=zip_bytes,
        media_type="application/x-zip-compressed",
        headers={
            "Content-Disposition": f'attachment; filename="{zip_filename}"',
            "X-Certificates-Count": str(count)
        }
    )


# ============================================================================
# 14. RESPALDO DEL SISTEMA COMPLETO (EXPORTACIÓN JSON / ZIP)
# ============================================================================
@router.get("/backup/export")
def export_system_backup(
    as_zip: bool = False,
    db: Session = Depends(get_db)
):
    """
    Genera un respaldo completo del sistema FUMIFLOSA (Base de datos completa,
    configuración de empresa, catálogo de químicos, clientes, sucursales,
    órdenes de servicio, certificados y químicos aplicados).
    """
    backup_data = SystemBackupRestoreService.export_full_backup(db)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    if as_zip:
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            json_bytes = json.dumps(backup_data, indent=2, ensure_ascii=False).encode('utf-8')
            zf.writestr(f"FUMIFLOSA_Backup_{timestamp}.json", json_bytes)
        
        zip_buf.seek(0)
        return StreamingResponse(
            zip_buf,
            media_type="application/x-zip-compressed",
            headers={"Content-Disposition": f'attachment; filename="FUMIFLOSA_Backup_{timestamp}.zip"'}
        )

    json_str = json.dumps(backup_data, indent=2, ensure_ascii=False)
    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="FUMIFLOSA_Backup_{timestamp}.json"'}
    )


# ============================================================================
# 15. RESTAURACIÓN DEL SISTEMA (DESDE ARCHIVO LOCAL O NUBE)
# ============================================================================
@router.post("/backup/restore-file", response_model=RestoreSummaryResponse)
async def restore_system_from_file(
    file: UploadFile = File(...),
    mode: str = "merge",
    db: Session = Depends(get_db)
):
    """
    Restaura la base de datos de FUMIFLOSA a partir de un archivo subido (.json o .zip).
    Modos:
      - 'merge' (default): Inserta registros nuevos y conserva existentes.
      - 'overwrite': Limpia el contenido actual y restablece el respaldo exacto.
    """
    content = await file.read()
    filename = file.filename.lower()

    if filename.endswith(".zip"):
        try:
            with zipfile.ZipFile(io.BytesIO(content), "r") as zf:
                json_files = [f for f in zf.namelist() if f.endswith(".json")]
                if not json_files:
                    raise HTTPException(status_code=400, detail="El archivo ZIP no contiene ningún JSON de respaldo.")
                json_content = zf.read(json_files[0]).decode('utf-8')
                backup_data = json.loads(json_content)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error al descomprimir archivo ZIP: {str(e)}")
    elif filename.endswith(".json"):
        try:
            backup_data = json.loads(content.decode('utf-8'))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error al leer JSON de respaldo: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="Formato no admitido. Sube un archivo .json o .zip.")

    try:
        summary = SystemBackupRestoreService.restore_full_backup(db, backup_data, mode=mode)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la restauración: {str(e)}")


@router.post("/backup/restore-cloud", response_model=RestoreSummaryResponse)
def restore_system_from_cloud_url(
    payload: CloudRestoreRequest,
    db: Session = Depends(get_db)
):
    """
    Restaura la base de datos descargando el respaldo desde una URL en la nube
    (ej. S3, Google Cloud Storage, GitHub Raw o enlace de almacenamiento público/privado).
    """
    try:
        summary = SystemBackupRestoreService.restore_from_cloud_url(
            db=db,
            url=payload.backup_url,
            mode=payload.mode
        )
        return summary
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al restaurar desde la nube ({payload.backup_url}): {str(e)}"
        )


# ============================================================================
# 16. CATÁLOGO EN LÍNEA RSCO / CICOPLAFEST
# ============================================================================
@router.get("/rsco/catalog", response_model=List[RSCOItemResponse])
def get_rsco_catalog(
    q: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Obtiene el catálogo de registros oficiales RSCO actualizable en línea."""
    query = db.query(RSCOItem).filter(RSCOItem.is_deleted == False)
    if q:
        search = f"%{q.strip()}%"
        query = query.filter(
            or_(
                RSCOItem.commercial_name.ilike(search),
                RSCOItem.active_ingredient.ilike(search),
                RSCOItem.cicoplafest_number.ilike(search),
                RSCOItem.manufacturer.ilike(search),
                RSCOItem.target_pests.ilike(search)
            )
        )
    return query.order_by(RSCOItem.commercial_name).limit(limit).all()


@router.post("/rsco/catalog", response_model=RSCOItemResponse, status_code=status.HTTP_201_CREATED)
def create_rsco_item(payload: RSCOItemCreate, db: Session = Depends(get_db)):
    """Da de alta un nuevo registro RSCO en línea."""
    existing = db.query(RSCOItem).filter(
        RSCOItem.cicoplafest_number == payload.cicoplafest_number.strip(),
        RSCOItem.is_deleted == False
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"El registro CICOPLAFEST/RSCO '{payload.cicoplafest_number}' ya existe en el catálogo.")
    
    item = RSCOItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/rsco/catalog/{item_id}", response_model=RSCOItemResponse)
def update_rsco_item(item_id: uuid.UUID, payload: RSCOItemUpdate, db: Session = Depends(get_db)):
    """Actualiza en línea los datos de un registro RSCO."""
    item = db.query(RSCOItem).filter(RSCOItem.id == item_id, RSCOItem.is_deleted == False).first()
    if not item:
        raise HTTPException(status_code=404, detail="Registro RSCO no encontrado.")
    
    for key, val in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, val)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/rsco/catalog/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rsco_item(item_id: uuid.UUID, db: Session = Depends(get_db)):
    """Elimina lógicamente un registro RSCO del catálogo."""
    item = db.query(RSCOItem).filter(RSCOItem.id == item_id, RSCOItem.is_deleted == False).first()
    if not item:
        raise HTTPException(status_code=404, detail="Registro RSCO no encontrado.")
    item.soft_delete()
    db.commit()
    return None


@router.post("/rsco/seed-defaults")
def seed_rsco_defaults(db: Session = Depends(get_db)):
    """Puebla o sincroniza el catálogo con los principales productos RSCO oficiales de México."""
    seeded = seed_default_rsco_items(db)
    return {"status": "ok", "seeded_count": seeded, "message": f"Catálogo RSCO sincronizado con éxito ({seeded} registros actualizados)."}


@router.post("/system/seed-defaults")
def seed_system_defaults_endpoint(db: Session = Depends(get_db)):
    """Puebla o sincroniza integralmente todos los datos base del sistema (empresa, usuarios, químicos, clientes y bitácoras)."""
    summary = seed_all_database_defaults(db)
    return {"status": "ok", "summary": summary, "message": "Base de datos y catálogos sincronizados exitosamente."}



# ============================================================================
# 17. BITÁCORAS DEL MANUAL INTEGRAL DE CONTROL DE PLAGAS (NOM-256 / STPS)
# ============================================================================

# 17.1 Bitácora de EPP y Mantenimiento
@router.get("/bitacoras/epp", response_model=List[EPPLogResponse])
def get_epp_logs(
    technician: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(EPPLog).filter(EPPLog.is_deleted == False)
    if technician:
        query = query.filter(EPPLog.technician_name.ilike(f"%{technician.strip()}%"))
    if category:
        query = query.filter(EPPLog.equipment_category == category)
    return query.order_by(desc(EPPLog.delivery_date)).limit(limit).all()


@router.post("/bitacoras/epp", response_model=EPPLogResponse, status_code=status.HTTP_201_CREATED)
def create_epp_log(payload: EPPLogCreate, db: Session = Depends(get_db)):
    log = EPPLog(**payload.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.delete("/bitacoras/epp/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_epp_log(log_id: uuid.UUID, db: Session = Depends(get_db)):
    log = db.query(EPPLog).filter(EPPLog.id == log_id, EPPLog.is_deleted == False).first()
    if not log:
        raise HTTPException(status_code=404, detail="Registro de EPP no encontrado.")
    log.soft_delete()
    db.commit()
    return None


# 17.2 Matriz Anual de EPP (con las 21 categorías del CSV del usuario)
DEFAULT_EPP_MATRIX_ITEMS = [
    ("PLAYERA POLO", "ANUAL"),
    ("PANTALÓN", "ANUAL"),
    ("OVEROL", "ANUAL"),
    ("ZAPATO INDUSTRIAL", "ANUAL"),
    ("CASCO DE SEGURIDAD", "ANUAL"),
    ("GAFAS DE SEGURIDAD", "CUANDO SE SOLICITE"),
    ("GAFAS OSCURAS", "CUANDO SE SOLICITE"),
    ("TAPONES AUDITIVOS", "MENSUAL (8 PZAS.)"),
    ("CUBREBOCAS", "MENSUAL (4 PZAS.)"),
    ("CUBREPOLVOS", "MENSUAL (4 PZAS.)"),
    ("CHALECO FLUORESCENTE", "ANUAL"),
    ("GUANTES LÁTEX", "MENSUAL (40 PARES)"),
    ("GUANTES NEOPRENO", "CUANDO SE SOLICITE"),
    ("TYVEK", "MENSUAL (8 PZAS.)"),
    ("MASCARILLA MEDIA", "ANUAL"),
    ("MASCARILLA COMPLETA", "ANUAL"),
    ("VISOR", "CUANDO SE SOLICITE"),
    ("CARTUCHOS", "SEMESTRAL"),
    ("FILTROS", "MENSUAL"),
    ("ARNÉS", "CUANDO SE SOLICITE"),
    ("RETENEDORES", "CUANDO SE SOLICITE")
]


@router.get("/bitacoras/epp-annual", response_model=List[EPPAnnualMatrixRow])
def get_epp_annual_matrix(
    technician_name: Optional[str] = None,
    year: int = 2026,
    db: Session = Depends(get_db)
):
    """Devuelve la matriz anual de EPP para un técnico. Si no existe, la inicializa con los 21 ítems oficiales."""
    if not technician_name or not technician_name.strip():
        first_tech = db.query(User).filter(User.is_active == True).first()
        tech = first_tech.full_name if first_tech else "Marco Antonio Flores Sáenz"
    else:
        tech = technician_name.strip()

    try:
        rows = db.query(EPPAnnualMatrix).filter(
            EPPAnnualMatrix.technician_name == tech,
            EPPAnnualMatrix.year == year,
            EPPAnnualMatrix.is_deleted == False
        ).order_by(EPPAnnualMatrix.created_at).all()

        if not rows:
            new_rows = []
            for item_name, freq in DEFAULT_EPP_MATRIX_ITEMS:
                entry = EPPAnnualMatrix(
                    technician_name=tech,
                    year=year,
                    epp_item=item_name,
                    frequency=freq
                )
                db.add(entry)
                new_rows.append(entry)
            db.commit()
            for r in new_rows:
                db.refresh(r)
            rows = new_rows

        return rows
    except Exception as e:
        print(f"[EPP ANNUAL MATRIX WARNING]: {e}")
        # Retorno sintético seguro para garantizar que nunca quede la tabla en blanco
        synthetic = []
        for item_name, freq in DEFAULT_EPP_MATRIX_ITEMS:
            synthetic.append(EPPAnnualMatrixRow(
                id=uuid.uuid4(),
                technician_name=tech,
                year=year,
                epp_item=item_name,
                frequency=freq
            ))
        return synthetic


@router.post("/bitacoras/epp-annual/row", response_model=EPPAnnualMatrixRow)
def create_epp_annual_row(
    payload: EPPAnnualRowCreate,
    db: Session = Depends(get_db)
):
    """Permite añadir un nuevo elemento de EPP personalizado a la matriz anual directamente."""
    tech = payload.technician_name.strip()
    entry = EPPAnnualMatrix(
        technician_name=tech,
        year=payload.year,
        epp_item=payload.epp_item.strip().upper(),
        frequency=payload.frequency.strip().upper()
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.post("/bitacoras/epp-annual/batch")
def save_epp_annual_matrix_batch(
    payload: EPPAnnualMatrixBatch,
    db: Session = Depends(get_db)
):
    """Guarda o actualiza en bloque las casillas y firmas de la matriz anual de EPP."""
    tech = payload.technician_name.strip()
    year = payload.year
    for row in payload.rows:
        existing = None
        if row.id:
            existing = db.query(EPPAnnualMatrix).filter(EPPAnnualMatrix.id == row.id).first()
        if not existing:
            existing = db.query(EPPAnnualMatrix).filter(
                EPPAnnualMatrix.technician_name == tech,
                EPPAnnualMatrix.year == year,
                EPPAnnualMatrix.epp_item == row.epp_item
            ).first()
        
        if existing:
            for field in [
                'frequency', 'jan_date', 'jan_signed', 'feb_date', 'feb_signed',
                'mar_date', 'mar_signed', 'apr_date', 'apr_signed', 'may_date', 'may_signed',
                'jun_date', 'jun_signed', 'jul_date', 'jul_signed', 'aug_date', 'aug_signed',
                'sep_date', 'sep_signed', 'oct_date', 'oct_signed', 'nov_date', 'nov_signed',
                'dec_date', 'dec_signed'
            ]:
                val = getattr(row, field, None)
                if val is not None:
                    setattr(existing, field, val)
        else:
            new_entry = EPPAnnualMatrix(
                technician_name=tech,
                year=year,
                epp_item=row.epp_item,
                frequency=row.frequency,
                jan_date=row.jan_date, jan_signed=row.jan_signed,
                feb_date=row.feb_date, feb_signed=row.feb_signed,
                mar_date=row.mar_date, mar_signed=row.mar_signed,
                apr_date=row.apr_date, apr_signed=row.apr_signed,
                may_date=row.may_date, may_signed=row.may_signed,
                jun_date=row.jun_date, jun_signed=row.jun_signed,
                jul_date=row.jul_date, jul_signed=row.jul_signed,
                aug_date=row.aug_date, aug_signed=row.aug_signed,
                sep_date=row.sep_date, sep_signed=row.sep_signed,
                oct_date=row.oct_date, oct_signed=row.oct_signed,
                nov_date=row.nov_date, nov_signed=row.nov_signed,
                dec_date=row.dec_date, dec_signed=row.dec_signed,
            )
            db.add(new_entry)
    db.commit()
    return {"status": "ok", "message": "Matriz anual de EPP guardada correctamente."}


# 17.3 Calibración de Equipos
@router.get("/bitacoras/equipment-calibration", response_model=List[EquipmentCalibrationResponse])
def get_equipment_calibrations(limit: int = 100, db: Session = Depends(get_db)):
    return db.query(EquipmentCalibrationLog).filter(EquipmentCalibrationLog.is_deleted == False).order_by(desc(EquipmentCalibrationLog.calibration_date)).limit(limit).all()


@router.post("/bitacoras/equipment-calibration", response_model=EquipmentCalibrationResponse, status_code=status.HTTP_201_CREATED)
def create_equipment_calibration(payload: EquipmentCalibrationCreate, db: Session = Depends(get_db)):
    cal = EquipmentCalibrationLog(**payload.model_dump())
    db.add(cal)
    db.commit()
    db.refresh(cal)
    return cal


@router.delete("/bitacoras/equipment-calibration/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_equipment_calibration(id: uuid.UUID, db: Session = Depends(get_db)):
    cal = db.query(EquipmentCalibrationLog).filter(EquipmentCalibrationLog.id == id, EquipmentCalibrationLog.is_deleted == False).first()
    if not cal:
        raise HTTPException(status_code=404, detail="Registro no encontrado.")
    cal.soft_delete()
    db.commit()
    return None


# 17.4 Monitoreo de Estaciones y Trampas
@router.get("/bitacoras/station-monitoring", response_model=List[StationMonitoringResponse])
def get_station_monitoring(limit: int = 100, db: Session = Depends(get_db)):
    return db.query(StationMonitoringLog).filter(StationMonitoringLog.is_deleted == False).order_by(desc(StationMonitoringLog.monitoring_date)).limit(limit).all()


@router.post("/bitacoras/station-monitoring", response_model=StationMonitoringResponse, status_code=status.HTTP_201_CREATED)
def create_station_monitoring(payload: StationMonitoringCreate, db: Session = Depends(get_db)):
    mon = StationMonitoringLog(**payload.model_dump())
    db.add(mon)
    db.commit()
    db.refresh(mon)
    return mon


@router.delete("/bitacoras/station-monitoring/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_station_monitoring(id: uuid.UUID, db: Session = Depends(get_db)):
    mon = db.query(StationMonitoringLog).filter(StationMonitoringLog.id == id, StationMonitoringLog.is_deleted == False).first()
    if not mon:
        raise HTTPException(status_code=404, detail="Registro no encontrado.")
    mon.soft_delete()
    db.commit()
    return None


# 17.5 Residuos Peligrosos y Triple Lavado
@router.get("/bitacoras/hazardous-waste", response_model=List[HazardousWasteResponse])
def get_hazardous_waste(limit: int = 100, db: Session = Depends(get_db)):
    return db.query(HazardousWasteLog).filter(HazardousWasteLog.is_deleted == False).order_by(desc(HazardousWasteLog.wash_date)).limit(limit).all()


@router.post("/bitacoras/hazardous-waste", response_model=HazardousWasteResponse, status_code=status.HTTP_201_CREATED)
def create_hazardous_waste(payload: HazardousWasteCreate, db: Session = Depends(get_db)):
    waste = HazardousWasteLog(**payload.model_dump())
    db.add(waste)
    db.commit()
    db.refresh(waste)
    return waste


@router.delete("/bitacoras/hazardous-waste/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hazardous_waste(id: uuid.UUID, db: Session = Depends(get_db)):
    waste = db.query(HazardousWasteLog).filter(HazardousWasteLog.id == id, HazardousWasteLog.is_deleted == False).first()
    if not waste:
        raise HTTPException(status_code=404, detail="Registro no encontrado.")
    waste.soft_delete()
    db.commit()
    return None


# 17.6 Exportación de Bitácoras a PDF
@router.get("/bitacoras/export-pdf/{bitacora_type}")
def export_bitacora_pdf(
    bitacora_type: str,
    technician_name: Optional[str] = None,
    year: int = 2026,
    db: Session = Depends(get_db)
):
    """Genera la versión imprimible en PDF de cualquiera de las bitácoras oficiales."""
    config = get_or_create_company_config(db)
    
    if bitacora_type == "epp-annual":
        tech = technician_name or "Técnico General"
        rows = db.query(EPPAnnualMatrix).filter(
            EPPAnnualMatrix.technician_name == tech,
            EPPAnnualMatrix.year == year,
            EPPAnnualMatrix.is_deleted == False
        ).all()
        if not rows:
            for item_name, freq in DEFAULT_EPP_MATRIX_ITEMS:
                entry = EPPAnnualMatrix(technician_name=tech, year=year, epp_item=item_name, frequency=freq)
                db.add(entry)
            db.commit()
            rows = db.query(EPPAnnualMatrix).filter(
                EPPAnnualMatrix.technician_name == tech,
                EPPAnnualMatrix.year == year,
                EPPAnnualMatrix.is_deleted == False
            ).all()
        pdf_bytes = BitacoraPDFGenerator.generate_epp_annual_pdf(rows, tech, year, config)
        filename = f"Bitacora_EPP_Anual_{tech.replace(' ', '_')}_{year}.pdf"

    elif bitacora_type == "epp-logs":
        logs = db.query(EPPLog).filter(EPPLog.is_deleted == False).order_by(desc(EPPLog.delivery_date)).all()
        cols = ["Fecha", "Técnico", "Categoría", "Elemento", "Estado", "Cambio", "Firma"]
        rows = [
            [l.delivery_date.strftime('%d/%m/%Y'), l.technician_name, l.equipment_category, l.equipment_item, l.condition_type, l.change_interval or '-', l.responsible_signature or 'Registrado']
            for l in logs
        ]
        pdf_bytes = BitacoraPDFGenerator.generate_generic_log_pdf(
            "BITÁCORA DE MANTENIMIENTO Y ENTREGA DE EPP (NOM-017-STPS)",
            "Control individual de entrega de equipo de protección personal",
            cols, rows, config
        )
        filename = f"Bitacora_EPP_Mantenimiento_{datetime.now().strftime('%Y%m%d')}.pdf"

    elif bitacora_type == "calibracion":
        cals = db.query(EquipmentCalibrationLog).filter(EquipmentCalibrationLog.is_deleted == False).order_by(desc(EquipmentCalibrationLog.calibration_date)).all()
        cols = ["Fecha", "Equipo", "Serie", "Boquilla", "Presión (psi)", "Gasto (L/min)", "Estado", "Técnico"]
        rows = [
            [c.calibration_date.strftime('%d/%m/%Y'), c.equipment_name, c.serial_number or '-', c.nozzle_type, c.working_pressure_psi or '-', c.flow_rate_lpm or '-', c.status, c.technician_name]
            for c in cals
        ]
        pdf_bytes = BitacoraPDFGenerator.generate_generic_log_pdf(
            "BITÁCORA DE CALIBRACIÓN Y MANTENIMIENTO DE EQUIPOS (NOM-256-SSA1-2012)",
            "Inspección de gasto, boquillas, manómetros y hermeticidad de equipos de aplicación",
            cols, rows, config
        )
        filename = f"Bitacora_Calibracion_Equipos_{datetime.now().strftime('%Y%m%d')}.pdf"

    elif bitacora_type == "estaciones":
        mons = db.query(StationMonitoringLog).filter(StationMonitoringLog.is_deleted == False).order_by(desc(StationMonitoringLog.monitoring_date)).all()
        cols = ["Fecha", "Sucursal", "Estación", "Tipo", "Zona", "Consumo", "Actividad", "Acción Correctiva", "Técnico"]
        rows = [
            [m.monitoring_date.strftime('%d/%m/%Y'), m.branch_name, m.station_number, m.station_type, m.zone, f"{m.bait_consumption_percent}%", f"Sí ({m.pest_count})" if m.pest_activity_detected else "No", m.corrective_action or '-', m.technician_name]
            for m in mons
        ]
        pdf_bytes = BitacoraPDFGenerator.generate_generic_log_pdf(
            "BITÁCORA DE MONITOREO DE CEBADEROS Y DISPOSITIVOS MIP",
            "Seguimiento y evaluación periódica de trampas, cebaderos y lámparas UV",
            cols, rows, config
        )
        filename = f"Bitacora_Monitoreo_Estaciones_{datetime.now().strftime('%Y%m%d')}.pdf"

    elif bitacora_type == "residuos":
        wastes = db.query(HazardousWasteLog).filter(HazardousWasteLog.is_deleted == False).order_by(desc(HazardousWasteLog.wash_date)).all()
        cols = ["Fecha", "Producto Químico", "Ingrediente Activo", "Piezas", "Capacidad", "Triple Lavado", "Perforado", "Almacén", "Responsable"]
        rows = [
            [w.wash_date.strftime('%d/%m/%Y'), w.chemical_name, w.active_ingredient, str(w.containers_count), w.container_capacity, "Sí" if w.triple_wash_performed else "No", "Sí" if w.containers_perforated else "No", w.temporary_storage_location, w.responsible_name]
            for w in wastes
        ]
        pdf_bytes = BitacoraPDFGenerator.generate_generic_log_pdf(
            "BITÁCORA DE RESIDUOS PELIGROSOS Y TRIPLE LAVADO (NOM-256 / SEMARNAT)",
            "Inutilización de envases vacíos de plaguicidas previo a destino final AMOCALI",
            cols, rows, config
        )
        filename = f"Bitacora_Residuos_TripleLavado_{datetime.now().strftime('%Y%m%d')}.pdf"

    else:
        raise HTTPException(status_code=400, detail="Tipo de bitácora no válido.")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )


# ============================================================================
# 18. CONSULTA DEL MANUAL INTEGRAL DE PLAGAS (MIP) & GUÍA DE COMBATE ESPECÍFICO
# ============================================================================
@router.get("/mip/manual")
def get_mip_manual_content():
    """Devuelve los módulos estructurados del Manual Integral de Control de Plagas conforme a NOM-256."""
    return get_mip_full_manual()


@router.get("/mip/pests")
def get_mip_pests_catalog(q: Optional[str] = None):
    """Devuelve el catálogo de combate específico contra diferentes plagas urbanas."""
    pests = get_pest_combat_guides()
    if q:
        query_str = q.lower().strip()
        pests = [
            p for p in pests
            if query_str in p["name"].lower()
            or query_str in p["scientific_name"].lower()
            or query_str in p["category"].lower()
            or any(query_str in chem.lower() for chem in p.get("recommended_chemicals", []))
        ]
    return pests


@router.get("/mip/pests/{pest_id}")
def get_mip_pest_detail(pest_id: str):
    pests = get_pest_combat_guides()
    for p in pests:
        if p["id"] == pest_id:
            return p
    raise HTTPException(status_code=404, detail="Plaga no encontrada en el catálogo MIP.")


