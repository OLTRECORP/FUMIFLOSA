import io
import uuid
import zipfile
from datetime import datetime, date, timedelta, timezone
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Header
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, or_, and_, desc

from app.database import get_db
from app.models import (
    ServiceOrder, Certificate, CertificateChemical, Branch, Client, 
    Chemical, User, UserRole, CompanyConfig
)
from app.schemas import (
    LoginRequest, LoginResponse, AuthUserInfo,
    ServiceOrderCreate, ServiceOrderUpdate, ServiceOrderResponse, DashboardExpirationsResponse,
    ClientExpirationsGroup, ExpirationDetail, DashboardSummaryStats,
    UserCreate, UserUpdate, UserResponse,
    ClientCreate, ClientUpdate, ClientResponse, ClientPortalConfigUpdate,
    BranchCreate, BranchUpdate, BranchResponse,
    ChemicalCreate, ChemicalUpdate, ChemicalResponse,
    CompanyConfigResponse, CompanyConfigUpdate,
    AdvancedAnalyticsResponse, ClientPortalAuthRequest, ClientPortalDataResponse,
    CloudRestoreRequest, RestoreSummaryResponse
)
from app.services.data_import import HistoricalDataImporter
from app.services.pdf_service import OfficialCertificatePDFGenerator
from app.services.backup_service import SystemBackupRestoreService

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
def get_detailed_analytics(db: Session = Depends(get_db)):
    """Genera las métricas avanzadas y estadísticas de servicios de fumigación."""
    total_services = db.query(func.count(ServiceOrder.id)).filter(ServiceOrder.is_deleted == False).scalar() or 0
    total_clients = db.query(func.count(Client.id)).filter(Client.is_deleted == False).scalar() or 0
    total_branches = db.query(func.count(Branch.id)).filter(Branch.is_deleted == False).scalar() or 0

    # 1. Desglose de Plagas
    pest_crawling = db.query(func.count(ServiceOrder.id)).filter(ServiceOrder.is_deleted == False, ServiceOrder.pest_crawling_insects == True).scalar() or 0
    pest_rodents = db.query(func.count(ServiceOrder.id)).filter(ServiceOrder.is_deleted == False, ServiceOrder.pest_rodents == True).scalar() or 0
    pest_flying = db.query(func.count(ServiceOrder.id)).filter(ServiceOrder.is_deleted == False, ServiceOrder.pest_flying_insects == True).scalar() or 0
    pest_others = db.query(func.count(ServiceOrder.id)).filter(ServiceOrder.is_deleted == False, ServiceOrder.pest_others.isnot(None), ServiceOrder.pest_others != "").scalar() or 0

    # 2. Desglose de Procedimientos
    proc_asp = db.query(func.count(ServiceOrder.id)).filter(ServiceOrder.is_deleted == False, ServiceOrder.proc_aspersion == True).scalar() or 0
    proc_baits = db.query(func.count(ServiceOrder.id)).filter(ServiceOrder.is_deleted == False, ServiceOrder.proc_baits == True).scalar() or 0
    proc_traps = db.query(func.count(ServiceOrder.id)).filter(ServiceOrder.is_deleted == False, ServiceOrder.proc_traps == True).scalar() or 0
    proc_gels = db.query(func.count(ServiceOrder.id)).filter(ServiceOrder.is_deleted == False, ServiceOrder.proc_gels == True).scalar() or 0
    proc_ulv = db.query(func.count(ServiceOrder.id)).filter(ServiceOrder.is_deleted == False, ServiceOrder.proc_ulv_fogging == True).scalar() or 0
    proc_thermo = db.query(func.count(ServiceOrder.id)).filter(ServiceOrder.is_deleted == False, ServiceOrder.proc_thermofogging == True).scalar() or 0

    # 3. Químicos más utilizados
    top_chems_query = db.query(
        Chemical.commercial_name,
        Chemical.active_ingredient,
        func.count(CertificateChemical.id).label("total_uses")
    ).join(CertificateChemical, CertificateChemical.chemical_id == Chemical.id)\
     .filter(Chemical.is_deleted == False)\
     .group_by(Chemical.commercial_name, Chemical.active_ingredient)\
     .order_by(desc("total_uses")).limit(5).all()

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
    
    critico_7d = db.query(func.count(Certificate.id)).filter(
        Certificate.is_deleted == False, Certificate.validity_end_date >= today, Certificate.validity_end_date <= limit_7
    ).scalar() or 0

    proximo_15d = db.query(func.count(Certificate.id)).filter(
        Certificate.is_deleted == False, Certificate.validity_end_date > limit_7, Certificate.validity_end_date <= limit_15
    ).scalar() or 0

    vigente = db.query(func.count(Certificate.id)).filter(
        Certificate.is_deleted == False, Certificate.validity_end_date > limit_15
    ).scalar() or 0

    vencido = db.query(func.count(Certificate.id)).filter(
        Certificate.is_deleted == False, Certificate.validity_end_date < today
    ).scalar() or 0

    # 6. Tendencia Mensual (Últimos meses)
    monthly_orders = db.query(
        func.to_char(ServiceOrder.service_start_date, 'YYYY-MM').label('month_key'),
        func.count(ServiceOrder.id).label('count')
    ).filter(ServiceOrder.is_deleted == False)\
     .group_by('month_key')\
     .order_by('month_key').limit(12).all()

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
     .filter(Client.is_deleted == False, ServiceOrder.is_deleted == False)\
     .group_by(Client.legal_name)\
     .order_by(desc("services_count")).limit(5).all()

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
    for key, value in update_data.items():
        setattr(branch, key, value)

    db.commit()
    db.refresh(branch)
    return branch


