import io
import uuid
import base64
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import (
    load_der_private_key, load_pem_private_key
)
from cryptography.x509.oid import NameOID, ExtensionOID
from sqlalchemy.orm import Session

from app.models import CompanySettings, Certificate, ServiceOrder, Branch, Client

logger = logging.getLogger(__name__)


class FielSATService:
    @staticmethod
    def extract_serial_number(cert: x509.Certificate) -> str:
        """
        Extrae el número de serie oficial del SAT.
        En certificados del SAT, el serial number X509 entero corresponde a caracteres ASCII
        (ej. bytes b'30001000000500003416').
        """
        serial_int = cert.serial_number
        try:
            # Convertir a bytes y decodificar como ASCII
            hex_str = hex(serial_int)[2:]
            if len(hex_str) % 2 != 0:
                hex_str = '0' + hex_str
            serial_bytes = bytes.fromhex(hex_str)
            decoded = serial_bytes.decode('ascii')
            if decoded.isalnum():
                return decoded
        except Exception:
            pass
        return str(serial_int)

    @staticmethod
    def extract_certificate_info(cert_bytes: bytes) -> Dict[str, Any]:
        """Extrae metadatos y valida la estructura de un certificado X.509 (.cer) del SAT."""
        try:
            # Probar carga DER (formato estándar SAT) o PEM
            try:
                cert = x509.load_der_x509_certificate(cert_bytes)
            except Exception:
                cert = x509.load_pem_x509_certificate(cert_bytes)

            serial_number = FielSATService.extract_serial_number(cert)
            valid_from = cert.not_valid_before_utc
            valid_to = cert.not_valid_after_utc

            # Extraer titular / CN y OIDs de SAT si están presentes
            holder_name = None
            rfc = None

            for attr in cert.subject:
                if attr.oid == NameOID.COMMON_NAME:
                    holder_name = attr.value
                elif attr.oid == NameOID.ORGANIZATION_NAME and not holder_name:
                    holder_name = attr.value
                elif attr.oid.dotted_string == "2.5.4.45":  # OID habitual de RFC en SAT
                    rfc = attr.value

            # Si el RFC no vino en OID específico, buscar en Subject o CN
            if not rfc and holder_name:
                parts = holder_name.split('/')
                for p in parts:
                    clean_p = p.strip().upper()
                    if len(clean_p) in (12, 13) and clean_p.isalnum():
                        rfc = clean_p
                        break

            now = datetime.now(timezone.utc)
            is_valid_date = (valid_from <= now <= valid_to)

            return {
                "success": True,
                "serial_number": serial_number,
                "holder_name": holder_name or "Titular e.firma SAT",
                "rfc": rfc or "RFC_FIEL",
                "valid_from": valid_from,
                "valid_to": valid_to,
                "is_expired": not is_valid_date
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Certificado .cer inválido o corrupto: {str(e)}"
            }

    @staticmethod
    def validate_and_load_private_key(key_bytes: bytes, password: str) -> Any:
        """Carga y descifra la llave privada (.key) del SAT en formato DER o PEM (PKCS#8)."""
        pwd_bytes = password.encode('utf-8') if password else None
        try:
            # 1. Intentar DER (formato estándar SAT)
            return load_der_private_key(key_bytes, password=pwd_bytes)
        except Exception:
            pass

        try:
            # 2. Intentar PEM
            return load_pem_private_key(key_bytes, password=pwd_bytes)
        except Exception as ex:
            raise ValueError(f"Contraseña de la clave privada incorrecta o archivo .key corrupto: {str(ex)}")

    @staticmethod
    def verify_key_pair(cert_bytes: bytes, private_key: Any) -> bool:
        """Verifica criptográficamente que la llave privada corresponda al certificado público."""
        try:
            try:
                cert = x509.load_der_x509_certificate(cert_bytes)
            except Exception:
                cert = x509.load_pem_x509_certificate(cert_bytes)

            public_key = cert.public_key()
            test_data = b"FUMIFLOSA_VERIFICATION_TEST_FIEL"

            # Firmar con la llave privada
            signature = private_key.sign(
                test_data,
                padding.PKCS1v15(),
                hashes.SHA256()
            )

            # Verificar con la llave pública
            public_key.verify(
                signature,
                test_data,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False

    @staticmethod
    def get_or_create_company_settings(db: Session) -> CompanySettings:
        """Obtiene la configuración única de empresa o crea una por defecto."""
        settings = db.query(CompanySettings).first()
        if not settings:
            settings = CompanySettings(
                company_name="FUMIFLOSA - CONTROL INTEGRAL DE PLAGAS",
                company_rfc="FUM200101XYZ",
                sanitary_license_number="2023-15A-099",
                sanitary_responsible_name="Biól. Roberto Sánchez Martínez",
                sanitary_responsible_id="CED-8849201"
            )
            db.add(settings)
            db.commit()
            db.refresh(settings)
        return settings

    @staticmethod
    def build_original_chain(cert: Certificate, order: ServiceOrder, company_rfc: str) -> str:
        """
        Construye la Cadena Original normalizada bajo estándares del SAT / NOM-256.
        Estructura: ||1.0|CERT_FOLIO|ORDER_FOLIO|ISSUE_DATE|VALIDITY_START|VALIDITY_END|COMPANY_RFC|CLIENT_RFC|BRANCH_NAME|CHEMICALS||
        """
        chemicals_desc = []
        if cert.applied_chemicals:
            for item in cert.applied_chemicals:
                chem_name = item.chemical.commercial_name if item.chemical else "Químico"
                cicoplafest = item.chemical.cicoplafest_number if item.chemical else "N/A"
                chemicals_desc.append(f"{chem_name}({cicoplafest}):{item.dose_applied}:{item.treated_zones_description}")
        
        chem_str = ";".join(chemicals_desc) if chemicals_desc else "TRATAMIENTO_ESTANDAR"
        branch_name = order.branch.name if order.branch else "SUCURSAL"
        client_rfc = order.branch.client.rfc if order.branch and order.branch.client else "XAXX010101000"

        chain_parts = [
            "1.0",
            cert.certificate_folio,
            order.folio,
            cert.issue_date.isoformat(),
            cert.validity_start_date.isoformat(),
            cert.validity_end_date.isoformat(),
            company_rfc.upper(),
            cert.sanitary_license_number,
            cert.sanitary_responsible_name,
            cert.sanitary_responsible_id or "NO_CEDULA",
            client_rfc.upper(),
            branch_name,
            chem_str
        ]
        return "||" + "|".join(chain_parts) + "||"

    @classmethod
    def sign_certificate(
        cls,
        db: Session,
        certificate_id: uuid.UUID,
        override_password: Optional[str] = None,
        private_key_password: Optional[str] = None
    ) -> Certificate:
        """
        Firma manualmente un certificado de servicio usando la e.firma / FIEL del SAT guardada.
        Genera la Cadena Original, el Sello Digital RSA-SHA256 en Base64 y actualiza el estado a Firmado.
        """
        cert = db.query(Certificate).filter(Certificate.id == certificate_id, Certificate.is_deleted == False).first()
        if not cert:
            raise ValueError("Certificado no encontrado.")

        order = cert.service_order
        if not order:
            raise ValueError("Orden de servicio asociada no encontrada.")

        company = cls.get_or_create_company_settings(db)
        if not company.is_fiel_active or not company.fiel_certificate_der or not company.fiel_private_key_der:
            raise ValueError("La empresa no tiene configurada o activa la FIEL / e.firma del SAT. Configúrela en el módulo de Empresa.")

        pwd = override_password or private_key_password
        if not pwd:
            raise ValueError("Debe ingresar la contraseña de la llave privada (.key) para autorizar y estampar la firma manual.")

        # Cargar y verificar llave privada con la contraseña suministrada
        private_key = cls.validate_and_load_private_key(company.fiel_private_key_der, pwd)
        if not cls.verify_key_pair(company.fiel_certificate_der, private_key):
            raise ValueError("La contraseña es incorrecta o la llave privada no corresponde al certificado activo.")

        # Generar Cadena Original
        original_chain = cls.build_original_chain(cert, order, company.company_rfc)

        # Generar Sello Digital RSA-SHA256
        signature_bytes = private_key.sign(
            original_chain.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        digital_seal = base64.b64encode(signature_bytes).decode('ascii')

        # Estampar firma en el certificado
        cert.is_signed = True
        cert.signed_at = datetime.now(timezone.utc)
        cert.digital_signature_seal = digital_seal
        cert.certificate_serial_number = company.fiel_serial_number or "30001000000500003416"
        cert.original_chain = original_chain
        cert.signed_by_name = company.fiel_holder_name or company.company_name
        cert.signed_by_rfc = company.fiel_rfc or company.company_rfc
        cert.verification_uuid = str(uuid.uuid4())

        db.commit()
        db.refresh(cert)
        return cert
