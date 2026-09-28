import io
import uuid
import zipfile
from datetime import datetime, date, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func

from app.database import get_db
from app.models import (
    ServiceOrder, Certificate, CertificateChemical, Branch, Client, 
    Chemical, User, UserRole
)
from app.schemas import (
    ServiceOrderCreate, ServiceOrderResponse, DashboardExpirationsResponse,
    ClientExpirationsGroup, ExpirationDetail, DashboardSummaryStats,
    UserCreate, UserUpdate, UserResponse,
    ClientCreate, ClientUpdate, ClientResponse,
    BranchCreate, BranchUpdate, BranchResponse,
    ChemicalCreate, ChemicalUpdate, ChemicalResponse,
    DuplicateServiceOrderRequest, MonthlyBatchGenerationRequest,
    MonthlyBatchGenerationResponse, SendEmailRequest, SendEmailResponse
)
from app.services.data_import import HistoricalDataImporter
from app.services.pdf_service import OfficialCertificatePDFGenerator
from app.services.email_service import OfficialCertificateEmailService
from app.services.duplication_service import ServiceDuplicationService

router = APIRouter(prefix="/api/v1", tags=["FUMIFLOSA Core"])


# ============================================================================
# 0. DASHBOARD SUMMARY STATS
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
# 1. USUARIOS Y ROLES (CRUD + STPS DC-3)
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
# 2. CLIENTES MATRIZ (CRUD)
# ============================================================================
@router.get("/clients", response_model=List[ClientResponse])
def get_clients(db: Session = Depends(get_db)):
    return db.query(Client).filter(Client.is_deleted == False).order_by(Client.legal_name).all()