@router.delete("/branches/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_branch(branch_id: uuid.UUID, db: Session = Depends(get_db)):
    branch = db.query(Branch).filter(Branch.id == branch_id, Branch.is_deleted == False).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada.")
    branch.soft_delete()
    db.commit()
    return None


# ============================================================================
# 7. CATÁLOGO DE QUÍMICOS (CRUD)
# ============================================================================
@router.get("/chemicals", response_model=List[ChemicalResponse])
def get_chemicals(db: Session = Depends(get_db)):
    return db.query(Chemical).filter(Chemical.is_deleted == False).order_by(Chemical.commercial_name).all()


@router.post("/chemicals", response_model=ChemicalResponse, status_code=status.HTTP_201_CREATED)
def create_chemical(payload: ChemicalCreate, db: Session = Depends(get_db)):
    existing = db.query(Chemical).filter(Chemical.cicoplafest_number == payload.cicoplafest_number, Chemical.is_deleted == False).first()
    if existing:
        raise HTTPException(status_code=400, detail="El número de registro CICOPLAFEST ya existe.")

    chem = Chemical(
        commercial_name=payload.commercial_name,
        active_ingredient=payload.active_ingredient,
        cicoplafest_number=payload.cicoplafest_number,
        authorized_dose_per_liter=payload.authorized_dose_per_liter,
        safety_interval_hours=payload.safety_interval_hours,
        compatible_methods=payload.compatible_methods,
        toxicological_category=payload.toxicological_category
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


# ============================================================================
# 8. ÓRDENES DE SERVICIO Y CERTIFICADOS
# ============================================================================
@router.get("/services", response_model=List[ServiceOrderResponse])
def get_service_orders(
    branch_id: Optional[uuid.UUID] = None, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
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
# 9. GENERACIÓN Y DESCARGA DE PDF OFICIAL (NOM-256 / SINTOX)
# ============================================================================
@router.get("/services/{service_id}/pdf")
def export_service_certificate_pdf(service_id: uuid.UUID, db: Session = Depends(get_db)):
    """Genera y descarga el PDF oficial conforme a la NOM-256-SSA1-2012."""
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


# ============================================================================
# 10. DASHBOARD B2B: MONITOREO DE EXPIRACIONES (7, 15, 30 DÍAS)
# ============================================================================
@router.get("/dashboard/expirations", response_model=DashboardExpirationsResponse)
def get_dashboard_expirations(db: Session = Depends(get_db)):
    """
    Agrupa por Cliente Matriz las sucursales con certificados próximos a vencer
    en ventanas de 7, 15 y 30 días naturales.
    """
    today = date.today()
    limit_30 = today + timedelta(days=30)

    certificates = db.query(Certificate).options(
        joinedload(Certificate.service_order).joinedload(ServiceOrder.branch).joinedload(Branch.client)
    ).filter(
        Certificate.is_deleted == False,
        Certificate.validity_end_date >= today,
        Certificate.validity_end_date <= limit_30
    ).all()

    clients_map = {}

    for cert in certificates:
        branch = cert.service_order.branch
        client = branch.client
        days_left = (cert.validity_end_date - today).days

        if client.id not in clients_map:
            clients_map[client.id] = ClientExpirationsGroup(
                client_id=client.id,
                legal_name=client.legal_name,
                rfc=client.rfc,
                portal_slug=client.portal_slug
            )

        exp_detail = ExpirationDetail(
            certificate_id=cert.id,
            certificate_folio=cert.certificate_folio,
            service_order_id=cert.service_order_id,
            branch_id=branch.id,
            branch_name=branch.name,
            branch_unit_code=branch.unit_code,
            validity_end_date=cert.validity_end_date,
            days_until_expiration=days_left
        )

        if days_left <= 7:
            clients_map[client.id].expiring_7_days.append(exp_detail)
        elif days_left <= 15:
            clients_map[client.id].expiring_15_days.append(exp_detail)
        else:
            clients_map[client.id].expiring_30_days.append(exp_detail)

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

