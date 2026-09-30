import io
import json
import uuid
import zipfile
import urllib.request
from datetime import datetime, date, timezone
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import extract, and_, or_

from app.models import (
    CompanyConfig, User, Client, Branch, Chemical, 
    ServiceOrder, Certificate, CertificateChemical,
    UserRole, BranchClassification, AreaType
)
from app.services.pdf_service import OfficialCertificatePDFGenerator


class SystemBackupRestoreService:
    """
    Servicio integral de Respaldo, Restauración Atómica y Descarga Masiva
    de Certificados Oficiales NOM-256 para FUMIFLOSA.
    """

    @staticmethod
    def export_full_backup(db: Session) -> Dict[str, Any]:
        """Exporta el estado completo de la base de datos a un diccionario serializable en JSON."""
        
        # 1. Configuración de Empresa
        company = db.query(CompanyConfig).first()
        company_data = None
        if company:
            company_data = {
                "id": str(company.id),
                "company_name": company.company_name,
                "trade_name": company.trade_name,
                "rfc": company.rfc,
                "tax_regime": company.tax_regime,
                "fiscal_address": company.fiscal_address,
                "phone": company.phone,
                "email": company.email,
                "website": company.website,
                "sanitary_license_number": company.sanitary_license_number,
                "sanitary_responsible_name": company.sanitary_responsible_name,
                "sanitary_responsible_id": company.sanitary_responsible_id,
                "stps_registration_number": company.stps_registration_number,
                "logo_url": company.logo_url,
                "sintox_emergency_phones": company.sintox_emergency_phones,
                "default_reentry_hours": company.default_reentry_hours,
                "default_validity_days": company.default_validity_days,
                "terms_and_notes": company.terms_and_notes
            }

        # 2. Usuarios
        users = db.query(User).all()
        users_data = []
        for u in users:
            users_data.append({
                "id": str(u.id),
                "username": u.username,
                "email": u.email,
                "hashed_password": u.hashed_password,
                "full_name": u.full_name,
                "role": u.role.value if hasattr(u.role, 'value') else str(u.role),
                "is_active": u.is_active,
                "stps_dc3_file_url": u.stps_dc3_file_url,
                "stps_registration_number": u.stps_registration_number,
                "client_id": str(u.client_id) if u.client_id else None,
                "branch_id": str(u.branch_id) if u.branch_id else None,
                "is_deleted": u.is_deleted
            })

        # 3. Químicos
        chemicals = db.query(Chemical).all()
        chemicals_data = []
        for c in chemicals:
            chemicals_data.append({
                "id": str(c.id),
                "commercial_name": c.commercial_name,
                "active_ingredient": c.active_ingredient,
                "cicoplafest_number": c.cicoplafest_number,
                "authorized_dose_per_liter": c.authorized_dose_per_liter,
                "safety_interval_hours": c.safety_interval_hours,
                "compatible_methods": c.compatible_methods,
                "toxicological_category": c.toxicological_category,
                "is_deleted": c.is_deleted
            })

        # 4. Clientes Matriz
        clients = db.query(Client).all()
        clients_data = []
        for cl in clients:
            clients_data.append({
                "id": str(cl.id),
                "legal_name": cl.legal_name,
                "rfc": cl.rfc,
                "master_contract_number": cl.master_contract_number,
                "tax_regime": cl.tax_regime,
                "portal_slug": cl.portal_slug,
                "portal_password": cl.portal_password,
                "portal_is_enabled": cl.portal_is_enabled,
                "is_deleted": cl.is_deleted
            })

        # 5. Sucursales
        branches = db.query(Branch).all()
        branches_data = []
        for b in branches:
            branches_data.append({
                "id": str(b.id),
                "client_id": str(b.client_id),
                "name": b.name,
                "unit_code": b.unit_code,
                "address": b.address,
                "phone": b.phone,
                "classification": b.classification.value if hasattr(b.classification, 'value') else str(b.classification),
                "responsible_contact_name": b.responsible_contact_name,
                "responsible_contact_email": b.responsible_contact_email,
                "is_deleted": b.is_deleted
            })

        # 6. Órdenes de Servicio
        orders = db.query(ServiceOrder).all()
        orders_data = []
        for o in orders:
            orders_data.append({
                "id": str(o.id),
                "folio": o.folio,
                "branch_id": str(o.branch_id),
                "technician_id": str(o.technician_id),
                "service_start_date": o.service_start_date.isoformat() if o.service_start_date else None,
                "service_end_date": o.service_end_date.isoformat() if o.service_end_date else None,
                "pest_crawling_insects": o.pest_crawling_insects,
                "pest_rodents": o.pest_rodents,
                "pest_flying_insects": o.pest_flying_insects,
                "pest_others": o.pest_others,
                "proc_aspersion": o.proc_aspersion,
                "proc_baits": o.proc_baits,
                "proc_traps": o.proc_traps,
                "proc_gels": o.proc_gels,
                "proc_ulv_fogging": o.proc_ulv_fogging,
                "proc_thermofogging": o.proc_thermofogging,
                "results_summary": o.results_summary,
                "observations": o.observations,
                "client_signature_data": o.client_signature_data,
                "is_deleted": o.is_deleted
            })

        # 7. Certificados
        certificates = db.query(Certificate).all()
        certificates_data = []
        for cert in certificates:
            certificates_data.append({
                "id": str(cert.id),
                "service_order_id": str(cert.service_order_id),
                "certificate_folio": cert.certificate_folio,
                "issue_date": cert.issue_date.isoformat() if cert.issue_date else None,
                "validity_start_date": cert.validity_start_date.isoformat() if cert.validity_start_date else None,
                "validity_end_date": cert.validity_end_date.isoformat() if cert.validity_end_date else None,
                "sanitary_license_number": cert.sanitary_license_number,
                "sanitary_responsible_name": cert.sanitary_responsible_name,
                "sanitary_responsible_id": cert.sanitary_responsible_id,
                "is_deleted": cert.is_deleted
            })

        # 8. Químicos Aplicados (Pivote)
        applied_chems = db.query(CertificateChemical).all()
        applied_data = []
        for ac in applied_chems:
            applied_data.append({
                "id": str(ac.id),
                "certificate_id": str(ac.certificate_id),
                "chemical_id": str(ac.chemical_id),
                "dose_applied": ac.dose_applied,
                "area_type": ac.area_type.value if hasattr(ac.area_type, 'value') else str(ac.area_type),
                "treated_zones_description": ac.treated_zones_description,
                "application_method": ac.application_method
            })

        backup_payload = {
            "version": "1.0",
            "system": "FUMIFLOSA SaaS Control de Plagas NOM-256",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "counts": {
                "users": len(users_data),
                "chemicals": len(chemicals_data),
                "clients": len(clients_data),
                "branches": len(branches_data),
                "orders": len(orders_data),
                "certificates": len(certificates_data),
                "applied_chemicals": len(applied_data)
            },
            "data": {
                "company_config": company_data,
                "users": users_data,
                "chemicals": chemicals_data,
                "clients": clients_data,
                "branches": branches_data,
                "service_orders": orders_data,
                "certificates": certificates_data,
                "certificate_chemicals": applied_data
            }
        }
        return backup_payload

    @staticmethod
    def restore_full_backup(db: Session, backup_dict: Dict[str, Any], mode: str = "merge") -> Dict[str, Any]:
        """
        Restaura atómicamente la base de datos a partir de un diccionario de respaldo.
        Soporta modos:
          - 'merge': Inserta registros omitiendo duplicados o actualizando datos faltantes.
          - 'overwrite': Limpia tablas existentes y restaura el estado exacto.
        """
        data = backup_dict.get("data", backup_dict)
        summary = {
            "status": "success",
            "mode": mode,
            "restored_at": datetime.now(timezone.utc),
            "company_config_restored": False,
            "users_restored": 0,
            "chemicals_restored": 0,
            "clients_restored": 0,
            "branches_restored": 0,
            "orders_restored": 0,
            "certificates_restored": 0,
            "certificate_chemicals_restored": 0,
            "message": ""
        }

        try:
            # Si es overwrite, limpiar en orden inverso de dependencias
            if mode == "overwrite":
                db.query(CertificateChemical).delete()
                db.query(Certificate).delete()
                db.query(ServiceOrder).delete()
                db.query(Branch).delete()
                db.query(Client).delete()
                db.query(Chemical).delete()
                # Omitir borrar usuarios superadmin para evitar deslogueo
                db.query(User).filter(User.username != "FOSM630329EA5").delete()
                db.flush()

            # 1. Company Config
            company_info = data.get("company_config")
            if company_info:
                cfg = db.query(CompanyConfig).first()
                if not cfg:
                    cfg = CompanyConfig(id=uuid.UUID(company_info["id"]) if "id" in company_info else uuid.uuid4())
                    db.add(cfg)
                
                for k, v in company_info.items():
                    if k != "id" and hasattr(cfg, k) and v is not None:
                        setattr(cfg, k, v)
                summary["company_config_restored"] = True
                db.flush()

            # 2. Users
            for u in data.get("users", []):
                uid = uuid.UUID(u["id"]) if u.get("id") else uuid.uuid4()
                existing_user = db.query(User).filter(
                    or_(User.id == uid, User.email == u["email"], User.username == u.get("username"))
                ).first()

                role_val = u.get("role", "TecnicoCampo")
                try:
                    role_enum = UserRole(role_val)
                except ValueError:
                    role_enum = UserRole.TECNICO_CAMPO

                if not existing_user:
                    new_user = User(
                        id=uid,
                        username=u.get("username"),
                        email=u["email"],
                        hashed_password=u.get("hashed_password", "hash_Fumiflosa2026*"),
                        full_name=u["full_name"],
                        role=role_enum,
                        is_active=u.get("is_active", True),
                        stps_dc3_file_url=u.get("stps_dc3_file_url"),
                        stps_registration_number=u.get("stps_registration_number"),
                        client_id=uuid.UUID(u["client_id"]) if u.get("client_id") else None,
                        branch_id=uuid.UUID(u["branch_id"]) if u.get("branch_id") else None,
                        is_deleted=u.get("is_deleted", False)
                    )
                    db.add(new_user)
                    summary["users_restored"] += 1
                else:
                    if mode == "overwrite":
                        existing_user.full_name = u["full_name"]
                        existing_user.role = role_enum
                        existing_user.is_active = u.get("is_active", True)
                    summary["users_restored"] += 1
            db.flush()

            # 3. Chemicals
            for c in data.get("chemicals", []):
                cid = uuid.UUID(c["id"]) if c.get("id") else uuid.uuid4()
                existing_chem = db.query(Chemical).filter(
                    or_(Chemical.id == cid, Chemical.cicoplafest_number == c["cicoplafest_number"])
                ).first()

                if not existing_chem:
                    new_chem = Chemical(
                        id=cid,
                        commercial_name=c["commercial_name"],
                        active_ingredient=c["active_ingredient"],
                        cicoplafest_number=c["cicoplafest_number"],
                        authorized_dose_per_liter=c["authorized_dose_per_liter"],
                        safety_interval_hours=c.get("safety_interval_hours", 2),
                        compatible_methods=c.get("compatible_methods", "Aspersión Manual"),
                        toxicological_category=c.get("toxicological_category", "Banda Verde"),
                        is_deleted=c.get("is_deleted", False)
                    )
                    db.add(new_chem)
                    summary["chemicals_restored"] += 1
                else:
                    summary["chemicals_restored"] += 1
            db.flush()

            # 4. Clients
            for cl in data.get("clients", []):
                clid = uuid.UUID(cl["id"]) if cl.get("id") else uuid.uuid4()
                existing_client = db.query(Client).filter(
                    or_(Client.id == clid, Client.rfc == cl["rfc"])
                ).first()

                if not existing_client:
                    new_client = Client(
                        id=clid,
                        legal_name=cl["legal_name"],
                        rfc=cl["rfc"],
                        master_contract_number=cl.get("master_contract_number"),
                        tax_regime=cl.get("tax_regime"),
                        portal_slug=cl.get("portal_slug") or uuid.uuid4().hex[:10],
                        portal_password=cl.get("portal_password"),
                        portal_is_enabled=cl.get("portal_is_enabled", True),
                        is_deleted=cl.get("is_deleted", False)
                    )
                    db.add(new_client)
                    summary["clients_restored"] += 1
                else:
                    if cl.get("portal_slug"):
                        existing_client.portal_slug = cl.get("portal_slug")
                    if cl.get("portal_password"):
                        existing_client.portal_password = cl.get("portal_password")
                    summary["clients_restored"] += 1
            db.flush()

            # 5. Branches
            for b in data.get("branches", []):
                bid = uuid.UUID(b["id"]) if b.get("id") else uuid.uuid4()
                existing_branch = db.query(Branch).filter(Branch.id == bid).first()

                class_val = b.get("classification", "Comercial")
                try:
                    class_enum = BranchClassification(class_val)
                except ValueError:
                    class_enum = BranchClassification.COMERCIAL

                if not existing_branch:
                    new_branch = Branch(
                        id=bid,
                        client_id=uuid.UUID(b["client_id"]),
                        name=b["name"],
                        unit_code=b.get("unit_code"),
                        address=b["address"],
                        phone=b["phone"],
                        classification=class_enum,
                        responsible_contact_name=b.get("responsible_contact_name", "Responsable de Sucursal"),
                        responsible_contact_email=b.get("responsible_contact_email"),
                        is_deleted=b.get("is_deleted", False)
                    )
                    db.add(new_branch)
                    summary["branches_restored"] += 1
                else:
                    summary["branches_restored"] += 1
            db.flush()

            # 6. Service Orders
            for o in data.get("service_orders", []):
                oid = uuid.UUID(o["id"]) if o.get("id") else uuid.uuid4()
                existing_order = db.query(ServiceOrder).filter(
                    or_(ServiceOrder.id == oid, ServiceOrder.folio == o["folio"])
                ).first()

                start_dt = datetime.fromisoformat(o["service_start_date"]) if o.get("service_start_date") else datetime.now(timezone.utc)
                end_dt = datetime.fromisoformat(o["service_end_date"]) if o.get("service_end_date") else start_dt

                if not existing_order:
                    new_order = ServiceOrder(
                        id=oid,
                        folio=o["folio"],
                        branch_id=uuid.UUID(o["branch_id"]),
                        technician_id=uuid.UUID(o["technician_id"]),
                        service_start_date=start_dt,
                        service_end_date=end_dt,
                        pest_crawling_insects=o.get("pest_crawling_insects", False),
                        pest_rodents=o.get("pest_rodents", False),
                        pest_flying_insects=o.get("pest_flying_insects", False),
                        pest_others=o.get("pest_others"),
                        proc_aspersion=o.get("proc_aspersion", False),
                        proc_baits=o.get("proc_baits", False),
                        proc_traps=o.get("proc_traps", False),
                        proc_gels=o.get("proc_gels", False),
                        proc_ulv_fogging=o.get("proc_ulv_fogging", False),
                        proc_thermofogging=o.get("proc_thermofogging", False),
                        results_summary=o.get("results_summary"),
                        observations=o.get("observations"),
                        client_signature_data=o.get("client_signature_data"),
                        is_deleted=o.get("is_deleted", False)
                    )
                    db.add(new_order)
                    summary["orders_restored"] += 1
                else:
                    summary["orders_restored"] += 1
            db.flush()

            # 7. Certificates
            for cert in data.get("certificates", []):
                cid = uuid.UUID(cert["id"]) if cert.get("id") else uuid.uuid4()
                existing_cert = db.query(Certificate).filter(
                    or_(Certificate.id == cid, Certificate.certificate_folio == cert["certificate_folio"])
                ).first()

                issue_d = date.fromisoformat(cert["issue_date"]) if cert.get("issue_date") else date.today()
                vstart_d = date.fromisoformat(cert["validity_start_date"]) if cert.get("validity_start_date") else issue_d
                vend_d = date.fromisoformat(cert["validity_end_date"]) if cert.get("validity_end_date") else issue_d

                if not existing_cert:
                    new_cert = Certificate(
                        id=cid,
                        service_order_id=uuid.UUID(cert["service_order_id"]),
                        certificate_folio=cert["certificate_folio"],
                        issue_date=issue_d,
                        validity_start_date=vstart_d,
                        validity_end_date=vend_d,
                        sanitary_license_number=cert.get("sanitary_license_number", "2023-15A-099"),
                        sanitary_responsible_name=cert.get("sanitary_responsible_name", "Biól. Roberto Sánchez Martínez"),
                        sanitary_responsible_id=cert.get("sanitary_responsible_id"),
                        is_deleted=cert.get("is_deleted", False)
                    )
                    db.add(new_cert)
                    summary["certificates_restored"] += 1
                else:
                    summary["certificates_restored"] += 1
            db.flush()

            # 8. Certificate Chemicals (Pivote)
            for ac in data.get("certificate_chemicals", []):
                acid = uuid.UUID(ac["id"]) if ac.get("id") else uuid.uuid4()
                existing_ac = db.query(CertificateChemical).filter(CertificateChemical.id == acid).first()

                area_val = ac.get("area_type", "Interior")
                try:
                    area_enum = AreaType(area_val)
                except ValueError:
                    area_enum = AreaType.INTERIOR

                if not existing_ac:
                    new_ac = CertificateChemical(
                        id=acid,
                        certificate_id=uuid.UUID(ac["certificate_id"]),
                        chemical_id=uuid.UUID(ac["chemical_id"]),
                        dose_applied=ac["dose_applied"],
                        area_type=area_enum,
                        treated_zones_description=ac.get("treated_zones_description", "Áreas generales"),
                        application_method=ac.get("application_method", "Aspersión Manual")
                    )
                    db.add(new_ac)
                    summary["certificate_chemicals_restored"] += 1
                else:
                    summary["certificate_chemicals_restored"] += 1

            db.commit()
            summary["message"] = f"Restauración completada con éxito en modo '{mode}'. Todos los registros han sido confirmados."
            return summary

        except Exception as e:
            db.rollback()
            summary["status"] = "error"
            summary["message"] = f"Error crítico durante la restauración: {str(e)}"
            raise e

    @staticmethod
    def restore_from_cloud_url(db: Session, url: str, mode: str = "merge") -> Dict[str, Any]:
        """Descarga un archivo de respaldo JSON o ZIP desde una URL en la nube y ejecuta la restauración."""
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "FUMIFLOSA-Backup-Client/1.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            content_bytes = response.read()

        # Detectar si es ZIP o JSON
        if url.endswith(".zip") or content_bytes[:4] == b"PK\x03\x04":
            with zipfile.ZipFile(io.BytesIO(content_bytes), "r") as zf:
                json_filename = [f for f in zf.namelist() if f.endswith(".json")][0]
                json_str = zf.read(json_filename).decode("utf-8")
                backup_data = json.loads(json_str)
        else:
            backup_data = json.loads(content_bytes.decode("utf-8"))

        return SystemBackupRestoreService.restore_full_backup(db, backup_data, mode=mode)

    @staticmethod
    def generate_bulk_certificates_zip(
        db: Session,
        client_id: Optional[uuid.UUID] = None,
        branch_id: Optional[uuid.UUID] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status_filter: Optional[str] = None
    ) -> Tuple[bytes, str, int]:
        """
        Genera en memoria un archivo ZIP con todos los PDFs oficiales que cumplan los filtros seleccionados,
        junto con un reporte manifiesto en CSV.
        """
        query = db.query(ServiceOrder).options(
            joinedload(ServiceOrder.branch).joinedload(Branch.client),
            joinedload(ServiceOrder.technician),
            joinedload(ServiceOrder.certificate).joinedload(Certificate.applied_chemicals).joinedload(CertificateChemical.chemical)
        ).join(Branch).join(Certificate).filter(
            ServiceOrder.is_deleted == False,
            Certificate.is_deleted == False
        )

        if client_id:
            query = query.filter(Branch.client_id == client_id)

        if branch_id:
            query = query.filter(Branch.id == branch_id)

        if year:
            query = query.filter(extract('year', Certificate.issue_date) == year)

        if month:
            query = query.filter(extract('month', Certificate.issue_date) == month)

        if start_date:
            query = query.filter(Certificate.issue_date >= start_date)

        if end_date:
            query = query.filter(Certificate.issue_date <= end_date)

        today = date.today()
        if status_filter == "vigente":
            query = query.filter(Certificate.validity_end_date >= today)
        elif status_filter == "vencido":
            query = query.filter(Certificate.validity_end_date < today)

        orders = query.order_by(Certificate.issue_date.desc()).all()

        company = db.query(CompanyConfig).first()

        zip_buffer = io.BytesIO()
        csv_manifest_lines = [
            "Folio Certificado,Folio Orden,Cliente,RFC,Sucursal,Fecha Expedicion,Inicio Vigencia,Fin Vigencia,Estado,Tecnico"
        ]

        count = 0
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for order in orders:
                if order.certificate:
                    cert = order.certificate
                    branch = order.branch
                    client = branch.client
                    is_valid = cert.validity_end_date >= today
                    state_str = "VIGENTE" if is_valid else "VENCIDO"

                    # 1. Generar PDF
                    pdf_bytes = OfficialCertificatePDFGenerator.generate(order, cert, company=company)
                    
                    clean_client = "".join(c for c in client.legal_name if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')[:30]
                    clean_branch = "".join(c for c in branch.name if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')[:30]
                    file_name = f"Cert_{clean_client}_{clean_branch}_{cert.certificate_folio}_{cert.issue_date.strftime('%Y%m%d')}.pdf"
                    
                    zip_file.writestr(file_name, pdf_bytes)
                    count += 1

                    # 2. Agregar a Manifiesto CSV
                    tech_name = order.technician.full_name if order.technician else "N/A"
                    csv_manifest_lines.append(
                        f'"{cert.certificate_folio}","{order.folio}","{client.legal_name}","{client.rfc}","{branch.name}","{cert.issue_date}","{cert.validity_start_date}","{cert.validity_end_date}","{state_str}","{tech_name}"'
                    )

            # Escribir manifiesto dentro del ZIP
            manifest_content = "\n".join(csv_manifest_lines)
            zip_file.writestr("MANIFIESTO_CERTIFICADOS.csv", manifest_content.encode("utf-8-sig"))

        zip_buffer.seek(0)
        
        # Nombre descriptivo del archivo ZIP
        filename_parts = ["Certificados_FUMIFLOSA"]
        if client_id:
            target_client = db.query(Client).filter(Client.id == client_id).first()
            if target_client:
                filename_parts.append(target_client.rfc)
        if year:
            filename_parts.append(str(year))
        if month:
            filename_parts.append(f"M{month:02d}")
        filename_parts.append(date.today().strftime('%Y%m%d'))
        
        final_filename = "_".join(filename_parts) + ".zip"
        return zip_buffer.getvalue(), final_filename, count
