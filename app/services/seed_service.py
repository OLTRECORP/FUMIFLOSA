"""app/services/seed_service.py
Sembrado Automático Integral de la Base de Datos FUMIFLOSA SaaS.
Garantiza que la base de datos (local o en la nube como Render PostgreSQL)
siempre cuente con:
  1. Configuración de Empresa Oficial NOM-256 (Licencia Sanitaria, SINTOX, STPS).
  2. Super Administrador Master y Técnicos de Campo con credenciales activas.
  3. Catálogo Oficial de Químicos COFEPRIS con fichas técnicas y HDS en línea.
  4. Catálogo de Registros RSCO / CICOPLAFEST.
  5. Clientes Institucionales y Sucursales de Referencia (IMSS, Walmart, OXXO, Farmacias del Ahorro).
  6. Órdenes de Servicio y Certificados Oficiales con Químicos Aplicados.
  7. Bitácoras NOM-256 (Calibración de Equipos, Monitoreo de Estaciones, Triple Lavado de Envases, Matriz EPP).
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models import (
    CompanyConfig, User, UserRole, Chemical, RSCOItem,
    Client, Branch, BranchClassification, ServiceOrder, Certificate,
    CertificateChemical, AreaType,
    EquipmentCalibrationLog, StationMonitoringLog, HazardousWasteLog, EPPAnnualMatrix
)
from app.services.pesticide_sheet_service import lookup_online_sheets_by_rsco
from app.services.mip_service import seed_default_rsco_items


DEFAULT_PESTICIDES_CATALOG = [
    {
        "commercial_name": "Biothrine Flow",
        "active_ingredient": "Deltametrina 2.5%",
        "cicoplafest_number": "RSCO-URB-INAC-111-315-009-2.5",
        "authorized_dose_per_liter": "10 a 20 ml / L de agua",
        "safety_interval_hours": 2,
        "compatible_methods": "Aspersión Manual / Aspersión Motorizada",
        "toxicological_category": "Banda Verde / Precaución (Cat. 5)"
    },
    {
        "commercial_name": "Demand 2.5 CS",
        "active_ingredient": "Lambda Cyhalotrina 2.5%",
        "cicoplafest_number": "RSCO-URB-INAC-173-356-064-2.5",
        "authorized_dose_per_liter": "5 a 10 ml / L de agua",
        "safety_interval_hours": 2,
        "compatible_methods": "Aspersión Residual Microencapsulada",
        "toxicological_category": "Banda Verde / Precaución (Cat. 5)"
    },
    {
        "commercial_name": "Maxforce Forte",
        "active_ingredient": "Fipronil 0.05%",
        "cicoplafest_number": "RSCO-URB-INAC-175-359-392-0.05",
        "authorized_dose_per_liter": "1 a 3 gotas (0.25 a 0.5g) / m²",
        "safety_interval_hours": 0,
        "compatible_methods": "Aplicación de Gel Focalizado en Grietas",
        "toxicological_category": "Banda Verde / Precaución (Cat. 5)"
    },
    {
        "commercial_name": "Temprid SC",
        "active_ingredient": "Imidacloprid 21% + Beta-ciflutrina 10.5%",
        "cicoplafest_number": "RSCO-MEZC-INAC-0101-385-342-31.5",
        "authorized_dose_per_liter": "4 a 8 ml / L de agua",
        "safety_interval_hours": 2,
        "compatible_methods": "Aspersión Focalizada e Inyección de Grietas",
        "toxicological_category": "Banda Azul / Moderadamente Tóxico (Cat. 4)"
    },
    {
        "commercial_name": "Advion Cucaracha Gel",
        "active_ingredient": "Indoxacarb 0.6%",
        "cicoplafest_number": "RSCO-URB-INAC-102K-301-392-0.6",
        "authorized_dose_per_liter": "2 a 3 gotas (0.5g) / m²",
        "safety_interval_hours": 0,
        "compatible_methods": "Aplicación de Cebo en Gel Cucarachicida",
        "toxicological_category": "Banda Verde / Precaución (Cat. 5)"
    },
    {
        "commercial_name": "Storm Bloques",
        "active_ingredient": "Flocumafen 0.005%",
        "cicoplafest_number": "RSCO-URB-ROD-0101-301-033-0.005",
        "authorized_dose_per_liter": "1 a 2 bloques (20-40g) por cebadero",
        "safety_interval_hours": 0,
        "compatible_methods": "Estaciones Cebaderas Inviolables",
        "toxicological_category": "Banda Azul / Moderadamente Tóxico (Cat. 4)"
    },
    {
        "commercial_name": "Premise 200 SC",
        "active_ingredient": "Imidacloprid 20%",
        "cicoplafest_number": "RSCO-URB-INAC-198-333-021-30.5",
        "authorized_dose_per_liter": "4 a 8 ml / L de agua",
        "safety_interval_hours": 2,
        "compatible_methods": "Aspersión Focalizada / Inyección Térmica",
        "toxicological_category": "Banda Verde / Precaución (Cat. 5)"
    },
    {
        "commercial_name": "Contrac Blox",
        "active_ingredient": "Bromadiolona 0.005%",
        "cicoplafest_number": "RSCO-URB-ROED-601-301-033-0.005",
        "authorized_dose_per_liter": "1 a 2 bloques por cebadero perimetral",
        "safety_interval_hours": 0,
        "compatible_methods": "Estaciones de Monitoreo y Cebado",
        "toxicological_category": "Banda Azul / Moderadamente Tóxico (Cat. 4)"
    },
    {
        "commercial_name": "Klerat Bloque",
        "active_ingredient": "Brodifacoum 0.005%",
        "cicoplafest_number": "RSCO-URB-ROED-602-302-033-0.005",
        "authorized_dose_per_liter": "1 bloque (20g) por estación",
        "safety_interval_hours": 0,
        "compatible_methods": "Estaciones Cebaderas Perimetrales",
        "toxicological_category": "Banda Azul / Moderadamente Tóxico (Cat. 4)"
    },
    {
        "commercial_name": "Fendona 6 SC",
        "active_ingredient": "Alfacipermetrina 6%",
        "cicoplafest_number": "RSCO-URB-INAC-181-314-064-06.0",
        "authorized_dose_per_liter": "5 ml / L de agua",
        "safety_interval_hours": 2,
        "compatible_methods": "Aspersión Residual en Interiores y Exteriores",
        "toxicological_category": "Banda Verde / Precaución (Cat. 5)"
    },
    {
        "commercial_name": "Alpine WSG",
        "active_ingredient": "Dinoteforan 40%",
        "cicoplafest_number": "RSCO-URB-INAC-195-318-009-40.0",
        "authorized_dose_per_liter": "10 a 30 g / L de agua",
        "safety_interval_hours": 2,
        "compatible_methods": "Aspersión de Gránulos Solubles",
        "toxicological_category": "Banda Verde / Precaución (Cat. 5)"
    },
    {
        "commercial_name": "Nuván 50 CE",
        "active_ingredient": "Diclorvos (DDVP) 50%",
        "cicoplafest_number": "RSCO-URB-INAC-109-305-009-50",
        "authorized_dose_per_liter": "5 a 10 ml / L de agua",
        "safety_interval_hours": 4,
        "compatible_methods": "Nebulización ULV en Frío / Espacios Confinados",
        "toxicological_category": "Banda Amarilla / Moderadamente Tóxico (Cat. 3)"
    },
    {
        "commercial_name": "Dragnet 36.8 CE",
        "active_ingredient": "Permetrina 36.8%",
        "cicoplafest_number": "RSCO-URB-INAC-110-315-009-38.4",
        "authorized_dose_per_liter": "5 a 10 ml / L de agua",
        "safety_interval_hours": 2,
        "compatible_methods": "Aspersión / Termonebulización",
        "toxicological_category": "Banda Verde / Precaución (Cat. 5)"
    },
    {
        "commercial_name": "Archer IGR",
        "active_ingredient": "Piriproxifen 1.3%",
        "cicoplafest_number": "RSCO-URB-INAC-192-311-009-1.3",
        "authorized_dose_per_liter": "2 a 4 ml / L de agua",
        "safety_interval_hours": 2,
        "compatible_methods": "Regulador de Crecimiento de Insectos / Aspersión",
        "toxicological_category": "Banda Verde / Precaución (Cat. 5)"
    },
    {
        "commercial_name": "Talstar Xtra",
        "active_ingredient": "Bifentrina 7.9%",
        "cicoplafest_number": "RSCO-URB-INAC-175-306-009-07.9",
        "authorized_dose_per_liter": "5 a 10 ml / L de agua",
        "safety_interval_hours": 2,
        "compatible_methods": "Aspersión Perimetral y Barreras de Exclusión",
        "toxicological_category": "Banda Verde / Precaución (Cat. 5)"
    }
]


from sqlalchemy.exc import IntegrityError


def seed_company_config(db: Session) -> CompanyConfig:
    """Garantiza la existencia de la configuración de la empresa prestadora."""
    try:
        config = db.query(CompanyConfig).first()
        if not config:
            config = CompanyConfig(
                company_name="MARCO ANTONIO FLORES SÁENZ",
                trade_name="FLOSA Control de Plagas",
                rfc="FOMS630329EA5",
                tax_regime="612 - Personas Físicas con Actividades Empresariales y Profesionales",
                fiscal_address="C10a 685 Col. Centro, Cd. Cuauhtémoc, Chih C.P. 31500",
                phone="625-837-3393",
                email="contacto@flosa.mx",
                website="https://flosa.mx",
                sanitary_license_number="08 17 19 SA 0001",
                sanitary_responsible_name="MARCO ANTONIO FLORES SÁENZ",
                sanitary_responsible_id="CED-8849201",
                stps_registration_number="FOSM-STPS-DC3-2026",
                sintox_emergency_phones="01-800-0092800 / 800-009-2800 / CDMX 55-5598-6659",
                default_reentry_hours=2,
                default_validity_days=30,
                terms_and_notes="Servicio ejecutado conforme a la NOM-256-SSA1-2012. Los plaguicidas empleados cuentan con registro sanitario vigente ante COFEPRIS."
            )
            db.add(config)
            db.commit()
            db.refresh(config)
        else:
            # Asegurar actualización de datos oficiales si tienen valores placeholder antiguos
            if config.sanitary_responsible_name in ["Biól. Roberto Sánchez Martínez", "Roberto Sánchez"]:
                config.sanitary_responsible_name = "MARCO ANTONIO FLORES SÁENZ"
                config.sanitary_license_number = "08 17 19 SA 0001"
                config.company_name = "MARCO ANTONIO FLORES SÁENZ"
                config.trade_name = "FLOSA Control de Plagas"
                config.rfc = "FOMS630329EA5"
                config.phone = "625-837-3393"
                config.fiscal_address = "C10a 685 Col. Centro, Cd. Cuauhtémoc, Chih C.P. 31500"
                db.commit()
        return config
    except IntegrityError:
        db.rollback()
        return db.query(CompanyConfig).first()
    except Exception:
        db.rollback()
        return db.query(CompanyConfig).first()


def seed_users(db: Session) -> int:
    """Garantiza la existencia del Super Administrador Master y de los técnicos aplicadores."""
    count_new = 0
    try:
        # 1. SuperAdmin Master
        master_admin = db.query(User).filter(
            or_(User.username == "FOSM630329EA5", User.email == "admin@fumiflosa.mx")
        ).first()
        if not master_admin:
            master_admin = User(
                username="FOSM630329EA5",
                email="admin@fumiflosa.mx",
                full_name="MARCO ANTONIO FLORES SÁENZ",
                role=UserRole.SUPERADMIN,
                hashed_password="hash_FLOSA6303",
                is_active=True
            )
            db.add(master_admin)
            count_new += 1
        else:
            master_admin.username = "FOSM630329EA5"
            master_admin.full_name = "MARCO ANTONIO FLORES SÁENZ"
            master_admin.role = UserRole.SUPERADMIN
            master_admin.is_active = True
            db.commit()

        # 2. Técnicos Aplicadores con DC-3
        techs = [
            ("tec1@fumiflosa.mx", "tecnico1", "Téc. Juan Carlos Pérez Morales", "NOM-256-DC3-TEC01"),
            ("tec2@fumiflosa.mx", "tecnico2", "Téc. Miguel Ángel Soto Flores", "NOM-256-DC3-TEC02"),
            ("tec3@fumiflosa.mx", "tecnico3", "Téc. Marco Antonio Flores Sáenz", "NOM-256-DC3-TEC03"),
        ]
        for email, uname, name, dc3 in techs:
            t_user = db.query(User).filter(or_(User.username == uname, User.email == email)).first()
            if not t_user:
                t_user = User(
                    username=uname,
                    email=email,
                    full_name=name,
                    role=UserRole.TECNICO_CAMPO,
                    hashed_password="hash_tec123",
                    stps_dc3_file_url=dc3,
                    is_active=True
                )
                db.add(t_user)
                count_new += 1

        db.commit()
    except IntegrityError:
        db.rollback()
    except Exception:
        db.rollback()
    return count_new


def seed_chemicals(db: Session) -> int:
    """Inserta en la tabla chemicals el catálogo oficial COFEPRIS si no existen."""
    count_new = 0
    for p in DEFAULT_PESTICIDES_CATALOG:
        try:
            rsco = p["cicoplafest_number"].strip().upper()
            existing = db.query(Chemical).filter(
                Chemical.cicoplafest_number == rsco,
                Chemical.is_deleted == False
            ).first()
            if not existing:
                sheet_info = lookup_online_sheets_by_rsco(rsco, p["commercial_name"])
                chem = Chemical(
                    commercial_name=p["commercial_name"],
                    active_ingredient=p["active_ingredient"],
                    cicoplafest_number=rsco,
                    authorized_dose_per_liter=p["authorized_dose_per_liter"],
                    safety_interval_hours=p["safety_interval_hours"],
                    compatible_methods=p["compatible_methods"],
                    toxicological_category=p["toxicological_category"],
                    technical_sheet_url=sheet_info.get("technical_sheet_url"),
                    safety_sheet_url=sheet_info.get("safety_sheet_url")
                )
                db.add(chem)
                db.commit()
                count_new += 1
        except IntegrityError:
            db.rollback()
        except Exception:
            db.rollback()
    return count_new


def seed_clients_and_services(db: Session) -> int:
    """
    Inserta clientes institucionales, sucursales y certificados de ejemplo con
    distintas vigencias de forma idempotente y segura.
    """
    # Obtener un técnico y químicos para asociar
    tech = db.query(User).filter(User.role == UserRole.TECNICO_CAMPO, User.is_active == True).first()
    if not tech:
        tech = db.query(User).first()

    chem_biothrine = db.query(Chemical).filter(Chemical.commercial_name.contains("Biothrine")).first()
    chem_maxforce = db.query(Chemical).filter(Chemical.commercial_name.contains("Maxforce")).first()
    chem_demand = db.query(Chemical).filter(Chemical.commercial_name.contains("Demand")).first()
    chem_temprid = db.query(Chemical).filter(Chemical.commercial_name.contains("Temprid")).first()

    today = date.today()

    demo_clients = [
        {
            "legal_name": "INSTITUTO MEXICANO DEL SEGURO SOCIAL",
            "rfc": "IMS421231I45",
            "portal_slug": "imss",
            "contract": "CONTRATO-IMSS-2026-09",
            "branches": [
                {
                    "name": "HGZ No. 1 - Gabriel Mancera",
                    "unit_code": "HGZ-01",
                    "address": "Av. Gabriel Mancera 222, Col. del Valle, Benito Juárez, CDMX",
                    "phone": "5556391122",
                    "contact": "Dra. Marcela Rivas",
                    "classification": BranchClassification.HOSPITALARIA,
                    "service_days_ago": 5, # Vigente (25 días restantes)
                    "folio": "IMSS-2026-001",
                    "quimicos": [chem_biothrine, chem_maxforce],
                    "pests": "Cucarachas, Moscas, Áreas Clínicas",
                    "method": "Aspersión Manual y Gel Focalizado",
                    "areas": "Cocina General, Almacén de Víveres y Archivo Clínico"
                },
                {
                    "name": "UMF No. 28 - Gabriel Mancera",
                    "unit_code": "UMF-28",
                    "address": "Gabriel Mancera 120, Col. del Valle, Benito Juárez, CDMX",
                    "phone": "5556391111",
                    "contact": "Dra. María Garza",
                    "classification": BranchClassification.HOSPITALARIA,
                    "service_days_ago": 24, # Próximo a vencer en 6 días (Crítico)
                    "folio": "IMSS-2026-002",
                    "quimicos": [chem_maxforce],
                    "pests": "Cucaracha Alemana",
                    "method": "Gel Cucarachicida",
                    "areas": "Consultorios 1 al 12 y Farmacia"
                },
                {
                    "name": "Hospital General de Zona No. 24",
                    "unit_code": "HGZ-24",
                    "address": "Av. Insurgentes Norte 1322, Gustavo A. Madero, CDMX",
                    "phone": "5557812033",
                    "contact": "Dr. Armando Fuentes",
                    "classification": BranchClassification.HOSPITALARIA,
                    "service_days_ago": 16, # Advertencia (14 días restantes)
                    "folio": "IMSS-2026-003",
                    "quimicos": [chem_demand, chem_biothrine],
                    "pests": "Insectos Rastreros y Voladores",
                    "method": "Aspersión Residual Microencapsulada",
                    "areas": "Comedores, Sótanos y Perímetros"
                }
            ]
        },
        {
            "legal_name": "NUEVA WAL-MART DE MEXICO S.DE R.L. DE C.V.",
            "rfc": "WAL860507P92",
            "portal_slug": "walmart",
            "contract": "WAL-CORP-2026-A",
            "branches": [
                {
                    "name": "Walmart Express Félix Cuevas",
                    "unit_code": "WAL-374",
                    "address": "Félix Cuevas 374, Tlacoquemécatl del Valle, Benito Juárez, CDMX",
                    "phone": "5555754400",
                    "contact": "Lic. Roberto Gómez",
                    "classification": BranchClassification.COMERCIAL,
                    "service_days_ago": 2, # Reciente (28 días restantes)
                    "folio": "WAL-2026-088",
                    "quimicos": [chem_temprid, chem_maxforce],
                    "pests": "Cucarachas, Hormigas, Roedores",
                    "method": "Microinyección y Cebado",
                    "areas": "Piso de Venta, Bodega de Secos y Panadería"
                },
                {
                    "name": "Bodega Aurrera San Antonio",
                    "unit_code": "BA-102",
                    "address": "Av. Central 210, San Antonio, Álvaro Obregón, CDMX",
                    "phone": "5552731000",
                    "contact": "Ing. Patricia Vega",
                    "classification": BranchClassification.COMERCIAL,
                    "service_days_ago": 45, # Vencido (hace 15 días)
                    "folio": "WAL-2026-072",
                    "quimicos": [chem_biothrine],
                    "pests": "Insectos Rastreros",
                    "method": "Aspersión Manual",
                    "areas": "Andenes de Carga y Pasillos de Trastienda"
                }
            ]
        },
        {
            "legal_name": "CADENA COMERCIAL OXXO SA DE CV",
            "rfc": "CCO8605231N4",
            "portal_slug": "oxxo",
            "contract": "OXXO-METRO-2026",
            "branches": [
                {
                    "name": "OXXO Insurgentes Sur",
                    "unit_code": "OXXO-1500",
                    "address": "Av. Insurgentes Sur 1500, Crédito Constructor, Benito Juárez, CDMX",
                    "phone": "5552345678",
                    "contact": "Lic. Carlos Mendoza",
                    "classification": BranchClassification.COMERCIAL,
                    "service_days_ago": 10, # Vigente (20 días restantes)
                    "folio": "OXXO-2026-042",
                    "quimicos": [chem_biothrine, chem_demand],
                    "pests": "Cucarachas y Moscas",
                    "method": "Aspersión y Termonebulización",
                    "areas": "Bodega y Área de Mostrador"
                }
            ]
        }
    ]

    total_services_created = 0

    for c_data in demo_clients:
        try:
            client = db.query(Client).filter(Client.rfc == c_data["rfc"]).first()
            if not client:
                client = Client(
                    legal_name=c_data["legal_name"],
                    rfc=c_data["rfc"],
                    portal_slug=c_data["portal_slug"],
                    master_contract_number=c_data["contract"],
                    portal_is_enabled=True
                )
                db.add(client)
                db.commit()
                db.refresh(client)

            for b_data in c_data["branches"]:
                branch = db.query(Branch).filter(
                    Branch.client_id == client.id,
                    Branch.name == b_data["name"]
                ).first()
                if not branch:
                    branch = Branch(
                        client_id=client.id,
                        name=b_data["name"],
                        unit_code=b_data.get("unit_code"),
                        full_address=b_data["address"],
                        phone=b_data["phone"],
                        branch_contact_name=b_data["contact"],
                        classification=b_data["classification"]
                    )
                    db.add(branch)
                    db.commit()
                    db.refresh(branch)

                # Verificar si la orden ya existe
                existing_order = db.query(ServiceOrder).filter(ServiceOrder.folio == b_data["folio"]).first()
                if not existing_order:
                    svc_date = today - timedelta(days=b_data["service_days_ago"])
                    start_dt = datetime.combine(svc_date, datetime.min.time().replace(hour=8, minute=0)).replace(tzinfo=timezone.utc)
                    end_dt = datetime.combine(svc_date, datetime.min.time().replace(hour=11, minute=0)).replace(tzinfo=timezone.utc)
                    validity_end = svc_date + timedelta(days=30)

                    service_order = ServiceOrder(
                        branch_id=branch.id,
                        technician_id=tech.id if tech else None,
                        folio=b_data["folio"],
                        status="completed",
                        service_start_date=start_dt,
                        service_end_date=end_dt,
                        scheduled_for=start_dt,
                        pest_detected=b_data["pests"],
                        areas_treated=b_data["areas"],
                        application_method=b_data["method"],
                        general_observations="Servicio mensual preventivo y correctivo conforme a la NOM-256-SSA1-2012."
                    )
                    db.add(service_order)
                    db.commit()
                    db.refresh(service_order)

                    certificate = Certificate(
                        service_order_id=service_order.id,
                        issue_date=svc_date,
                        validity_end_date=validity_end,
                        reentry_safety_hours=2,
                        sanitary_license_number_snapshot="2023-15A-099",
                        sanitary_responsible_name_snapshot="Biól. Roberto Sánchez Martínez",
                        is_cancelled=False
                    )
                    db.add(certificate)
                    db.commit()
                    db.refresh(certificate)

                    # Químicos aplicados
                    for chem in b_data.get("quimicos", []):
                        if chem:
                            app_chem = CertificateChemical(
                                certificate_id=certificate.id,
                                chemical_id=chem.id,
                                chemical_name_snapshot=chem.commercial_name,
                                active_ingredient_snapshot=chem.active_ingredient,
                                cicoplafest_snapshot=chem.cicoplafest_number,
                                dose_applied_snapshot=chem.authorized_dose_per_liter,
                                applied_area_snapshot=b_data["areas"],
                                application_method_snapshot=b_data["method"],
                                area_type=AreaType.INTERIOR
                            )
                            db.add(app_chem)

                    db.commit()
                    total_services_created += 1
        except IntegrityError:
            db.rollback()
        except Exception:
            db.rollback()

    return total_services_created


def seed_bitacoras_and_equipment(db: Session) -> int:
    """Inserta registros base de calibración de equipos y monitoreo de estaciones."""
    count = 0
    # 1. Calibración de Equipos
    if db.query(EquipmentCalibrationLog).filter(EquipmentCalibrationLog.is_deleted == False).count() == 0:
        equipments = [
            {
                "name": "Aspersor Manual de Presión Previa Birchmeier Iris 15L",
                "serial": "BIR-2023-0891",
                "nozzle": "Abanico Plano TeeJet 8002",
                "pressure": "40 psi",
                "flow": "0.75 L/min",
                "status": "OPERATIVO",
                "tech": "Téc. Juan Carlos Pérez Morales",
                "notes": "Prueba de hermeticidad y gasto volumétrico conforme a NOM-256."
            },
            {
                "name": "Termonebulizador Portátil PulsFOG K-10-SP",
                "serial": "PULS-2024-4412",
                "nozzle": "Dosificador de Niebla Térmica 1.0 mm",
                "pressure": "Autónoma por resonador",
                "flow": "12 L/h",
                "status": "OPERATIVO",
                "tech": "Téc. Miguel Ángel Soto Flores",
                "notes": "Limpieza de bujía, calibración de válvula de paso y tanque de mezcla."
            },
            {
                "name": "Nebulizador en Frío ULV Fontan Portastar",
                "serial": "FONT-2022-1090",
                "nozzle": "Boquilla Rotativa ULV Aerosol",
                "pressure": "Compresor Rotativo",
                "flow": "3.5 L/h (GMD 15 micras)",
                "status": "OPERATIVO",
                "tech": "Téc. Marco Antonio Flores Sáenz",
                "notes": "Medición de tamaño de gota micrométrica y verificación de revoluciones."
            }
        ]
        for eq in equipments:
            log = EquipmentCalibrationLog(
                equipment_name=eq["name"],
                serial_number=eq["serial"],
                nozzle_type=eq["nozzle"],
                working_pressure_psi=eq["pressure"],
                flow_rate_lpm=eq["flow"],
                status=eq["status"],
                calibration_date=date.today() - timedelta(days=15),
                next_calibration_date=date.today() + timedelta(days=75),
                technician_name=eq["tech"],
                observations=eq["notes"]
            )
            db.add(log)
            count += 1

    # 2. Monitoreo de Estaciones
    if db.query(StationMonitoringLog).filter(StationMonitoringLog.is_deleted == False).count() == 0:
        stations = [
            ("HGZ No. 1 - Gabriel Mancera", "CEB-01", "Cebadero de Roedor", "Exterior - Perímetro Sur", 25, True, 1, "Rattus norvegicus", "Reposición de cebo Storm Bloques"),
            ("HGZ No. 1 - Gabriel Mancera", "CEB-02", "Cebadero de Roedor", "Exterior - Andén de Residuos", 50, True, 2, "Mus musculus", "Limpieza y reposición de bloque rodenticida"),
            ("Walmart Express Félix Cuevas", "UV-01", "Lámpara de Luz UV", "Interior - Pasillo de Panadería", 0, True, 8, "Musca domestica", "Reemplazo de lámina adhesiva UV"),
            ("Walmart Express Félix Cuevas", "TRAP-01", "Trampa Mecánica de Golpe", "Interior - Almacén de Secos", 0, False, 0, None, "Revisión rutinaria operativa"),
        ]
        for bname, num, stype, zone, cons, act, cnt, ptype, act_corr in stations:
            slog = StationMonitoringLog(
                branch_name=bname,
                station_number=num,
                station_type=stype,
                zone=zone,
                bait_consumption_percent=cons,
                pest_activity_detected=act,
                pest_count=cnt,
                pest_type=ptype,
                corrective_action=act_corr,
                monitoring_date=date.today() - timedelta(days=5),
                technician_name="Téc. Juan Carlos Pérez Morales"
            )
            db.add(slog)
            count += 1

    # 3. Residuos Peligrosos
    if db.query(HazardousWasteLog).filter(HazardousWasteLog.is_deleted == False).count() == 0:
        hwastes = [
            ("Biothrine Flow", "Deltametrina 2.5%", 4, "1 Litro", True, True, date.today() - timedelta(days=10), "MAN-SEMARNAT-2026-088", "Biól. Roberto Sánchez Martínez"),
            ("Temprid SC", "Imidacloprid 21% + Beta-ciflutrina 10.5%", 2, "1 Litro", True, True, date.today() - timedelta(days=12), "MAN-SEMARNAT-2026-089", "Biól. Roberto Sánchez Martínez")
        ]
        for chem_n, act_ing, cnt, cap, tw, perf, wdate, manif, resp in hwastes:
            hlog = HazardousWasteLog(
                chemical_name=chem_n,
                active_ingredient=act_ing,
                containers_count=cnt,
                container_capacity=cap,
                triple_wash_performed=tw,
                containers_perforated=perf,
                wash_date=wdate,
                temporary_storage_location="Área de Residuos FUMIFLOSA",
                disposal_manifest_number=manif,
                responsible_name=resp
            )
            db.add(hlog)
            count += 1

    db.commit()
    return count


def seed_all_database_defaults(db: Session) -> dict:
    """Ejecuta todos los sembradores garantizando integridad y disponibilidad instantánea de datos."""
    cfg = seed_company_config(db)
    u_count = seed_users(db)
    c_count = seed_chemicals(db)
    r_count = seed_default_rsco_items(db)
    s_count = seed_clients_and_services(db)
    b_count = seed_bitacoras_and_equipment(db)

    return {
        "status": "success",
        "company": cfg.trade_name,
        "users_seeded": u_count,
        "chemicals_seeded": c_count,
        "rsco_seeded": r_count,
        "clients_and_services_seeded": s_count,
        "bitacoras_seeded": b_count
    }
