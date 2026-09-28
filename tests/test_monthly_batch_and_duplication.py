import uuid
import pytest
from datetime import datetime, date, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import get_db
from app.models import (
    Base, User, UserRole, Client, Branch, BranchClassification, 
    Chemical, ServiceOrder, Certificate, CertificateChemical, AreaType
)
from app.main import app
from app.services.duplication_service import ServiceDuplicationService
from app.services.email_service import OfficialCertificateEmailService
from app.services.pdf_service import OfficialCertificatePDFGenerator

from sqlalchemy.pool import StaticPool

# Configuración de base de datos de prueba en memoria (SQLite con soporte de UUID como string y StaticPool)
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def seed_test_data(db):
    """Crea datos iniciales de prueba."""
    # 1. Técnico
    tech = User(
        id=uuid.uuid4(),
        email="tecnico@fumiflosa.mx",
        full_name="Técnico Certificado STPS",
        hashed_password="hash_password123",
        role=UserRole.TECNICO_CAMPO,
        stps_registration_number="STPS-TC-2026-001"
    )
    db.add(tech)

    # 2. Cliente Matriz
    client_corp = Client(
        id=uuid.uuid4(),
        legal_name="INSTITUTO MEXICANO DEL SEGURO SOCIAL",
        rfc="IMS421231I45",
        master_contract_number="CTR-2026-IMSS-NACIONAL"
    )
    db.add(client_corp)

    # 3. Sucursales
    branch1 = Branch(
        id=uuid.uuid4(),
        client_id=client_corp.id,
        name="HGZ No. 1 Gabriel Mancera",
        unit_code="HGZ-01",
        address="Gabriel Mancera 222, CDMX",
        phone="5556390000",
        classification=BranchClassification.HOSPITALARIA,
        responsible_contact_name="Dr. Juan Pérez",
        responsible_contact_email="juan.perez@imss.gob.mx"
    )
    branch2 = Branch(
        id=uuid.uuid4(),
        client_id=client_corp.id,
        name="UMF No. 22 San Jerónimo",
        unit_code="UMF-22",
        address="Av. San Jerónimo 110, CDMX",
        phone="5556391111",
        classification=BranchClassification.HOSPITALARIA,
        responsible_contact_name="Dra. María Gómez",
        responsible_contact_email="maria.gomez@imss.gob.mx"
    )
    db.add_all([branch1, branch2])

    # 4. Químico
    chem = Chemical(
        id=uuid.uuid4(),
        commercial_name="Biothrine Flow",
        active_ingredient="Deltametrina 2.5%",
        cicoplafest_number="RSCO-URB-INAC-111-2020",
        authorized_dose_per_liter="10 ml / Litro",
        safety_interval_hours=2,
        compatible_methods="Aspersión Manual",
        toxicological_category="Precaución"
    )
    db.add(chem)
    db.commit()

    # 5. Orden de servicio y certificado inicial para branch1
    start_dt = datetime(2026, 8, 1, 9, 0, 0, tzinfo=timezone.utc)
    end_dt = datetime(2026, 8, 1, 11, 0, 0, tzinfo=timezone.utc)
    order1 = ServiceOrder(
        id=uuid.uuid4(),
        folio="IMSS-ORD-000001",
        branch_id=branch1.id,
        technician_id=tech.id,
        service_start_date=start_dt,
        service_end_date=end_dt,
        pest_crawling_insects=True,
        pest_rodents=True,
        pest_flying_insects=False,
        proc_aspersion=True,
        proc_baits=True,
        results_summary="Servicio inicial de agosto.",
        observations="Sin novedades."
    )
    db.add(order1)
    db.flush()

    cert1 = Certificate(
        id=uuid.uuid4(),
        service_order_id=order1.id,
        certificate_folio="IMSS-CERT-000001",
        issue_date=start_dt.date(),
        validity_start_date=start_dt.date(),
        validity_end_date=start_dt.date() + timedelta(days=30),
        sanitary_license_number="2023-15A-099",
        sanitary_responsible_name="Biól. Roberto Sánchez Martínez",
        sanitary_responsible_id="CED-8849201"
    )
    db.add(cert1)
    db.flush()

    cert_chem = CertificateChemical(
        id=uuid.uuid4(),
        certificate_id=cert1.id,
        chemical_id=chem.id,
        dose_applied="10 ml / Litro",
        area_type=AreaType.INTERIOR,
        treated_zones_description="Áreas de urgencias y pasillos",
        application_method="Aspersión Manual"
    )
    db.add(cert_chem)
    db.commit()

    return {
        "tech": tech,
        "client": client_corp,
        "branch1": branch1,
        "branch2": branch2,
        "chem": chem,
        "order1": order1,
        "cert1": cert1
    }


