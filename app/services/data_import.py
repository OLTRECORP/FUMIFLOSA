import io
import re
from datetime import datetime, date, time, timedelta, timezone
from typing import Optional, Dict, Any, List

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
    Permite hasta 4 ingredientes activos / químicos con su información por certificado:
      - Vía columnas numeradas: (quimico_nombre_1..4, ingrediente_activo_1..4, quimico_cicoplafest_1..4, dosis_1..4, lugar_tratado_1..4, metodo_1..4)
      - Vía columnas base o delimitadas por '|' o ';'
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
        if not val_str or val_str.lower() in ('nan', 'none', 'null', '0', '00'):
            return None

        # Si el día viene como 00 o 0 (ej. 00/03/2020), corregir a 01 para permitir lectura segura
        val_str = re.sub(r'^00?([/-])', r'01\1', val_str)

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

    def _get_first_val(self, row: dict, keys: List[str]) -> Optional[str]:
        """Devuelve el primer valor no vacío de una lista de claves posibles."""
        for k in keys:
            v = row.get(k)
            if v is not None and not pd.isna(v) and str(v).strip():
                return str(v).strip()
        return None

    def _extract_chemicals_from_row(self, row: dict) -> List[Dict[str, Any]]:
        """
        Extrae hasta 4 químicos/ingredientes activos de una fila del CSV.
        Soporta:
          1. Columnas individuales: _1, _2, _3, _4 (o sin guion bajo 1, 2, 3, 4)
          2. Delimitadores pipe '|' o ';' dentro de las columnas base
        """
        extracted = []

        # 1. Checar slots 1 a 4 por columnas numeradas
        for i in [1, 2, 3, 4]:
            suffix = f"_{i}"
            suffix_alt = f"{i}"

            possible_name_keys = [f"quimico_nombre{suffix}", f"quimico_nombre{suffix_alt}", f"producto{suffix}", f"producto{suffix_alt}"]
            if i == 1:
                possible_name_keys.extend(["quimico_nombre", "producto", "nombre_comercial"])

            possible_active_keys = [f"ingrediente_activo{suffix}", f"ingrediente_activo{suffix_alt}", f"activo{suffix}", f"activo{suffix_alt}"]
            if i == 1:
                possible_active_keys.extend(["ingrediente_activo", "activo", "ingrediente"])

            possible_cico_keys = [f"quimico_cicoplafest{suffix}", f"quimico_cicoplafest{suffix_alt}", f"cicoplafest{suffix}", f"cicoplafest{suffix_alt}"]
            if i == 1:
                possible_cico_keys.extend(["quimico_cicoplafest", "cicoplafest", "registro_cicoplafest"])

            possible_dose_keys = [f"dosis{suffix}", f"dosis{suffix_alt}"]
            if i == 1:
                possible_dose_keys.extend(["dosis", "dosis_autorizada"])

            possible_lugar_keys = [f"lugar_tratado{suffix}", f"lugar_tratado{suffix_alt}", f"zona_tratada{suffix}", f"zona{suffix}"]
            if i == 1:
                possible_lugar_keys.extend(["lugar_tratado", "zona_tratada", "lugar", "zonas_tratadas"])

            possible_metodo_keys = [f"metodo{suffix}", f"metodo{suffix_alt}", f"metodo_aplicacion{suffix}"]
            if i == 1:
                possible_metodo_keys.extend(["metodo", "metodo_aplicacion", "procedimiento"])

            name = self._get_first_val(row, possible_name_keys)
            active = self._get_first_val(row, possible_active_keys)
            cico = self._get_first_val(row, possible_cico_keys)
            dose = self._get_first_val(row, possible_dose_keys)
            lugar = self._get_first_val(row, possible_lugar_keys)
            metodo = self._get_first_val(row, possible_metodo_keys)

            if name or active or cico:
                safe_name = name or active or f"Químico #{i}"
                safe_active = active or name or "Ingrediente Activo"
                safe_cico = (cico or f"RSCO-URB-INAC-{abs(hash(safe_name + safe_active)) % 10000:04d}-2026").rstrip('|').rstrip(';').strip()
                
                extracted.append({
                    "slot": i,
                    "name": safe_name,
                    "active_ingredient": safe_active,
                    "cicoplafest": safe_cico,
                    "dose": dose or "10 ml / 1 L",
                    "lugar": lugar or "Áreas comunes e interiores",
                    "metodo": metodo or "Aspersión Manual"
                })

        # 2. Si solo se detectó 1 químico (o ninguno) y existen delimitadores '|' o ';' en los campos base
        if len(extracted) <= 1:
            base_name = str(row.get("quimico_nombre") or "")
            base_active = str(row.get("ingrediente_activo") or "")
            base_cico = str(row.get("quimico_cicoplafest") or "")
            base_dose = str(row.get("dosis") or "")
            base_lugar = str(row.get("lugar_tratado") or "")
            base_metodo = str(row.get("metodo") or "")

            delim = "|" if "|" in (base_active + base_name) else (";" if ";" in (base_active + base_name) else None)
            
            if delim:
                names = [s.strip() for s in base_name.split(delim) if s.strip()]
                actives = [s.strip() for s in base_active.split(delim) if s.strip()]
                cicos = [s.strip() for s in base_cico.split(delim) if s.strip()]
                doses = [s.strip() for s in base_dose.split(delim) if s.strip()]
                lugares = [s.strip() for s in base_lugar.split(delim) if s.strip()]
                metodos = [s.strip() for s in base_metodo.split(delim) if s.strip()]

                total_count = min(4, max(len(names), len(actives), len(cicos)))
                if total_count > 1:
                    extracted = []
                    for idx in range(total_count):
                        item_name = names[idx] if idx < len(names) else (actives[idx] if idx < len(actives) else f"Químico #{idx+1}")
                        item_active = actives[idx] if idx < len(actives) else item_name
                        item_cico = cicos[idx] if idx < len(cicos) else f"RSCO-URB-INAC-{abs(hash(item_name)) % 10000:04d}-2026"
                        item_dose = doses[idx] if idx < len(doses) else (doses[0] if doses else "10 ml / 1 L")
                        item_lugar = lugares[idx] if idx < len(lugares) else (lugares[0] if lugares else "Áreas comunes e interiores")
                        item_metodo = metodos[idx] if idx < len(metodos) else (metodos[0] if metodos else "Aspersión Manual")
                        
                        extracted.append({
                            "slot": idx + 1,
                            "name": item_name,
                            "active_ingredient": item_active,
                            "cicoplafest": item_cico,
                            "dose": item_dose,
                            "lugar": item_lugar,
                            "metodo": item_metodo
                        })

        # Fallback predeterminado si no se encontró nada
        if not extracted:
            extracted.append({
                "slot": 1,
                "name": str(row.get("quimico_nombre") or "Insecticida Piretroide").strip(),
                "active_ingredient": str(row.get("ingrediente_activo") or "Deltametrina 2.5%").strip(),
                "cicoplafest": str(row.get("quimico_cicoplafest") or "RSCO-URB-INAC-111-2020").strip(),
                "dose": str(row.get("dosis") or "10 ml / 1 L").strip(),
                "lugar": str(row.get("lugar_tratado") or "Áreas comunes e interiores").strip(),
                "metodo": str(row.get("metodo") or "Aspersión Manual").strip()
            })

        return extracted[:4]

    def process_csv(self, file_contents: bytes) -> dict:
        """
        Ingesta, normaliza y persiste órdenes y certificados históricos en una sola transacción atómica.
        Permite hasta 4 químicos/ingredientes activos por certificado (33 columnas).
        """
        # Intentar leer con encoding UTF-8 o latin1
        try:
            df = pd.read_csv(io.BytesIO(file_contents), dtype=str, encoding='utf-8-sig')
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(io.BytesIO(file_contents), dtype=str, encoding='latin1')
            except Exception:
                df = pd.read_csv(io.BytesIO(file_contents), dtype=str, encoding='cp1252')

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
                "El archivo CSV debe contener la columna de fecha de expedición: 'fecha_de_exp'."
            )

        summary = {
            "clients_created": 0,
            "clients_linked": 0,
            "branches_created": 0,
            "branches_linked": 0,
            "orders_processed": 0,
            "chemicals_created": 0,
            "chemicals_linked": 0,
            "applied_chemicals_total": 0,
            "duplicates_skipped": 0,
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
            all_clients = self.db.query(Client).filter(Client.is_deleted == False).all()
            clients_by_rfc = {c.rfc.strip().upper(): c for c in all_clients if c.rfc}
            clients_by_name = {c.legal_name.strip().upper(): c for c in all_clients if c.legal_name}

            all_branches = self.db.query(Branch).filter(Branch.is_deleted == False).all()
            branches_by_name = {(b.client_id, b.name.strip().upper()): b for b in all_branches}
            branches_by_addr = {
                (b.client_id, b.address.strip().upper()): b for b in all_branches if b.address and len(b.address.strip()) > 5
            }

            all_chemicals = self.db.query(Chemical).filter(Chemical.is_deleted == False).all()
            chems_by_cico = {c.cicoplafest_number.strip().upper(): c for c in all_chemicals if c.cicoplafest_number}
            chems_by_name = {c.commercial_name.strip().upper(): c for c in all_chemicals if c.commercial_name}
            chems_by_active = {c.active_ingredient.strip().upper(): c for c in all_chemicals if c.active_ingredient}

            users_cache = {u.email.lower(): u for u in self.db.query(User).all()}
            existing_cert_folios = {cert.certificate_folio.strip().upper() for cert in self.db.query(Certificate.certificate_folio).filter(Certificate.is_deleted == False).all()}
            existing_order_folios = {order.folio.strip().upper() for order in self.db.query(ServiceOrder.folio).filter(ServiceOrder.is_deleted == False).all()}

            existing_cert_dates_branches = set()
            for cert, order in self.db.query(Certificate, ServiceOrder).join(ServiceOrder, Certificate.service_order_id == ServiceOrder.id).filter(Certificate.is_deleted == False, ServiceOrder.is_deleted == False).all():
                existing_cert_dates_branches.add((cert.issue_date, order.branch_id))

            # Técnico por defecto
            default_tech = users_cache.get("admin@fumiflosa.mx")
            if not default_tech:
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
                row_num = idx + 2

                rfc = (row.get('rfc') or '').strip().upper()
                razon_social = (row.get('razon_social') or '').strip()
                sucursal_nombre = (row.get('sucursal_nombre') or '').strip()
                sucursal_direccion = (row.get('sucursal_direccion') or '').strip()

                if not razon_social and not sucursal_nombre:
                    summary["errors"].append(f"Línea {row_num}: Razón Social y Sucursal vacías (omitida).")
                    continue

                if not razon_social:
                    razon_social = sucursal_nombre or "CLIENTE GENERAL FUMIFLOSA"
                if not sucursal_nombre:
                    sucursal_nombre = "Matriz / Principal"

                # Parseo de Fecha de Expedición
                exp_date = self._parse_date(row.get(date_col))
                if not exp_date:
                    summary["errors"].append(f"Línea {row_num}: Fecha de expedición '{row.get(date_col)}' inválida.")
                    continue

                # 1. Gestión / Upsert de Cliente Matriz
                client = None
                if rfc:
                    client = clients_by_rfc.get(rfc)
                    if not client:
                        client = clients_by_name.get(razon_social.upper())

                if not client and not rfc:
                    client = clients_by_name.get(razon_social.upper())

                if not client:
                    # Crear nuevo cliente
                    if not rfc:
                        # Generar RFC genérico único
                        rfc = f"GEN{abs(hash(razon_social)) % 1000000000:09d}"[:13]
                        while rfc in clients_by_rfc:
                            rfc = f"GEN{abs(hash(razon_social + str(idx))) % 1000000000:09d}"[:13]

                    new_client = Client(
                        legal_name=razon_social,
                        rfc=rfc,
                        tax_regime=row.get('regimen_fiscal', '601 - General de Ley Personas Morales')
                    )
                    self.db.add(new_client)
                    self.db.flush()
                    clients_by_rfc[rfc] = new_client
                    clients_by_name[razon_social.upper()] = new_client
                    client = new_client
                    summary["clients_created"] += 1
                else:
                    summary["clients_linked"] += 1

                # 2. Gestión / Upsert de Sucursal
                branch = branches_by_name.get((client.id, sucursal_nombre.upper()))
                if not branch and sucursal_direccion and len(sucursal_direccion) > 5:
                    branch = branches_by_addr.get((client.id, sucursal_direccion.upper()))

                if not branch:
                    new_branch = Branch(
                        client_id=client.id,
                        name=sucursal_nombre,
                        address=sucursal_direccion or 'Domicilio no especificado',
                        phone=(row.get('sucursal_telefono') or '5500000000').strip(),
                        classification=BranchClassification.COMERCIAL,
                        responsible_contact_name=(row.get('contacto_sucursal') or 'Encargado de Unidad').strip()
                    )
                    self.db.add(new_branch)
                    self.db.flush()
                    branches_by_name[(client.id, sucursal_nombre.upper())] = new_branch
                    if sucursal_direccion:
                        branches_by_addr[(client.id, sucursal_direccion.upper())] = new_branch
                    branch = new_branch
                    summary["branches_created"] += 1
                else:
                    summary["branches_linked"] += 1

                # 3. Determinación de Folios y Validación de Duplicidad
                input_folio = (row.get('folio') or '').strip().lstrip('/').strip()
                if input_folio.lower() in ('nan', 'none', 'null'):
                    input_folio = ''

                if input_folio:
                    cert_folio = input_folio
                    order_folio = f"ORD-{input_folio}" if not input_folio.startswith("ORD-") else input_folio
                else:
                    cert_folio = f"HIST-CERT-{seq_num:06d}"
                    order_folio = f"HIST-ORD-{seq_num:06d}"
                    seq_num += 1

                # Omitir si ya existe el certificado por folio
                if cert_folio.upper() in existing_cert_folios:
                    summary["errors"].append(f"Línea {row_num}: El certificado con folio '{cert_folio}' ya existe (omitido por duplicidad).")
                    summary["duplicates_skipped"] += 1
                    continue

                # Omitir si ya existe un certificado con la misma (fecha_de_exp, sucursal_id)
                if (exp_date, branch.id) in existing_cert_dates_branches:
                    summary["errors"].append(f"Línea {row_num}: Ya existe un certificado emitido el {exp_date} para la sucursal '{branch.name}' (omitido por duplicidad).")
                    summary["duplicates_skipped"] += 1
                    continue

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
                existing_cert_dates_branches.add((exp_date, branch.id))

                # 6. Extraer y Persistir hasta 4 Químicos / Ingredientes Activos
                chem_items = self._extract_chemicals_from_row(row.to_dict())

                for item in chem_items:
                    cico = item["cicoplafest"].upper().strip()
                    c_name = item["name"].strip()
                    c_active = item["active_ingredient"].strip()

                    chem_entity = chems_by_cico.get(cico)
                    if not chem_entity:
                        chem_entity = chems_by_name.get(c_name.upper())
                    if not chem_entity:
                        chem_entity = chems_by_active.get(c_active.upper())

                    if not chem_entity:
                        chem_entity = Chemical(
                            commercial_name=c_name,
                            active_ingredient=c_active,
                            cicoplafest_number=cico,
                            authorized_dose_per_liter=item["dose"],
                            compatible_methods=item["metodo"],
                            toxicological_category="Precaución / Banda Verde",
                            safety_interval_hours=2
                        )
                        self.db.add(chem_entity)
                        self.db.flush()
                        chems_by_cico[cico] = chem_entity
                        chems_by_name[c_name.upper()] = chem_entity
                        chems_by_active[c_active.upper()] = chem_entity
                        summary["chemicals_created"] += 1
                    else:
                        summary["chemicals_linked"] += 1

                    area_t = self._detect_area_type(item["lugar"])

                    cert_chem = CertificateChemical(
                        certificate_id=certificate.id,
                        chemical_id=chem_entity.id,
                        dose_applied=item["dose"],
                        area_type=area_t,
                        treated_zones_description=item["lugar"],
                        application_method=item["metodo"]
                    )
                    self.db.add(cert_chem)
                    summary["applied_chemicals_total"] += 1

                summary["orders_processed"] += 1

            self.db.commit()
            return summary

        except Exception as e:
            self.db.rollback()
            raise RuntimeError(f"Falla atómica en la importación de datos históricos: {str(e)}")
