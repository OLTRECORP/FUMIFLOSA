import io
import re
from datetime import datetime, date, time, timedelta, timezone
from typing import Optional, Dict, Any

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_

from app.models import (
    Client, Branch, Chemical, ServiceOrder, Certificate, 
    CertificateChemical, User, UserRole, BranchClassification, AreaType,
    CompanyConfig
)


class HistoricalDataImporter:
    """
    Importador masivo e inteligente de certificados y clientes históricos.
    Formato esperado:
      folio,rfc,razon_social,sucursal_nombre,sucursal_direccion,sucursal_telefono,
      contacto_sucursal,fecha_de_exp,quimico_nombre,ingrediente_activo,
      quimico_cicoplafest,dosis,lugar_tratado,metodo,observaciones
    """

    def __init__(self, db: Session):
        self.db = db

    def _get_next_sequence(self, prefix: str) -> int:
        """Obtiene el conteo consecutivo para generar folios unificados."""
        stmt = select(func.count(ServiceOrder.id)).where(ServiceOrder.folio.like(f"{prefix}-%"))
        count = self.db.execute(stmt).scalar() or 0
        return count + 1

    def _parse_date(self, val: Any) -> Optional[date]:
        """Convierte cadenas de fecha en diversos formatos (ISO, DD/MM/YYYY, etc.) a date."""
        if pd.isna(val) or val is None:
            return None
        val_str = str(val).strip()
        if not val_str:
            return None

        # Intentar con pandas to_datetime
        try:
            dt = pd.to_datetime(val_str, errors='coerce', dayfirst=True)
            if not pd.isna(dt):
                return dt.date()
        except Exception:
            pass

        try:
            dt = pd.to_datetime(val_str, errors='coerce', dayfirst=False)
            if not pd.isna(dt):
                return dt.date()
        except Exception:
            pass

        # Formatos comunes manuales
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S'):
            try:
                return datetime.strptime(val_str, fmt).date()
            except ValueError:
                continue
        return None

    def _detect_area_type(self, lugar: str) -> AreaType:
        """Detecta automáticamente el tipo de área (Interior, Exterior, Perimetral)."""
        lugar_lower = (lugar or "").lower()
        if "perimetr" in lugar_lower or "barda" in lugar_lower or "cerca" in lugar_lower:
            return AreaType.PERIMETRAL
        elif "exterior" in lugar_lower or "patio" in lugar_lower or "jardin" in lugar_lower or "estacionamiento" in lugar_lower:
            return AreaType.EXTERIOR
        return AreaType.INTERIOR

    def process_csv(self, file_contents: bytes) -> dict:
        """
        Ingesta, normaliza y persiste órdenes y certificados históricos en una sola transacción atómica.
        """
        # Intentar leer con encoding UTF-8 o latin1
        try:
            df = pd.read_csv(io.BytesIO(file_contents), dtype=str, encoding='utf-8-sig')
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(file_contents), dtype=str, encoding='latin1')

        # Normalizar nombres de columnas a minúsculas y sin espacios
        df.columns = df.columns.str.strip().str.lower()
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)

        # Mapeo de alias de fecha de expedición
        date_col = None
        for candidate in ['fecha_de_exp', 'fecha_exp', 'fecha_expedicion', 'fecha_inicio', 'fecha']:
            if candidate in df.columns:
                date_col = candidate
                break

        if not date_col:
            raise ValueError(
                "El archivo CSV no contiene la columna de fecha requerida: 'fecha_de_exp'."
            )

        summary = {
            "clients_created": 0,
            "branches_created": 0,
            "orders_processed": 0,
            "chemicals_created": 0,
            "errors": []
        }

        try:
            # 0. Obtener configuración base de la empresa de fumigación
            company = self.db.query(CompanyConfig).first()
            sanitary_license = company.sanitary_license_number if company else "2023-15A-099"
            sanitary_responsible = company.sanitary_responsible_name if company else "Biól. Roberto Sánchez Martínez"
            sanitary_responsible_id = company.sanitary_responsible_id if company else "CED-8849201"
            validity_days = company.default_validity_days if company else 30

            # 1. Caché de entidades existentes
            clients_cache = {c.rfc.upper(): c for c in self.db.query(Client).all()}
            branches_cache = {(b.client_id, b.name.strip().upper()): b for b in self.db.query(Branch).all()}
            chemicals_cache = {c.cicoplafest_number.strip().upper(): c for c in self.db.query(Chemical).all()}
            users_cache = {u.email.lower(): u for u in self.db.query(User).all()}
            existing_cert_folios = {cert.certificate_folio.strip().upper() for cert in self.db.query(Certificate.certificate_folio).all()}
            existing_order_folios = {order.folio.strip().upper() for order in self.db.query(ServiceOrder.folio).all()}

            # Técnico por defecto
            default_tech = users_cache.get("admin@fumiflosa.mx")
            if not default_tech:
                # Buscar cualquier superadmin o técnico activo
                default_tech = self.db.query(User).filter(User.role == UserRole.SUPERADMIN).first()
                if not default_tech:
                    default_tech = User(
                        username="FOSM630329EA5",
                        email="admin@fumiflosa.mx",
                        full_name="Super Administrador Master - FUMIFLOSA",
                        hashed_password="hash_FLOSA6303",
                        role=UserRole.SUPERADMIN,
                        is_active=True
                    )
                    self.db.add(default_tech)
                    self.db.flush()
                users_cache[default_tech.email.lower()] = default_tech

            seq_num = self._get_next_sequence("HIST")

            for idx, row in df.iterrows():
                row_num = idx + 2 # Línea en el archivo CSV (1-indexed + encabezado)

                rfc = (row.get('rfc') or '').strip().upper()
                razon_social = (row.get('razon_social') or '').strip()
                sucursal_nombre = (row.get('sucursal_nombre') or '').strip()

                if not rfc or not razon_social or not sucursal_nombre:
                    summary["errors"].append(f"Línea {row_num}: Datos incompletos (RFC, Razón Social o Sucursal faltante).")
                    continue

                # Parseo de Fecha de Expedición
                exp_date = self._parse_date(row.get(date_col))
                if not exp_date:
                    summary["errors"].append(f"Línea {row_num}: Fecha de expedición '{row.get(date_col)}' inválida.")
                    continue

                # 1. Gestión de Cliente Matriz
                if rfc not in clients_cache:
                    new_client = Client(
                        legal_name=razon_social,
                        rfc=rfc,
                        tax_regime=row.get('regimen_fiscal', '601 - General de Ley Personas Morales')
                    )
                    self.db.add(new_client)
                    self.db.flush()
                    clients_cache[rfc] = new_client
                    summary["clients_created"] += 1

                client = clients_cache[rfc]

                # 2. Gestión de Sucursal
                branch_key = (client.id, sucursal_nombre.upper())
                if branch_key not in branches_cache:
                    new_branch = Branch(
                        client_id=client.id,
                        name=sucursal_nombre,
                        address=(row.get('sucursal_direccion') or 'Domicilio no especificado').strip(),
                        phone=(row.get('sucursal_telefono') or '5500000000').strip(),
                        classification=BranchClassification.COMERCIAL,
                        responsible_contact_name=(row.get('contacto_sucursal') or 'Encargado de Unidad').strip()
                    )
                    self.db.add(new_branch)
                    self.db.flush()
                    branches_cache[branch_key] = new_branch
                    summary["branches_created"] += 1

                branch = branches_cache[branch_key]

                # 3. Determinación de Folios
                input_folio = (row.get('folio') or '').strip()
                if input_folio:
                    cert_folio = input_folio
                    order_folio = f"ORD-{input_folio}" if not input_folio.startswith("ORD-") else input_folio
                else:
                    cert_folio = f"HIST-CERT-{seq_num:06d}"
                    order_folio = f"HIST-ORD-{seq_num:06d}"
                    seq_num += 1

                # Omitir duplicados exactos si ya existe el certificado
                if cert_folio.upper() in existing_cert_folios:
                    summary["errors"].append(f"Línea {row_num}: El certificado con folio '{cert_folio}' ya existe (omitido).")
                    continue

                # Ajustar order_folio si colisiona
                orig_order_folio = order_folio
                col_idx = 1
                while order_folio.upper() in existing_order_folios:
                    order_folio = f"{orig_order_folio}-{col_idx}"
                    col_idx += 1

                # 4. Crear Orden de Servicio
                service_start = datetime.combine(exp_date, time(9, 0), tzinfo=timezone.utc)
                service_end = service_start + timedelta(hours=2)

                service_order = ServiceOrder(
                    folio=order_folio,
                    branch_id=branch.id,
                    technician_id=default_tech.id,
                    service_start_date=service_start,
                    service_end_date=service_end,
                    pest_crawling_insects=True,
                    pest_rodents=True,
                    proc_aspersion=True,
                    observations=(row.get('observaciones') or 'Servicio migrado históricamente conforme a NOM-256.').strip(),
                    results_summary="Tratamiento integral preventivo y correctivo aplicado satisfactoriamente."
                )
                self.db.add(service_order)
                self.db.flush()
                existing_order_folios.add(order_folio.upper())

                # 5. Crear Certificado NOM-256 Oficial
                certificate = Certificate(
                    service_order_id=service_order.id,
                    certificate_folio=cert_folio,
                    issue_date=exp_date,
                    validity_start_date=exp_date,
                    validity_end_date=exp_date + timedelta(days=validity_days),
                    sanitary_license_number=sanitary_license,
                    sanitary_responsible_name=sanitary_responsible,
                    sanitary_responsible_id=sanitary_responsible_id
                )
                self.db.add(certificate)
                self.db.flush()
                existing_cert_folios.add(cert_folio.upper())

                # 6. Gestión y Dosificación de Químico
                cico = (row.get('quimico_cicoplafest') or 'RSCO-URB-INAC-111-2020').strip().upper()
                if cico not in chemicals_cache:
                    chem = Chemical(
                        commercial_name=(row.get('quimico_nombre') or 'Insecticida Piretroide').strip(),
                        active_ingredient=(row.get('ingrediente_activo') or 'Deltametrina 2.5%').strip(),
                        cicoplafest_number=cico,
                        authorized_dose_per_liter=(row.get('dosis') or '10 ml / 1 L').strip(),
                        compatible_methods=(row.get('metodo') or 'Aspersión Manual').strip(),
                        toxicological_category="Precaución / Banda Verde",
                        safety_interval_hours=2
                    )
                    self.db.add(chem)
                    self.db.flush()
                    chemicals_cache[cico] = chem
                    summary["chemicals_created"] += 1

                chem_entity = chemicals_cache[cico]

                lugar = (row.get('lugar_tratado') or 'Áreas comunes e interiores').strip()
                area_t = self._detect_area_type(lugar)

                cert_chem = CertificateChemical(
                    certificate_id=certificate.id,
                    chemical_id=chem_entity.id,
                    dose_applied=(row.get('dosis') or chem_entity.authorized_dose_per_liter or '10 ml / 1 L').strip(),
                    area_type=area_t,
                    treated_zones_description=lugar,
                    application_method=(row.get('metodo') or 'Aspersión Manual').strip()
                )
                self.db.add(cert_chem)
                summary["orders_processed"] += 1

            self.db.commit()
            return summary

        except Exception as e:
            self.db.rollback()
            raise RuntimeError(f"Falla atómica en la importación de datos históricos: {str(e)}")
