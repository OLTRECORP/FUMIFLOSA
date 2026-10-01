import io
import uuid
import pytest
from datetime import datetime, date, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding

from app.database import get_db
from app.models import (
    Base, User, UserRole, Client, Branch, BranchClassification,
    Chemical, ServiceOrder, Certificate, CertificateChemical, AreaType, CompanySettings
)
from app.main import app
from app.services.fiel_service import FielSATService
from app.services.pdf_service import OfficialCertificatePDFGenerator

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


def generate_mock_fiel_pair(password: str = "satPassword2026"):
    """Genera un par de llaves y certificado X.509 simulando una FIEL del SAT en formato DER."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    
    # Nombre del sujeto con formato SAT RFC + Razón Social
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "MX"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "FUMIFLOSA SA DE CV"),
        x509.NameAttribute(NameOID.COMMON_NAME, "FUM190101XYZ FUMIFLOSA SA DE CV"),
    ])
    
    # Número de serie representable como ASCII en SAT: b"30001000000500003416"
    serial_str = "30001000000500003416"
    serial_int = int.from_bytes(serial_str.encode('ascii'), byteorder='big')
    
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(serial_int)
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1460))
        .sign(private_key, hashes.SHA256())
    )
    
    cert_der = cert.public_bytes(serialization.Encoding.DER)
    
    key_der = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(password.encode("utf-8"))
    )
    
    return cert_der, key_der, private_key, cert


def seed_fiel_test_data(db):
    """Crea datos iniciales con orden y certificado para pruebas de firma."""
    tech = User(
        id=uuid.uuid4(),
        email="tecnico@fumiflosa.mx",
        full_name="Técnico Certificado STPS",
        hashed_password="hash_password123",
        role=UserRole.TECNICO_CAMPO
    )
    db.add(tech)

    client_corp = Client(
        id=uuid.uuid4(),
        legal_name="HOTEL GRAN CARIBE S.A. DE C.V.",
        rfc="HGC8505128B4"
    )
    db.add(client_corp)

    branch = Branch(
        id=uuid.uuid4(),
        client_id=client_corp.id,
        name="Sucursal Principal Cancún",
        address="Blvd. Kukulcan Km 12.5, Cancún, Q.R.",
        phone="9981234567",
        responsible_contact_name="Lic. Roberto Cancún",
        responsible_contact_email="roberto@cancunhotel.com",
        classification=BranchClassification.COMERCIAL
    )
    db.add(branch)
    db.commit()

    chem = Chemical(
        id=uuid.uuid4(),
        commercial_name="Maxforce Gel",
        active_ingredient="Hydramethylnon 2.15%",
        cicoplafest_number="RSCO-URB-INAC-112-2021",
        authorized_dose_per_liter="Puntos de 0.5g",
        safety_interval_hours=0,
        compatible_methods="Cebo en Gel",
        toxicological_category="Precaución"
    )
    db.add(chem)
    db.commit()

    start_dt = datetime(2026, 10, 1, 9, 0, 0, tzinfo=timezone.utc)
    order = ServiceOrder(
        id=uuid.uuid4(),
        folio="FF-ORD-2026-0010",
        branch_id=branch.id,
        technician_id=tech.id,
        service_start_date=start_dt,
        service_end_date=start_dt + timedelta(hours=2),
        pest_crawling_insects=True,
        proc_baits=True,
        results_summary="Control preventivo de cucarachas en cocina general."
    )
    db.add(order)
    db.flush()

    cert = Certificate(
        id=uuid.uuid4(),
        service_order_id=order.id,
        certificate_folio="FF-CERT-2026-0010",
        issue_date=start_dt.date(),
        validity_start_date=start_dt.date(),
        validity_end_date=start_dt.date() + timedelta(days=30),
        sanitary_license_number="2024-23A-888",
        sanitary_responsible_name="Dr. Alejandro Flota Morales",
        sanitary_responsible_id="CED-9938120"
    )
    db.add(cert)
    db.flush()

    cert_chem = CertificateChemical(
        id=uuid.uuid4(),
        certificate_id=cert.id,
        chemical_id=chem.id,
        dose_applied="Puntos de 0.5g cada 2 metros",
        area_type=AreaType.INTERIOR,
        treated_zones_description="Cocinas y alacenas",
        application_method="Aplicación con pistola dosificadora"
    )
    db.add(cert_chem)
    db.commit()

    return {
        "tech": tech,
        "client": client_corp,
        "branch": branch,
        "chem": chem,
        "order": order,
        "cert": cert
    }


def test_fiel_sat_service_crypto_operations(db_session):
    cert_der, key_der, private_key, cert_obj = generate_mock_fiel_pair("MiClaveSAT123")

    # 1. Extraer info
    info = FielSATService.extract_certificate_info(cert_der)
    assert info["serial_number"] != ""
    assert "FUMIFLOSA" in info["holder_name"]
    assert info["is_expired"] is False

    # 2. Cargar clave privada
    loaded_key = FielSATService.validate_and_load_private_key(key_der, "MiClaveSAT123")
    assert loaded_key is not None

    # 3. Contraseña incorrecta falla
    with pytest.raises(ValueError, match="Contraseña de la clave privada incorrecta"):
        FielSATService.validate_and_load_private_key(key_der, "PasswordEquivocada")

    # 4. Verificar par
    assert FielSATService.verify_key_pair(cert_der, loaded_key) is True


def test_sign_certificate_and_verify_signature(db_session):
    data = seed_fiel_test_data(db_session)
    cert = data["cert"]
    cert_der, key_der, _, _ = generate_mock_fiel_pair("ClaveFirma2026")

    # Guardar en CompanySettings
    settings = FielSATService.get_or_create_company_settings(db_session)
    info = FielSATService.extract_certificate_info(cert_der)
    settings.fiel_certificate_der = cert_der
    settings.fiel_private_key_der = key_der
    settings.fiel_serial_number = info["serial_number"]
    settings.fiel_valid_from = info["valid_from"]
    settings.fiel_valid_to = info["valid_to"]
    settings.fiel_rfc = info["rfc"]
    settings.fiel_holder_name = info["holder_name"]
    settings.is_fiel_active = True
    db_session.commit()

    # Firmar
    signed_cert = FielSATService.sign_certificate(
        db=db_session,
        certificate_id=cert.id,
        private_key_password="ClaveFirma2026"
    )

    assert signed_cert.is_signed is True
    assert signed_cert.signed_at is not None
    assert signed_cert.digital_signature_seal is not None
    assert len(signed_cert.digital_signature_seal) > 30
    assert signed_cert.original_chain.startswith("||1.0|")
    assert signed_cert.certificate_serial_number == info["serial_number"]
    assert signed_cert.signed_by_name == info["holder_name"]
    assert signed_cert.signed_by_rfc == info["rfc"]

    # Verificar matemáticamente la firma usando la clave pública del certificado
    import base64
    x509_cert = x509.load_der_x509_certificate(cert_der)
    public_key = x509_cert.public_key()
    raw_signature = base64.b64decode(signed_cert.digital_signature_seal)
    
    # Debe pasar la verificación sin excepción
    public_key.verify(
        raw_signature,
        signed_cert.original_chain.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256()
    )


def test_api_company_settings_and_fiel_upload_workflow(client, db_session):
    cert_der, key_der, _, _ = generate_mock_fiel_pair("SecretFiel2026")

    # 1. Obtener settings iniciales
    res_get = client.get("/api/v1/company/settings")
    assert res_get.status_code == 200
    assert "FUMIFLOSA" in res_get.json()["company_name"]

    # 2. Actualizar configuración de empresa
    res_put = client.put(
        "/api/v1/company/settings",
        json={
            "company_name": "FUMIFLOSA CONTROL INTEGRAL S.A. DE C.V.",
            "company_rfc": "FCI200101AA1",
            "sanitary_license_number": "2026-COFEPRIS-091",
            "sanitary_responsible_name": "Dr. Carlos Sanitario",
            "sanitary_responsible_id": "CED-123456"
        }
    )
    assert res_put.status_code == 200
    assert res_put.json()["company_name"] == "FUMIFLOSA CONTROL INTEGRAL S.A. DE C.V."

    # 3. Subir FIEL SAT (.cer, .key, password)
    files = {
        "certificate_file": ("fiel.cer", io.BytesIO(cert_der), "application/x-x509-ca-cert"),
        "private_key_file": ("fiel.key", io.BytesIO(key_der), "application/octet-stream")
    }
    data = {"password": "SecretFiel2026"}

    res_upload = client.post("/api/v1/company/fiel/upload", files=files, data=data)
    assert res_upload.status_code == 200
    upload_json = res_upload.json()
    assert upload_json["is_active"] is True
    assert upload_json["serial_number"] != ""

    # 4. Consultar estado FIEL
    res_fiel = client.get("/api/v1/company/fiel")
    assert res_fiel.status_code == 200
    assert res_fiel.json()["is_active"] is True


def test_api_sign_certificate_and_verification(client, db_session):
    data = seed_fiel_test_data(db_session)
    cert = data["cert"]
    cert_der, key_der, _, _ = generate_mock_fiel_pair("PassSign999")

    # Subir FIEL vía API
    files = {
        "certificate_file": ("fiel.cer", io.BytesIO(cert_der), "application/x-x509-ca-cert"),
        "private_key_file": ("fiel.key", io.BytesIO(key_der), "application/octet-stream")
    }
    res_up = client.post("/api/v1/company/fiel/upload", files=files, data={"password": "PassSign999"})
    assert res_up.status_code == 200

    # 1. Firmar con contraseña incorrecta -> 400
    res_bad_pass = client.post(
        f"/api/v1/certificates/{cert.id}/sign",
        json={"password": "ContraseñaIncorrecta"}
    )
    assert res_bad_pass.status_code == 400
    assert "incorrecta" in res_bad_pass.json()["detail"].lower()

    # 2. Firmar exitosamente -> 200
    res_sign = client.post(
        f"/api/v1/certificates/{cert.id}/sign",
        json={"password": "PassSign999"}
    )
    assert res_sign.status_code == 200
    sign_json = res_sign.json()
    assert sign_json["is_signed"] is True
    assert sign_json["digital_signature_seal"] != ""
    assert sign_json["verification_uuid"] is not None

    # 3. Consultar verificación pública del certificado
    res_verify = client.get(f"/api/v1/certificates/{cert.id}/verification")
    assert res_verify.status_code == 200
    verify_json = res_verify.json()
    assert verify_json["is_signed_digitally"] is True
    assert verify_json["certificate_folio"] == cert.certificate_folio
    assert verify_json["is_valid"] is True


def test_pdf_generation_with_signed_seal(db_session):
    data = seed_fiel_test_data(db_session)
    order = data["order"]
    cert = data["cert"]
    cert_der, key_der, _, _ = generate_mock_fiel_pair("PasswordPDF")

    # Configurar y firmar
    settings = FielSATService.get_or_create_company_settings(db_session)
    info = FielSATService.extract_certificate_info(cert_der)
    settings.fiel_certificate_der = cert_der
    settings.fiel_private_key_der = key_der
    settings.fiel_serial_number = info["serial_number"]
    settings.is_fiel_active = True
    db_session.commit()

    FielSATService.sign_certificate(db_session, cert.id, "PasswordPDF")
    db_session.refresh(cert)

    # Generar PDF con sello digital y QR
    pdf_bytes = OfficialCertificatePDFGenerator.generate(order, cert)
    assert pdf_bytes is not None
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000
