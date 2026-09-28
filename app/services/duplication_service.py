import uuid
import logging
from datetime import datetime, date, timedelta, time, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, desc

from app.models import (
    ServiceOrder, Certificate, CertificateChemical, Branch, Client, 
    Chemical, User, UserRole, AreaType
)
from app.services.pdf_service import OfficialCertificatePDFGenerator
from app.services.email_service import OfficialCertificateEmailService

logger = logging.getLogger(__name__)


class ServiceDuplicationService:
    def __init__(self, db: Session):
        self.db = db

    def _get_next_sequence(self, prefix: str) -> int:
        """Obtiene el conteo consecutivo para generar folios únicos secuenciales."""
        count = self.db.execute(
            select(func.count(ServiceOrder.id)).where(ServiceOrder.folio.like(f"{prefix}-%"))
        ).scalar() or 0
        return count + 1

    def duplicate_single_service(
        self,
        source_service_id: uuid.UUID,
        new_service_start_date: Optional[datetime] = None,
        new_service_end_date: Optional[datetime] = None,
        technician_id: Optional[uuid.UUID] = None,
        folio_prefix: Optional[str] = "SRV",
        observations: Optional[str] = None,
        send_email: bool = False,
        recipient_email: Optional[str] = None,
        additional_notes: Optional[str] = None
    ) -> ServiceOrder:
        """
        Duplica una orden de servicio existente junto con su certificado NOM-256
        y todos los químicos aplicados, actualizando fechas y generando nuevos folios únicos.
        """
        # 1. Cargar la orden origen con todas sus relaciones
        source_order = self.db.query(ServiceOrder).options(
            joinedload(ServiceOrder.branch).joinedload(Branch.client),
            joinedload(ServiceOrder.technician),
            joinedload(ServiceOrder.certificate).joinedload(Certificate.applied_chemicals).joinedload(CertificateChemical.chemical)
        ).filter(ServiceOrder.id == source_service_id, ServiceOrder.is_deleted == False).first()

        if not source_order:
            raise ValueError(f"Orden de servicio de origen {source_service_id} no encontrada.")

        if not source_order.certificate:
            raise ValueError("La orden de servicio origen no cuenta con un certificado emitido para duplicar.")

        # 2. Determinar fechas
        if not new_service_start_date:
            new_service_start_date = datetime.now(timezone.utc)
        elif new_service_start_date.tzinfo is None:
            new_service_start_date = new_service_start_date.replace(tzinfo=timezone.utc)

        if not new_service_end_date:
            duration = source_order.service_end_date - source_order.service_start_date
            if duration.total_seconds() <= 0:
                duration = timedelta(hours=2)
            new_service_end_date = new_service_start_date + duration
        elif new_service_end_date.tzinfo is None:
            new_service_end_date = new_service_end_date.replace(tzinfo=timezone.utc)

        # 3. Determinar técnico
        target_technician_id = technician_id or source_order.technician_id
        technician = self.db.query(User).filter(User.id == target_technician_id, User.is_active == True).first()
        if not technician:
            raise ValueError(f"Técnico asignado ID {target_technician_id} no válido o inactivo.")

        # 4. Generar folios
        prefix = folio_prefix or "SRV"
        next_num = self._get_next_sequence(prefix)
        new_order_folio = f"{prefix}-ORD-{next_num:06d}"
        new_cert_folio = f"{prefix}-CERT-{next_num:06d}"

        # 5. Crear nueva Orden de Servicio
        new_order = ServiceOrder(
            folio=new_order_folio,
            branch_id=source_order.branch_id,
            technician_id=technician.id,
            service_start_date=new_service_start_date,
            service_end_date=new_service_end_date,
            pest_crawling_insects=source_order.pest_crawling_insects,
            pest_rodents=source_order.pest_rodents,
            pest_flying_insects=source_order.pest_flying_insects,
            pest_others=source_order.pest_others,
            proc_aspersion=source_order.proc_aspersion,
            proc_baits=source_order.proc_baits,
            proc_traps=source_order.proc_traps,
            proc_gels=source_order.proc_gels,
            proc_ulv_fogging=source_order.proc_ulv_fogging,
            proc_thermofogging=source_order.proc_thermofogging,
            results_summary=source_order.results_summary,
            observations=observations if observations is not None else source_order.observations,
            client_signature_data=None  # La nueva orden queda lista para firma en campo si aplica
        )
        self.db.add(new_order)
        self.db.flush()

        # 6. Crear nuevo Certificado con vigencia a 30 días
        issue_d = new_service_start_date.date()
        source_cert = source_order.certificate
        new_cert = Certificate(
            service_order_id=new_order.id,
            certificate_folio=new_cert_folio,
            issue_date=issue_d,
            validity_start_date=issue_d,
            validity_end_date=issue_d + timedelta(days=30),
            sanitary_license_number=source_cert.sanitary_license_number,
            sanitary_responsible_name=source_cert.sanitary_responsible_name,
            sanitary_responsible_id=source_cert.sanitary_responsible_id
        )
        self.db.add(new_cert)
        self.db.flush()

        # 7. Duplicar Químicos Aplicados
        for chem_app in source_cert.applied_chemicals:
            new_chem_app = CertificateChemical(
                certificate_id=new_cert.id,
                chemical_id=chem_app.chemical_id,
                dose_applied=chem_app.dose_applied,
                area_type=chem_app.area_type,
                treated_zones_description=chem_app.treated_zones_description,
                application_method=chem_app.application_method
            )
            self.db.add(new_chem_app)

        self.db.commit()

        # Recargar con todas las relaciones
        reloaded_order = self.db.query(ServiceOrder).options(
            joinedload(ServiceOrder.branch).joinedload(Branch.client),
            joinedload(ServiceOrder.technician),
            joinedload(ServiceOrder.certificate).joinedload(Certificate.applied_chemicals).joinedload(CertificateChemical.chemical)
        ).filter(ServiceOrder.id == new_order.id).first()

        # 8. Envío de Correo si se solicitó
        if send_email and reloaded_order and reloaded_order.certificate:
            target_email = recipient_email or (reloaded_order.branch.responsible_contact_email if reloaded_order.branch else None)
            if target_email:
                try:
                    pdf_bytes = OfficialCertificatePDFGenerator.generate(reloaded_order, reloaded_order.certificate)
                    OfficialCertificateEmailService.send_certificate_email(
                        order=reloaded_order,
                        cert=reloaded_order.certificate,
                        pdf_bytes=pdf_bytes,
                        recipient_email=target_email,
                        additional_notes=additional_notes or "Servicio programado mensual renovado automáticamente."
                    )
                except Exception as ex:
                    logger.warning(f"No se pudo enviar correo automático al duplicar servicio: {str(ex)}")

        return reloaded_order

    def generate_monthly_batch_for_client(
        self,
        client_id: uuid.UUID,
        target_date: Optional[date] = None,
        service_start_time: str = "09:00:00",
        service_duration_hours: int = 2,
        technician_id: Optional[uuid.UUID] = None,
        branch_ids: Optional[List[uuid.UUID]] = None,
        mode: str = "clone_last_service",  # "clone_last_service" | "use_template"
        folio_prefix: Optional[str] = "MENS",
        observations: Optional[str] = None,
        send_emails: bool = False,
        # Parámetros opcionales para modo plantilla
        template_pest_crawling: bool = True,
        template_pest_rodents: bool = True,
        template_pest_flying: bool = False,
        template_proc_aspersion: bool = True,
        template_proc_baits: bool = False,
        template_proc_gels: bool = False,
        template_chemical_id: Optional[uuid.UUID] = None,
        template_dose: str = "10 ml / Litro",
        template_zones: str = "Áreas interiores, sanitarios y perímetro común",
        template_method: str = "Aspersión Manual"
    ) -> Dict[str, Any]:
        """
        Genera en lote mensual órdenes de servicio y certificados NOM-256 para
        todas o una selección de sucursales de un Cliente Matriz.
        """
        client = self.db.query(Client).filter(Client.id == client_id, Client.is_deleted == False).first()
        if not client:
            raise ValueError(f"Cliente Matriz ID {client_id} no encontrado.")

        # Obtener sucursales
        query_branches = self.db.query(Branch).filter(
            Branch.client_id == client_id,
            Branch.is_deleted == False
        )
        if branch_ids and len(branch_ids) > 0:
            query_branches = query_branches.filter(Branch.id.in_(branch_ids))

        branches = query_branches.order_by(Branch.name).all()
        if not branches:
            raise ValueError("No se encontraron sucursales activas para este cliente.")

        # Técnico por defecto o seleccionado
        default_tech = None
        if technician_id:
            default_tech = self.db.query(User).filter(User.id == technician_id, User.is_active == True).first()
            if not default_tech:
                raise ValueError(f"Técnico ID {technician_id} no encontrado o inactivo.")
        else:
            default_tech = self.db.query(User).filter(
                User.role == UserRole.TECNICO_CAMPO, 
                User.is_active == True
            ).first()
            if not default_tech:
                default_tech = self.db.query(User).filter(User.is_active == True).first()

        # Químico por defecto si se requiere
        default_chem = None
        if template_chemical_id:
            default_chem = self.db.query(Chemical).filter(Chemical.id == template_chemical_id).first()
        if not default_chem:
            default_chem = self.db.query(Chemical).filter(Chemical.is_deleted == False).first()

        # Parsear fechas de aplicación
        if not target_date:
            target_date = date.today()

        try:
            parsed_time = datetime.strptime(service_start_time, "%H:%M:%S").time()
        except Exception:
            parsed_time = time(9, 0, 0)

        service_dt_start = datetime.combine(target_date, parsed_time).replace(tzinfo=timezone.utc)
        service_dt_end = service_dt_start + timedelta(hours=max(1, service_duration_hours))

        prefix = folio_prefix or "MENS"
        seq_num = self._get_next_sequence(prefix)

        created_orders_summary = []
        emails_sent_count = 0
        orders_to_email = []

        try:
            for branch in branches:
                order_folio = f"{prefix}-ORD-{seq_num:06d}"
                cert_folio = f"{prefix}-CERT-{seq_num:06d}"
                seq_num += 1

                # Buscar último servicio de la sucursal si el modo es "clone_last_service"
                last_order = None
                if mode == "clone_last_service":
                    last_order = self.db.query(ServiceOrder).options(
                        joinedload(ServiceOrder.certificate).joinedload(Certificate.applied_chemicals)
                    ).filter(
                        ServiceOrder.branch_id == branch.id,
                        ServiceOrder.is_deleted == False
                    ).order_by(desc(ServiceOrder.service_start_date)).first()

                # Definir valores de la orden
                tech_for_order = default_tech
                if not technician_id and last_order and last_order.technician_id:
                    branch_last_tech = self.db.query(User).filter(User.id == last_order.technician_id, User.is_active == True).first()
                    if branch_last_tech:
                        tech_for_order = branch_last_tech

                pest_crawling = last_order.pest_crawling_insects if last_order else template_pest_crawling
                pest_rodents = last_order.pest_rodents if last_order else template_pest_rodents
                pest_flying = last_order.pest_flying_insects if last_order else template_pest_flying
                pest_others = last_order.pest_others if last_order else None

                proc_asp = last_order.proc_aspersion if last_order else template_proc_aspersion
                proc_baits = last_order.proc_baits if last_order else template_proc_baits
                proc_traps = last_order.proc_traps if last_order else False
                proc_gels = last_order.proc_gels if last_order else template_proc_gels
                proc_ulv = last_order.proc_ulv_fogging if last_order else False
                proc_thermo = last_order.proc_thermofogging if last_order else False

                order_obs = observations or (last_order.observations if last_order else "Servicio mensual programado de control integral de plagas.")
                results_sum = last_order.results_summary if last_order else "Servicio preventivo mensual ejecutado conforme a la NOM-256-SSA1-2012."

                new_order = ServiceOrder(
                    folio=order_folio,
                    branch_id=branch.id,
                    technician_id=tech_for_order.id,
                    service_start_date=service_dt_start,
                    service_end_date=service_dt_end,
                    pest_crawling_insects=pest_crawling,
                    pest_rodents=pest_rodents,
                    pest_flying_insects=pest_flying,
                    pest_others=pest_others,
                    proc_aspersion=proc_asp,
                    proc_baits=proc_baits,
                    proc_traps=proc_traps,
                    proc_gels=proc_gels,
                    proc_ulv_fogging=proc_ulv,
                    proc_thermofogging=proc_thermo,
                    results_summary=results_sum,
                    observations=order_obs
                )
                self.db.add(new_order)
                self.db.flush()

                # Certificado NOM-256
                lic_sanitaria = "2023-15A-099"
                resp_nombre = "Biól. Responsable Sanitario FUMIFLOSA"
                resp_cedula = "CED-BIO-992811"

                if last_order and last_order.certificate:
                    lic_sanitaria = last_order.certificate.sanitary_license_number
                    resp_nombre = last_order.certificate.sanitary_responsible_name
                    resp_cedula = last_order.certificate.sanitary_responsible_id

                new_cert = Certificate(
                    service_order_id=new_order.id,
                    certificate_folio=cert_folio,
                    issue_date=target_date,
                    validity_start_date=target_date,
                    validity_end_date=target_date + timedelta(days=30),
                    sanitary_license_number=lic_sanitaria,
                    sanitary_responsible_name=resp_nombre,
                    sanitary_responsible_id=resp_cedula
                )
                self.db.add(new_cert)
                self.db.flush()

                # Químicos
                if last_order and last_order.certificate and last_order.certificate.applied_chemicals:
                    for app_ch in last_order.certificate.applied_chemicals:
                        new_app = CertificateChemical(
                            certificate_id=new_cert.id,
                            chemical_id=app_ch.chemical_id,
                            dose_applied=app_ch.dose_applied,
                            area_type=app_ch.area_type,
                            treated_zones_description=app_ch.treated_zones_description,
                            application_method=app_ch.application_method
                        )
                        self.db.add(new_app)
                elif default_chem:
                    new_app = CertificateChemical(
                        certificate_id=new_cert.id,
                        chemical_id=default_chem.id,
                        dose_applied=template_dose,
                        area_type=AreaType.INTERIOR,
                        treated_zones_description=template_zones,
                        application_method=template_method
                    )
                    self.db.add(new_app)

                created_orders_summary.append({
                    "service_order_id": str(new_order.id),
                    "order_folio": order_folio,
                    "certificate_id": str(new_cert.id),
                    "certificate_folio": cert_folio,
                    "branch_id": str(branch.id),
                    "branch_name": branch.name,
                    "unit_code": branch.unit_code,
                    "technician_name": tech_for_order.full_name,
                    "validity_start_date": str(target_date),
                    "validity_end_date": str(target_date + timedelta(days=30))
                })

                if send_emails and branch.responsible_contact_email:
                    orders_to_email.append((new_order.id, branch.responsible_contact_email))

            self.db.commit()

            # Enviar correos en segundo plano / lote después del commit
            if send_emails and orders_to_email:
                for ord_id, rec_email in orders_to_email:
                    try:
                        ord_obj = self.db.query(ServiceOrder).options(
                            joinedload(ServiceOrder.branch).joinedload(Branch.client),
                            joinedload(ServiceOrder.technician),
                            joinedload(ServiceOrder.certificate).joinedload(Certificate.applied_chemicals).joinedload(CertificateChemical.chemical)
                        ).filter(ServiceOrder.id == ord_id).first()

                        if ord_obj and ord_obj.certificate:
                            pdf_data = OfficialCertificatePDFGenerator.generate(ord_obj, ord_obj.certificate)
                            email_res = OfficialCertificateEmailService.send_certificate_email(
                                order=ord_obj,
                                cert=ord_obj.certificate,
                                pdf_bytes=pdf_data,
                                recipient_email=rec_email,
                                additional_notes=f"Renovación de servicio mensual programado para {target_date.strftime('%B %Y')}."
                            )
                            if email_res.get("success"):
                                emails_sent_count += 1
                    except Exception as email_err:
                        logger.warning(f"Error al enviar correo en lote para orden {ord_id}: {str(email_err)}")

            return {
                "client_id": client.id,
                "client_name": client.legal_name,
                "total_branches_processed": len(branches),
                "orders_created_count": len(created_orders_summary),
                "certificates_created_count": len(created_orders_summary),
                "emails_sent_count": emails_sent_count,
                "created_orders": created_orders_summary
            }

        except Exception as e:
            self.db.rollback()
            raise RuntimeError(f"Error en la generación masiva mensual de órdenes: {str(e)}")
