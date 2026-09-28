import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Optional, List, Dict, Any

from app.config import settings
from app.models import ServiceOrder, Certificate

logger = logging.getLogger(__name__)


class OfficialCertificateEmailService:
    @staticmethod
    def send_certificate_email(
        order: ServiceOrder,
        cert: Certificate,
        pdf_bytes: bytes,
        recipient_email: str,
        additional_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envía por correo electrónico el Certificado Oficial NOM-256 adjunto en PDF
        a la dirección de correo indicada o al responsable de la sucursal.
        """
        if not recipient_email or not recipient_email.strip():
            return {
                "success": False,
                "error": "No se proporcionó una dirección de correo electrónico válida."
            }

        recipient_email = recipient_email.strip()
        branch_name = order.branch.name if order.branch else "Unidad Operativa"
        client_name = order.branch.client.legal_name if order.branch and order.branch.client else "Cliente Corporativo"
        cert_folio = cert.certificate_folio
        order_folio = order.folio

        subject = f"Certificado Oficial de Fumigación NOM-256 - {cert_folio} - {branch_name}"

        # Plantilla HTML con estilo profesional FUMIFLOSA
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; color: #1e293b; }}
                .card {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; }}
                .header {{ background: #0f172a; color: #ffffff; padding: 24px; text-align: center; border-bottom: 4px solid #16a34a; }}
                .header h1 {{ margin: 0; font-size: 20px; letter-spacing: 0.5px; }}
                .header p {{ margin: 5px 0 0 0; font-size: 12px; color: #94a3b8; }}
                .badge {{ display: inline-block; background: #15803d; color: #ffffff; font-size: 11px; font-weight: bold; padding: 3px 10px; border-radius: 20px; margin-top: 8px; }}
                .content {{ padding: 24px; font-size: 14px; line-height: 1.6; }}
                .info-table {{ width: 100%; border-collapse: collapse; margin: 16px 0; background: #f8fafc; border-radius: 8px; overflow: hidden; }}
                .info-table td {{ padding: 10px 14px; font-size: 13px; border-bottom: 1px solid #e2e8f0; }}
                .info-table td.label {{ font-weight: bold; color: #475569; width: 40%; }}
                .info-table td.value {{ color: #0f172a; font-weight: 500; }}
                .alert-box {{ background: #eff6ff; border-left: 4px solid #2563eb; padding: 12px 16px; border-radius: 4px; margin: 16px 0; font-size: 13px; color: #1e40af; }}
                .footer {{ background: #f1f5f9; padding: 16px; text-align: center; font-size: 11px; color: #64748b; border-top: 1px solid #e2e8f0; }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="header">
                    <h1>FUMIFLOSA</h1>
                    <p>Servicios Especializados de Control de Plagas Urbanas</p>
                    <div class="badge">NOM-256-SSA1-2012 / COFEPRIS</div>
                </div>
                <div class="content">
                    <p>Estimado/a cliente <strong>{client_name}</strong>,</p>
                    <p>Le informamos que se ha generado y registrado exitosamente el <strong>Certificado Oficial de Servicio de Control de Plagas</strong> correspondiente a su unidad:</p>
                    
                    <table class="info-table">
                        <tr>
                            <td class="label">Folio Certificado:</td>
                            <td class="value"><strong>{cert_folio}</strong></td>
                        </tr>
                        <tr>
                            <td class="label">Orden de Servicio:</td>
                            <td class="value">{order_folio}</td>
                        </tr>
                        <tr>
                            <td class="label">Unidad / Sucursal:</td>
                            <td class="value">{branch_name}</td>
                        </tr>
                        <tr>
                            <td class="label">Fecha de Aplicación:</td>
                            <td class="value">{cert.issue_date.strftime('%d/%m/%Y')}</td>
                        </tr>
                        <tr>
                            <td class="label">Vigencia Oficial (30 días):</td>
                            <td class="value"><span style="color: #16a34a; font-weight: bold;">{cert.validity_start_date.strftime('%d/%m/%Y')} al {cert.validity_end_date.strftime('%d/%m/%Y')}</span></td>
                        </tr>
                        <tr>
                            <td class="label">Licencia Sanitaria:</td>
                            <td class="value">{cert.sanitary_license_number}</td>
                        </tr>
                        <tr>
                            <td class="label">Responsable Sanitario:</td>
                            <td class="value">{cert.sanitary_responsible_name}</td>
                        </tr>
                    </table>

                    {f'<div class="alert-box"><strong>Nota adicional:</strong> {additional_notes}</div>' if additional_notes else ''}

                    <p>Adjunto a este correo encontrará el documento PDF oficial del Certificado con validez ante COFEPRIS, Protección Civil y autoridades sanitarias correspondientes.</p>
                </div>
                <div class="footer">
                    <p>Centro de Atención de Emergencias Toxicológicas <strong>SINTOX: 01-800-0092800</strong> (24 horas)</p>
                    <p>FUMIFLOSA &copy; 2026 - Control Integral de Plagas</p>
                </div>
            </div>
        </body>
        </html>
        """

        plain_text = (
            f"FUMIFLOSA - Certificado Oficial de Servicio NOM-256\n"
            f"Folio: {cert_folio}\n"
            f"Orden: {order_folio}\n"
            f"Unidad: {branch_name}\n"
            f"Vigencia: {cert.validity_start_date.strftime('%d/%m/%Y')} al {cert.validity_end_date.strftime('%d/%m/%Y')}\n\n"
            f"El certificado oficial en PDF ha sido adjuntado a este correo."
        )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = recipient_email

        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        # Adjuntar PDF
        pdf_attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
        pdf_filename = f"Certificado_{cert_folio}.pdf"
        pdf_attachment.add_header("Content-Disposition", "attachment", filename=pdf_filename)
        msg.attach(pdf_attachment)

        # Si las credenciales SMTP no están configuradas (por ejemplo en entorno dev/test), simulamos y registramos
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.info(
                f"[SIMULACIÓN EMAIL] Certificado {cert_folio} enviado virtualmente a {recipient_email}. "
                f"Para envío real en producción, configure las variables SMTP_USER y SMTP_PASSWORD."
            )
            return {
                "success": True,
                "recipient": recipient_email,
                "folio": cert_folio,
                "mode": "simulated",
                "message": f"Certificado enviado virtualmente a {recipient_email} (Modo desarrollo / Sandbox)."
            }

        # Envío real vía SMTP
        try:
            if settings.SMTP_PORT == 465:
                server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
            else:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
                if settings.SMTP_TLS:
                    server.starttls()
            
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, [recipient_email], msg.as_string())
            server.quit()

            logger.info(f"[EMAIL ENVIADO] Certificado {cert_folio} enviado exitosamente a {recipient_email}")
            return {
                "success": True,
                "recipient": recipient_email,
                "folio": cert_folio,
                "mode": "smtp_live",
                "message": f"Certificado enviado exitosamente a {recipient_email}."
            }

        except Exception as e:
            logger.error(f"[ERROR SMTP] Error al enviar correo a {recipient_email}: {str(e)}")
            return {
                "success": False,
                "recipient": recipient_email,
                "folio": cert_folio,
                "error": f"Error SMTP al enviar correo: {str(e)}"
            }