def test_duplicate_single_service(db_session):
    data = seed_test_data(db_session)
    source_order = data["order1"]

    service = ServiceDuplicationService(db_session)
    new_start = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    new_end = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    duplicated = service.duplicate_single_service(
        source_service_id=source_order.id,
        new_service_start_date=new_start,
        new_service_end_date=new_end,
        folio_prefix="MENS",
        observations="Servicio mensual de septiembre.",
        send_email=False
    )

    assert duplicated is not None
    assert duplicated.id != source_order.id
    assert duplicated.folio.startswith("MENS-ORD-")
    assert duplicated.service_start_date.replace(tzinfo=timezone.utc) == new_start
    assert duplicated.service_end_date.replace(tzinfo=timezone.utc) == new_end
    assert duplicated.observations == "Servicio mensual de septiembre."
    assert duplicated.pest_crawling_insects == source_order.pest_crawling_insects
    assert duplicated.pest_rodents == source_order.pest_rodents

    # Verificar certificado
    assert duplicated.certificate is not None
    assert duplicated.certificate.id != data["cert1"].id
    assert duplicated.certificate.certificate_folio.startswith("MENS-CERT-")
    assert duplicated.certificate.validity_start_date == date(2026, 9, 1)
    assert duplicated.certificate.validity_end_date == date(2026, 9, 1) + timedelta(days=30)
    assert duplicated.certificate.sanitary_license_number == data["cert1"].sanitary_license_number

    # Verificar químicos clonados
    assert len(duplicated.certificate.applied_chemicals) == 1
    applied_chem = duplicated.certificate.applied_chemicals[0]
    assert applied_chem.chemical_id == data["chem"].id
    assert applied_chem.treated_zones_description == "Áreas de urgencias y pasillos"


def test_generate_monthly_batch_for_client(db_session):
    data = seed_test_data(db_session)
    client_corp = data["client"]

    service = ServiceDuplicationService(db_session)
    target_d = date(2026, 9, 15)

    result = service.generate_monthly_batch_for_client(
        client_id=client_corp.id,
        target_date=target_d,
        service_start_time="08:30:00",
        service_duration_hours=2,
        mode="clone_last_service",
        folio_prefix="IMSS-SEP",
        send_emails=False
    )

    assert result["client_id"] == client_corp.id
    assert result["total_branches_processed"] == 2
    assert result["orders_created_count"] == 2
    assert result["certificates_created_count"] == 2
    assert len(result["created_orders"]) == 2

    # Verificar que ambas sucursales tengan su nueva orden
    branch_names = [o["branch_name"] for o in result["created_orders"]]
    assert "HGZ No. 1 Gabriel Mancera" in branch_names
    assert "UMF No. 22 San Jerónimo" in branch_names

    for o in result["created_orders"]:
        assert o["order_folio"].startswith("IMSS-SEP-ORD-")
        assert o["certificate_folio"].startswith("IMSS-SEP-CERT-")
        assert o["validity_start_date"] == "2026-09-15"
        assert o["validity_end_date"] == str(date(2026, 9, 15) + timedelta(days=30))


def test_pdf_generation_and_email_service(db_session):
    data = seed_test_data(db_session)
    order = data["order1"]
    cert = data["cert1"]

    # Generar PDF con ReportLab
    pdf_bytes = OfficialCertificatePDFGenerator.generate(order, cert)
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")

    # Enviar Email simulado
    email_res = OfficialCertificateEmailService.send_certificate_email(
        order=order,
        cert=cert,
        pdf_bytes=pdf_bytes,
        recipient_email="contacto@imss.gob.mx",
        additional_notes="Prueba de envío de certificado."
    )
    assert email_res["success"] is True
    assert email_res["recipient"] == "contacto@imss.gob.mx"
    assert email_res["folio"] == cert.certificate_folio


def test_api_duplicate_endpoint(client, db_session):
    data = seed_test_data(db_session)
    source_order_id = str(data["order1"].id)

    response = client.post(
        f"/api/v1/services/{source_order_id}/duplicate",
        json={
            "folio_prefix": "DUP",
            "observations": "Duplicado vía API",
            "send_email": False
        }
    )

    assert response.status_code == 201
    res_data = response.json()
    assert res_data["id"] != source_order_id
    assert res_data["folio"].startswith("DUP-ORD-")
    assert res_data["certificate"]["certificate_folio"].startswith("DUP-CERT-")


def test_api_send_email_endpoint(client, db_session):
    data = seed_test_data(db_session)
    order_id = str(data["order1"].id)

    response = client.post(
        f"/api/v1/services/{order_id}/send-email",
        json={
            "recipient_email": "responsable@hospital.gob.mx",
            "additional_notes": "Envío de certificado mensual."
        }
    )

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["recipient"] == "responsable@hospital.gob.mx"


def test_api_monthly_batch_endpoint(client, db_session):
    data = seed_test_data(db_session)
    client_id = str(data["client"].id)

    response = client.post(
        f"/api/v1/clients/{client_id}/generate-monthly-batch",
        json={
            "client_id": client_id,
            "target_date": "2026-10-01",
            "service_start_time": "09:00:00",
            "mode": "clone_last_service",
            "folio_prefix": "OCT",
            "send_emails": False
        }
    )

    assert response.status_code == 201
    res_data = response.json()
    assert res_data["orders_created_count"] == 2
    assert res_data["certificates_created_count"] == 2
    assert len(res_data["created_orders"]) == 2