@router.post("/clients", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(payload: ClientCreate, db: Session = Depends(get_db)):
    existing = db.query(Client).filter(Client.rfc == payload.rfc, Client.is_deleted == False).first()
    if existing:
        raise HTTPException(status_code=400, detail="El RFC ya se encuentra registrado.")

    client = Client(
        legal_name=payload.legal_name,
        rfc=payload.rfc,
        master_contract_number=payload.master_contract_number,
        tax_regime=payload.tax_regime
    )
    db.add(client)
    db.commit()
    db.refresh(client)
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
# 3. SUCURSALES (CRUD)
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
# 4. CATÁLOGO DE QUÍMICOS (CRUD)
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
# 5. ÓRDENES DE SERVICIO Y CERTIFICADOS (Creación Atómica y Listado)
# ============================================================================
@router.get("/services", response_model=List[ServiceOrderResponse])
def get_service_orders(
    branch_id: Optional[uuid.UUID] = None, 
    limit: int = 50, 
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
        certificate = Certificate(
            service_order_id=service_order.id,
            certificate_folio=cert_folio,
            issue_date=start_date,
            validity_start_date=start_date,
            validity_end_date=start_date + timedelta(days=30),
            sanitary_license_number=payload.sanitary_license_number,
            sanitary_responsible_name=payload.sanitary_responsible_name,
            sanitary_responsible_id=payload.sanitary_responsible_id
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
# 5.1 DUPLICACIÓN DE ORDEN / CERTIFICADO PARA EL MES
# ============================================================================
@router.post("/services/{service_id}/duplicate", response_model=ServiceOrderResponse, status_code=status.HTTP_201_CREATED)
def duplicate_service_order(
    service_id: uuid.UUID,
    payload: DuplicateServiceOrderRequest = DuplicateServiceOrderRequest(),
    db: Session = Depends(get_db)
):
    """
    Duplica una orden de servicio existente con su certificado NOM-256 y químicos dosificados,
    actualizando la fecha de aplicación y calculando automáticamente la nueva vigencia a 30 días.
    Opcionalmente envía el nuevo certificado por correo electrónico.
    """
    duplication_service = ServiceDuplicationService(db)
    try:
        new_order = duplication_service.duplicate_single_service(
            source_service_id=service_id,
            new_service_start_date=payload.new_service_start_date,
            new_service_end_date=payload.new_service_end_date,
            technician_id=payload.technician_id,
            folio_prefix=payload.folio_prefix,
            observations=payload.observations,
            send_email=payload.send_email,
            recipient_email=payload.recipient_email,
            additional_notes=payload.additional_notes
        )
        return new_order
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al duplicar el servicio: {str(e)}")


# ============================================================================
# 5.2 ENVÍO DE CERTIFICADO POR CORREO ELECTRÓNICO
# ============================================================================
@router.post("/services/{service_id}/send-email", response_model=SendEmailResponse)
def send_certificate_email(
    service_id: uuid.UUID,
    payload: SendEmailRequest = SendEmailRequest(),
    db: Session = Depends(get_db)
):
    """
    Genera el PDF del Certificado Oficial NOM-256 y lo envía por correo electrónico
    al contacto responsable de la sucursal o a un correo destinatario personalizado.
    """
    order = db.query(ServiceOrder).options(
        joinedload(ServiceOrder.branch).joinedload(Branch.client),
        joinedload(ServiceOrder.technician),
        joinedload(ServiceOrder.certificate).joinedload(Certificate.applied_chemicals).joinedload(CertificateChemical.chemical)
    ).filter(ServiceOrder.id == service_id, ServiceOrder.is_deleted == False).first()

    if not order or not order.certificate:
        raise HTTPException(status_code=404, detail="Orden o Certificado no encontrado.")

    recipient = payload.recipient_email
    if not recipient and order.branch and order.branch.responsible_contact_email:
        recipient = order.branch.responsible_contact_email

    if not recipient:
        raise HTTPException(
            status_code=400, 
            detail="No se encontró un correo destinatario en la sucursal. Por favor ingrese un correo válido."
        )

    try:
        pdf_bytes = OfficialCertificatePDFGenerator.generate(order, order.certificate)
        result = OfficialCertificateEmailService.send_certificate_email(
            order=order,
            cert=order.certificate,
            pdf_bytes=pdf_bytes,
            recipient_email=str(recipient),
            additional_notes=payload.additional_notes
        )
        return SendEmailResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el envío de correo: {str(e)}")


# ============================================================================
# 5.3 GENERACIÓN MASIVA MENSUAL POR CLIENTE MATRIZ (CONTRATOS MULTI-SUCURSAL)
# ============================================================================
@router.post("/clients/{client_id}/generate-monthly-batch", response_model=MonthlyBatchGenerationResponse, status_code=status.HTTP_201_CREATED)
def generate_client_monthly_batch(
    client_id: uuid.UUID,
    payload: MonthlyBatchGenerationRequest,
    db: Session = Depends(get_db)
):
    """
    Genera en lote mensual órdenes de servicio y certificados NOM-256 para
    todas o una selección de sucursales de un Cliente Matriz (ej. IMSS con 100+ unidades).
    Clona la configuración previa de cada sucursal o aplica una plantilla base.
    """
    duplication_service = ServiceDuplicationService(db)
    try:
        result = duplication_service.generate_monthly_batch_for_client(
            client_id=client_id,
            target_date=payload.target_date,
            service_start_time=payload.service_start_time or "09:00:00",
            service_duration_hours=payload.service_duration_hours,
            technician_id=payload.technician_id,
            branch_ids=payload.branch_ids,
            mode=payload.mode,
            folio_prefix=payload.folio_prefix,
            observations=payload.observations,
            send_emails=payload.send_emails,
            template_pest_crawling=payload.template_pest_crawling,
            template_pest_rodents=payload.template_pest_rodents,
            template_pest_flying=payload.template_pest_flying,
            template_proc_aspersion=payload.template_proc_aspersion,
            template_proc_baits=payload.template_proc_baits,
            template_proc_gels=payload.template_proc_gels,
            template_chemical_id=payload.template_chemical_id,
            template_dose=payload.template_dose,
            template_zones=payload.template_zones,
            template_method=payload.template_method
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar lote mensual: {str(e)}")


@router.post("/batch/generate-monthly", response_model=MonthlyBatchGenerationResponse, status_code=status.HTTP_201_CREATED)
def generate_monthly_batch_generic(
    payload: MonthlyBatchGenerationRequest,
    db: Session = Depends(get_db)
):
    """Ruta directa para invocación de generación masiva mensual."""
    return generate_client_monthly_batch(client_id=payload.client_id, payload=payload, db=db)


# ============================================================================
# 6. GENERACIÓN Y DESCARGA DE PDF OFICIAL (NOM-256 / SINTOX)
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

    pdf_bytes = OfficialCertificatePDFGenerator.generate(order, order.certificate)
    
    filename = f"Certificado_{order.certificate.certificate_folio}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )


# ============================================================================
# 7. DASHBOARD B2B: MONITOREO DE EXPIRACIONES (7, 15, 30 DÍAS)
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
                rfc=client.rfc
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
# 8. PORTAL CLIENTE MATRIZ: HISTORIAL Y DESCARGA MASIVA ZIP
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

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for order in orders:
            if order.certificate:
                pdf_data = OfficialCertificatePDFGenerator.generate(order, order.certificate)
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
# 9. IMPORTACIÓN HISTÓRICA CSV CON PANDAS
# ============================================================================
@router.post("/import/historical-csv")
async def import_historical_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Procesa un archivo CSV histórico y migra órdenes/certificados en lote."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un CSV válido.")
    
    contents = await file.read()
    importer = HistoricalDataImporter(db)
    result = importer.process_csv(contents)
    return {"status": "success", "result": result}
