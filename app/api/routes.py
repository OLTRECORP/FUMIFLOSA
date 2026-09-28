import io
import uuid
import zipfile
from datetime import datetime, date, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func

from app.database import get_db
from app.models import (
    ServiceOrder, Certificate, CertificateChemical, Branch, Client, 
    Chemical, User
)
from app.schemas import (
    ServiceOrderCreate, ServiceOrderResponse, DashboardExpirationsResponse,
    ClientExpirationsGroup, ExpirationDetail
)
from app.services.data_import import HistoricalDataImporter
from app.services.pdf_service import OfficialCertificatePDFGenerator

router = APIRouter(prefix="/api/v1", tags=["FUMIFLOSA Core"])


# ============================================================================
# 1. CREACIÓN ATÓMICA DE ORDEN + CERTIFICADO
# ============================================================================
@router.post("/services", response_model=ServiceOrderResponse, status_code=status.HTTP_201_CREATED)
def create_service_order_with_certificate(
    payload: ServiceOrderCreate,
    db: Session = Depends(get_db)
):
    """
    Crea atómicamente la Orden de Servicio y el Certificado NOM-256 enlazado
    junto con sus químicos dosificados bajo una sola transacción segura.
    """
    # 1. Validar existencia de sucursal y técnico
    branch = db.query(Branch).filter(Branch.id == payload.branch_id, Branch.is_deleted == False).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada.")

    technician = db.query(User).filter(User.id == payload.technician_id, User.is_active == True).first()
    if not technician:
        raise HTTPException(status_code=404, detail="Técnico no encontrado o inactivo.")

    # 2. Generar Folios Consecutivos
    prefix = payload.folio_prefix or "SRV"
    count = db.execute(
        select(func.count(ServiceOrder.id)).where(ServiceOrder.folio.like(f"{prefix}-%"))
    ).scalar() or 0
    next_num = count + 1
    
    order_folio = f"{prefix}-ORD-{next_num:06d}"
    cert_folio = f"{prefix}-CERT-{next_num:06d}"

    try:
        # 3. Instanciar Orden de Servicio
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

        # 4. Instanciar Certificado Oficial (Vigencia 30 días calculada)
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

        # 5. Asociar Químicos Aplicados
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
# 2. GENERACIÓN Y DESCARGA DE PDF OFICIAL
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
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ============================================================================
# 3. DASHBOARD B2B: MONITOREO DE EXPIRACIONES (7, 15, 30 DÍAS)
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
# 4. PORTAL CLIENTE MATRIZ: HISTORIAL Y DESCARGA MASIVA ZIP
# ============================================================================
@router.get("/portal/matrix/{client_id}/services", response_model=List[ServiceOrderResponse])
def get_matrix_services_history(client_id: uuid.UUID, db: Session = Depends(get_db)):
    """Devuelve el historial consolidado de todas las sucursales de la matriz."""
    orders = db.query(ServiceOrder).join(Branch).filter(
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
# 5. IMPORTACIÓN HISTÓRICA CSV
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
