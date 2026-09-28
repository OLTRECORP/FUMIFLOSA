import io
from datetime import timedelta, timezone
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models import (
    Client, Branch, Chemical, ServiceOrder, Certificate, 
    CertificateChemical, User, UserRole, BranchClassification, AreaType
)


class HistoricalDataImporter:
    def __init__(self, db: Session):
        self.db = db

    def _get_next_sequence(self, prefix: str) -> int:
        """Obtiene el conteo consecutivo para generar folios unificados."""
        stmt = select(func.count(ServiceOrder.id)).where(ServiceOrder.folio.like(f"{prefix}-%"))
        count = self.db.execute(stmt).scalar() or 0
        return count + 1

    def process_csv(self, file_contents: bytes) -> dict:
        """
        Ingesta, normaliza y persiste órdenes y certificados históricos en una sola transacción atómica.
        """
        df = pd.read_csv(io.BytesIO(file_contents), dtype=str)
        
        # Limpieza inicial
        df.columns = df.columns.str.strip().str.lower()
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        
        # Parseo de fechas con pandas
        df['fecha_inicio_dt'] = pd.to_datetime(df['fecha_inicio'], errors='coerce')
        df['fecha_fin_dt'] = pd.to_datetime(df['fecha_fin'], errors='coerce')
        
        # Filtrar filas con fechas inválidas
        invalid_dates = df['fecha_inicio_dt'].isna() | df['fecha_fin_dt'].isna()
        if invalid_dates.any():
            df = df[~invalid_dates]

        summary = {"clients_created": 0, "branches_created": 0, "orders_processed": 0, "errors": []}
        
        try:
            # 1. Caché de entidades existentes
            clients_cache = {c.rfc: c for c in self.db.query(Client).all()}
            branches_cache = {(b.client_id, b.name): b for b in self.db.query(Branch).all()}
            chemicals_cache = {c.cicoplafest_number: c for c in self.db.query(Chemical).all()}
            users_cache = {u.email: u for u in self.db.query(User).all()}

            # Técnico por defecto
            default_tech = users_cache.get("admin@fumiflosa.mx")
            if not default_tech:
                default_tech = User(
                    email="admin@fumiflosa.mx",
                    full_name="Técnico Principal FUMIFLOSA",
                    hashed_password="hashed_pw_placeholder",
                    role=UserRole.TECNICO_CAMPO
                )
                self.db.add(default_tech)
                self.db.flush()
                users_cache[default_tech.email] = default_tech

            seq_num = self._get_next_sequence("HIST")

            for _, row in df.iterrows():
                rfc = row['rfc']
                razon_social = row['razon_social']
                
                # Gestión de Matriz
                if rfc not in clients_cache:
                    new_client = Client(
                        legal_name=razon_social,
                        rfc=rfc,
                        tax_regime=row.get('regimen_fiscal', '601')
                    )
                    self.db.add(new_client)
                    self.db.flush()
                    clients_cache[rfc] = new_client
                    summary["clients_created"] += 1
                
                client = clients_cache[rfc]

                # Gestión de Sucursal
                branch_key = (client.id, row['sucursal_nombre'])
                if branch_key not in branches_cache:
                    new_branch = Branch(
                        client_id=client.id,
                        name=row['sucursal_nombre'],
                        address=row['sucursal_direccion'],
                        phone=row.get('sucursal_telefono', '5500000000'),
                        classification=BranchClassification.COMERCIAL,
                        responsible_contact_name=row.get('contacto_sucursal', 'Encargado de Unidad')
                    )
                    self.db.add(new_branch)
                    self.db.flush()
                    branches_cache[branch_key] = new_branch
                    summary["branches_created"] += 1

                branch = branches_cache[branch_key]

                # Técnico
                tech_email = row.get('tecnico_email', 'admin@fumiflosa.mx')
                technician = users_cache.get(tech_email, default_tech)

                # Orden de Servicio
                order_folio = f"HIST-ORD-{seq_num:06d}"
                cert_folio = f"HIST-CERT-{seq_num:06d}"
                seq_num += 1

                service_order = ServiceOrder(
                    folio=order_folio,
                    branch_id=branch.id,
                    technician_id=technician.id,
                    service_start_date=row['fecha_inicio_dt'].to_pydatetime().replace(tzinfo=timezone.utc),
                    service_end_date=row['fecha_fin_dt'].to_pydatetime().replace(tzinfo=timezone.utc),
                    pest_crawling_insects=True,
                    pest_rodents=True,
                    proc_aspersion=True,
                    observations=row.get('observaciones', 'Servicio migrado históricamente.'),
                    results_summary="Tratamiento correctivo y preventivo aplicado satisfactoriamente."
                )
                self.db.add(service_order)
                self.db.flush()

                # Certificado NOM-256 (30 días vigencia)
                start_d = row['fecha_inicio_dt'].date()
                certificate = Certificate(
                    service_order_id=service_order.id,
                    certificate_folio=cert_folio,
                    issue_date=start_d,
                    validity_start_date=start_d,
                    validity_end_date=start_d + timedelta(days=30),
                    sanitary_license_number=row.get('licencia_sanitaria', '2023-15A-099'),
                    sanitary_responsible_name=row.get('responsable_sanitario', 'Biól. Responsable Sanitario')
                )
                self.db.add(certificate)
                self.db.flush()

                # Químico
                cicoplafest = row.get('quimico_cicoplafest', 'RSCO-URB-INAC-111-2020')
                if cicoplafest not in chemicals_cache:
                    chem = Chemical(
                        commercial_name=row.get('quimico_nombre', 'Insecticida Piretroide'),
                        active_ingredient=row.get('ingrediente_activo', 'Deltametrina'),
                        cicoplafest_number=cicoplafest,
                        authorized_dose_per_liter=row.get('dosis', '10ml / 1L'),
                        compatible_methods="Aspersión",
                        toxicological_category="Precaución"
                    )
                    self.db.add(chem)
                    self.db.flush()
                    chemicals_cache[cicoplafest] = chem

                chem_entity = chemicals_cache[cicoplafest]

                cert_chem = CertificateChemical(
                    certificate_id=certificate.id,
                    chemical_id=chem_entity.id,
                    dose_applied=row.get('dosis', '10 ml / Litro'),
                    area_type=AreaType.INTERIOR,
                    treated_zones_description=row.get('lugar_tratado', 'Áreas comunes e interiores'),
                    application_method=row.get('metodo', 'Aspersión Manual')
                )
                self.db.add(cert_chem)
                summary["orders_processed"] += 1

            self.db.commit()
            return summary

        except Exception as e:
            self.db.rollback()
            raise RuntimeError(f"Falla atómica en la importación de datos históricos: {str(e)}")
