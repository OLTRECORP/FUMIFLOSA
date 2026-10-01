import io
import os
from datetime import date, datetime
from typing import Optional, Any, List, Dict
from pathlib import Path

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas

from app.models import ServiceOrder, Certificate, CompanyConfig


ASSETS_DIR = Path(__file__).parent.parent / "assets" / "certificates"
FRAME_PATH = ASSETS_DIR / "border_frame.png"
WATERMARK_PATH = ASSETS_DIR / "watermark_flosa.png"
LOGO_PATH = ASSETS_DIR / "logo_flosa.png"
SIGNATURE_PATH = ASSETS_DIR / "signature_mafs.png"


def _safe_str(val: Any, default: str = "") -> str:
    """Extrae de forma segura el valor en cadena de texto sin fallar por Enums o None."""
    if val is None:
        return default
    if hasattr(val, "value"):
        return str(val.value)
    return str(val)


class OfficialCertificatePDFGenerator:
    """
    Generador del Certificado Oficial de Servicio de Control de Plagas.
    Replica con total exactitud visual el formato oficial histórico de FLOSA:
    - Formato Carta Horizontal (Landscape Letter: 792 x 612 pt)
    - Marco ornamental clásico en tonos verde salvia
    - Marca de agua central tenue con escudo FLOSA
    - Tipografía y jerarquía visual oficial de certificación NOM-256
    - Tabla estructurada de hasta 4 químicos / ingredientes activos aplicados
    - Cuadro de recomendaciones de seguridad y tiempo de reentrada al cliente
    - Bloque de firmas con firma digitalizada del Responsable Técnico y Licencia Sanitaria
    - Recuadro de emergencias toxicológicas SINTOX 24 Horas
    - Marca de agua y cinta de alerta 'CANCELADO' en caso de certificado cancelado
    """

    @classmethod
    def generate(cls, order: ServiceOrder, cert: Certificate, company: Optional[CompanyConfig] = None) -> bytes:
        try:
            return cls._generate_canvas(order, cert, company)
        except Exception as err:
            import traceback
            traceback.print_exc()
            return cls._generate_fallback(order, cert, company, str(err))

    @classmethod
    def _generate_canvas(cls, order: ServiceOrder, cert: Certificate, company: Optional[CompanyConfig] = None) -> bytes:
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=landscape(letter))
        page_width, page_height = landscape(letter)  # 792.0 x 612.0

        # 1. MARCO ORNAMENTAL HISTÓRICO
        if FRAME_PATH.exists():
            c.drawImage(str(FRAME_PATH), 8.25, 14.25, width=775.5, height=585.0, mask='auto')
        else:
            c.setStrokeColor(colors.HexColor("#738C7B"))
            c.setLineWidth(3)
            c.rect(20, 20, page_width - 40, page_height - 40)
            c.setLineWidth(0.8)
            c.rect(25, 25, page_width - 50, page_height - 50)

        # 2. ENCABEZADO CENTRADO (FORMATO EXACTO WORD)
        c.setFont("Times-Bold", 23)
        c.setFillColor(colors.HexColor("#435D40"))
        c.drawCentredString(396, 508, "CERTIFICADO DE SERVICIO")

        c.setFont("Times-BoldItalic", 9)
        c.setFillColor(colors.HexColor("#111111"))
        
        responsible_title = getattr(company, 'company_name', None) or "Marco Antonio Flores Sáenz (FLOSA Control de Plagas)"
        c.drawCentredString(396, 484, responsible_title)
        
        comp_rfc = getattr(company, 'rfc', None) or "FOMS630329EA5"
        comp_tel = getattr(company, 'phone', None) or "6258373393"
        c.drawCentredString(396, 472, f"{comp_rfc}    Tel: {comp_tel}")
        
        comp_address = getattr(company, 'address', None) or "C10a 685 Col. Centro, Cd. Cuauhtémoc, Chih C.P. 31500"
        c.drawCentredString(396, 460, comp_address)

        # 3. FOLIO Y FECHA (ALINEADOS A LA DERECHA)
        folio_str = getattr(cert, 'certificate_folio', None) or (f"B/{order.folio}" if order and getattr(order, 'folio', None) else "B/00001")
        issue_date_val = getattr(cert, 'issue_date', None) or (getattr(order, 'service_start_date', None).date() if order and getattr(order, 'service_start_date', None) else date.today())
        issue_str = issue_date_val.strftime("%d/%m/%y") if issue_date_val else date.today().strftime("%d/%m/%y")

        c.setFont("Times-BoldItalic", 9.5)
        c.setFillColor(colors.HexColor("#111111"))
        c.drawRightString(706, 442, f"Folio:    {folio_str}")
        c.drawRightString(706, 428, f"Fecha De Expedición:   {issue_str}")

        # 4. DATOS DEL CLIENTE Y LUGAR DE SERVICIO
        branch = getattr(order, 'branch', None) if order else None
        client = getattr(branch, 'client', None) if branch else None

        client_name = _safe_str(getattr(client, 'legal_name', None) or "CLIENTE GENERAL").upper()
        branch_name = _safe_str(getattr(branch, 'name', None) or "").upper()
        branch_addr = _safe_str(getattr(branch, 'address', None) or "DOMICILIO CONOCIDO").upper()
        branch_class = _safe_str(getattr(branch, 'classification', None) or "COMERCIAL").upper()

        client_display = client_name
        lugar_display = branch_name or branch_class
        
        # Plagas a controlar
        pests_list = []
        if order:
            if getattr(order, 'pest_crawling_insects', False):
                pests_list.append("INSECTOS RASTREROS")
            if getattr(order, 'pest_flying_insects', False):
                pests_list.append("INSECTOS VOLADORES")
            if getattr(order, 'pest_rodents', False):
                pests_list.append("ROEDORES")
            if getattr(order, 'pest_others', None):
                pests_list.append(_safe_str(order.pest_others).upper())
        pests_text = ", ".join(pests_list) if pests_list else "TODO TIPO DE INSECTOS RASTREROS"

        styles = getSampleStyleSheet()
        client_label_style = ParagraphStyle(
            'ClientLabel',
            parent=styles['Normal'],
            fontName='Times-Bold',
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#111111")
        )
        client_val_style = ParagraphStyle(
            'ClientVal',
            parent=styles['Normal'],
            fontName='Times-Bold',
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#111111")
        )

        client_rows = [
            [
                Paragraph("<b>Nombre Del Cliente:</b>", client_label_style),
                Paragraph(client_display, client_val_style)
            ],
            [
                Paragraph("<b>Dirección:</b>", client_label_style),
                Paragraph(branch_addr, client_val_style)
            ],
            [
                Paragraph("<b>Lugar De Servicio:</b>", client_label_style),
                Paragraph(lugar_display, client_val_style)
            ],
            [
                Paragraph("<b>Plagas a controlar:</b>", client_label_style),
                Paragraph(pests_text, client_val_style)
            ]
        ]
        
        client_table = Table(client_rows, colWidths=[115, 507])
        client_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 1.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        # Render tabla cliente
        client_table.wrapOn(c, 622, 100)
        client_table.drawOn(c, 85, 360)

        # 5. TABLA DE QUÍMICOS / INGREDIENTES ACTIVOS (HASTA 4 LÍNEAS - FORMATO WORD)
        chem_hdr_style = ParagraphStyle(
            'ChemHdr',
            parent=styles['Normal'],
            fontName='Times-Bold',
            fontSize=8.5,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#111111")
        )
        chem_cell_style = ParagraphStyle(
            'ChemCell',
            parent=styles['Normal'],
            fontName='Times-Roman',
            fontSize=8.5,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#111111")
        )

        chem_data = [
            [
                Paragraph("<b>Ingrediente Activo</b>", chem_hdr_style),
                Paragraph("<b>Registro CICOPLAFEST</b>", chem_hdr_style),
                Paragraph("<b>Dosis / Litro</b>", chem_hdr_style),
                Paragraph("<b>Lugar Tratado</b>", chem_hdr_style),
                Paragraph("<b>Método de Aplicación</b>", chem_hdr_style)
            ]
        ]

        applied = list(getattr(cert, 'applied_chemicals', None) or [])
        # Rellenar filas reales
        for item in applied[:4]:
            chem = getattr(item, 'chemical', None)
            act_ing = _safe_str(getattr(chem, 'active_ingredient', None) if chem else '').upper() or "CIPERMETRINA"
            cico = _safe_str(getattr(chem, 'cicoplafest_number', None) if chem else '').upper() or "RSCO-URB-MEZC-111-00-02-40"
            dose = _safe_str(getattr(item, 'dose_applied', None)).upper() or "3 GR/L"
            
            area_str = _safe_str(getattr(item, 'area_type', None)).upper()
            zone_str = _safe_str(getattr(item, 'treated_zones_description', None)).upper()
            treated_loc = f"{area_str}: {zone_str}".strip(" :") if (area_str or zone_str) else "INTERIORES"
            method_str = _safe_str(getattr(item, 'application_method', None)).upper() or "ASPERSION"

            chem_data.append([
                Paragraph(act_ing, chem_cell_style),
                Paragraph(cico, chem_cell_style),
                Paragraph(dose, chem_cell_style),
                Paragraph(treated_loc, chem_cell_style),
                Paragraph(method_str, chem_cell_style)
            ])

        # Rellenar con filas vacías si hay menos de 4 para mantener el formato idéntico de 4 filas
        while len(chem_data) < 5:
            chem_data.append([
                Paragraph("&nbsp;", chem_cell_style),
                Paragraph("&nbsp;", chem_cell_style),
                Paragraph("&nbsp;", chem_cell_style),
                Paragraph("&nbsp;", chem_cell_style),
                Paragraph("&nbsp;", chem_cell_style)
            ])

        chem_table = Table(chem_data, colWidths=[140, 192, 78, 106, 106], rowHeights=[19] * 5)
        chem_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E8EFE7")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#777777")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))

        chem_table.wrapOn(c, 622, 100)
        chem_table.drawOn(c, 85, 250)

        # 6. RECOMENDACIONES AL CLIENTE
        c.setFont("Times-Bold", 9)
        c.setFillColor(colors.HexColor("#111111"))
        c.drawString(85, 234, "Recomendaciones al cliente:")

        rec_style = ParagraphStyle(
            'RecStyle',
            parent=styles['Normal'],
            fontName='Times-Roman',
            fontSize=8,
            leading=10.5,
            alignment=TA_JUSTIFY,
            textColor=colors.HexColor("#111111")
        )
        recommendations_text = (
            "Si al momento de aplicar los productos se encuentran personas o niños retirarlos del lugar como mínimo una hora, "
            "se recomienda colocar este certificado en un lugar visible, la vigencia es de 30 días a partir de la fecha del presente documento. "
            "Para antídotos en caso de contacto o ingestión acudir al medico o llame a SINTOX."
        )

        rec_table = Table([[Paragraph(recommendations_text, rec_style)]], colWidths=[622])
        rec_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#999999")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        rec_table.wrapOn(c, 622, 50)
        rec_table.drawOn(c, 85, 185)

        # 7. PIE DE PÁGINA (3 COLUMNAS: LOGO, FIRMA TÉCNICA, SINTOX)
        # Logo izquierdo
        if LOGO_PATH.exists():
            c.drawImage(str(LOGO_PATH), 85, 75, width=175.0, height=75.0, mask='auto')

        # Firma Centro
        if SIGNATURE_PATH.exists():
            c.drawImage(str(SIGNATURE_PATH), 335, 108, width=125.0, height=50.0, mask='auto')

        c.setStrokeColor(colors.HexColor("#222222"))
        c.setLineWidth(0.8)
        c.line(300, 110, 492, 110)

        c.setFont("Times-Bold", 9)
        c.setFillColor(colors.HexColor("#111111"))
        resp_name = getattr(cert, 'sanitary_responsible_name', None) or (getattr(company, 'sanitary_responsible_name', None) if company else "Marco Antonio Flores Sáenz")
        c.drawCentredString(396, 96, resp_name)
        
        c.drawCentredString(396, 84, "Responsable Técnico")

        license_no = getattr(cert, 'sanitary_license_number', None) or (getattr(company, 'sanitary_license_number', None) if company else "08 17 19 SA 0001")
        c.drawCentredString(396, 72, f"No. De Licencia Sanitaria: {license_no}")

        # Recuadro SINTOX (Derecha)
        sintox_body_style = ParagraphStyle(
            'SintoxBody',
            parent=styles['Normal'],
            fontName='Times-Bold',
            fontSize=6.2,
            leading=8,
            alignment=TA_CENTER
        )

        sintox_content = (
            "<font color='#C53030'><b>EN CASO DE INTOXICACION DE PLAGUICIDAS SINTOX</b></font><br/>"
            "<font color='#111111'>DEL INTERIOR SIN COSTO  01-800-0092800</font><br/>"
            "<font color='#111111'>AREA METROPOLITANA 01(55)5598-6659 Y (55)5611-2634</font><br/>"
            "<font color='#1A56DB'><b>SERVICIO LAS 24 HORAS</b></font>"
        )
        sintox_table = Table([[Paragraph(sintox_content, sintox_body_style)]], colWidths=[204])
        sintox_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor("#C53030")),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#FFFAFA")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        sintox_table.wrapOn(c, 204, 55)
        sintox_table.drawOn(c, 503, 85)

        # 8. MARCA DE AGUA EN CASO DE CANCELACIÓN
        if getattr(cert, 'is_cancelled', False):
            c.saveState()
            c.setFont("Helvetica-Bold", 65)
            c.setFillColor(colors.HexColor("#E53E3E"), alpha=0.35)
            c.translate(396, 306)
            c.rotate(35)
            c.drawCentredString(0, 0, "CANCELADO")
            c.restoreState()

            # Cintillo superior de cancelación
            c.setFillColor(colors.HexColor("#E53E3E"))
            c.rect(75, page_height - 65, page_width - 150, 20, fill=True, stroke=False)
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 8)
            cancel_date_str = cert.cancelled_at.strftime("%d/%m/%Y %H:%M") if cert.cancelled_at else ""
            cancel_msg = f"CERTIFICADO CANCELADO: {cert.cancellation_reason or 'No se llevó a cabo'} ({cancel_date_str})"
            c.drawCentredString(page_width / 2, page_height - 52, cancel_msg[:120])

        c.showPage()
        c.save()
        buffer.seek(0)
        return buffer.getvalue()

    @classmethod
    def _generate_fallback(cls, order: ServiceOrder, cert: Certificate, company: Optional[CompanyConfig], error_msg: str) -> bytes:
        """Genera un certificado de emergencia estructurado en caso de error imprevisto."""
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=landscape(letter))
        w, h = landscape(letter)

        c.setStrokeColor(colors.HexColor("#738C7B"))
        c.setLineWidth(2)
        c.rect(20, 20, w - 40, h - 40)

        c.setFont("Helvetica-Bold", 20)
        c.setFillColor(colors.HexColor("#1E3A2F"))
        c.drawCentredString(w / 2, h - 60, "CERTIFICADO DE SERVICIO DE CONTROL DE PLAGAS")

        c.setFont("Helvetica", 10)
        c.setFillColor(colors.HexColor("#333333"))
        company_name = company.company_name if company else "Marco Antonio Flores Sáenz (FLOSA)"
        c.drawCentredString(w / 2, h - 80, company_name)
        
        folio = getattr(cert, 'certificate_folio', None) or getattr(order, 'folio', 'CERT-OFICIAL')
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, h - 120, f"Folio Certificado: {folio}")
        issue_d = cert.issue_date.strftime("%d/%m/%Y") if (cert and cert.issue_date) else date.today().strftime("%d/%m/%Y")
        c.drawString(550, h - 120, f"Fecha de Emisión: {issue_d}")

        client_name = order.branch.client.legal_name if (order and order.branch and order.branch.client) else "Cliente General"
        branch_name = order.branch.name if (order and order.branch) else "Sucursal Principal"
        branch_addr = order.branch.address if (order and order.branch) else "Domicilio Registrado"

        c.setFont("Helvetica-Bold", 9)
        c.drawString(40, h - 150, "Datos del Establecimiento:")
        c.setFont("Helvetica", 9)
        c.drawString(40, h - 165, f"Razón Social: {client_name} - Sucursal: {branch_name}")
        c.drawString(40, h - 180, f"Dirección: {branch_addr}")

        c.setFont("Helvetica-Bold", 9)
        c.drawString(40, h - 210, "Tratamiento Sanitizado Realizado Conforme a NOM-256-SSA1-2012:")
        c.setFont("Helvetica", 9)
        c.drawString(40, h - 225, "Aplicación integral de plaguicidas autorizados con registro COFEPRIS / CICOPLAFEST.")
        c.drawString(40, h - 240, "Vigencia Oficial: 30 Días Naturales a partir de la fecha de emisión.")

        c.drawString(40, 60, f"Licencia Sanitaria: {company.sanitary_license_number if company else '08 17 19 SA 0001'}")
        c.drawRightString(w - 40, 60, f"Responsable Sanitario: {company.sanitary_responsible_name if company else 'Marco Antonio Flores Sáenz'}")

        c.showPage()
        c.save()
        buf.seek(0)
        return buf.getvalue()


class OfficialWorkOrderPDFGenerator:
    """
    Generador de la ORDEN DE SERVICIO TÉCNICA Y OPERATIVA (Documento Independiente).
    Documento de control interno y recepción en sitio para el cliente:
    - Formato Carta Vertical (Portrait Letter: 612 x 792 pt)
    - Datos del cliente, sucursal, responsable en sitio y técnico aplicador
    - Checklist de plagas diagnosticadas y procedimientos técnicos ejecutados
    - Desglose de químicos dosificados y áreas tratadas
    - Registro de tiempos de servicio y horas de reentrada segura
    - Espacio de recepción para firma en sitio del cliente y conformidad
    """

    @classmethod
    def generate(cls, order: ServiceOrder, company: Optional[CompanyConfig] = None) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=32,
            bottomMargin=32
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'OrderTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=15,
            textColor=colors.HexColor("#1A365D"),
            alignment=TA_LEFT
        )
        subtitle_style = ParagraphStyle(
            'OrderSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#4A5568")
        )
        folio_style = ParagraphStyle(
            'OrderFolio',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#2B6CB0"),
            alignment=TA_RIGHT
        )
        sec_title_style = ParagraphStyle(
            'SecTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#1A365D")
        )
        label_style = ParagraphStyle(
            'Lbl',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#2D3748")
        )
        val_style = ParagraphStyle(
            'Val',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1A202C")
        )

        elements = []

        # 1. ENCABEZADO DE ORDEN DE SERVICIO
        company_name = getattr(company, 'trade_name', None) or "FLOSA CONTROL DE PLAGAS"
        company_legal = getattr(company, 'company_name', None) or "Marco Antonio Flores Sáenz"
        company_rfc = getattr(company, 'rfc', None) or "FOMS630329EA5"
        company_tel = getattr(company, 'phone', None) or "6258373393"

        status_label = (getattr(order, 'status', None) or 'COMPLETADO').upper()
        cert_obj = getattr(order, 'certificate', None)
        cert_folio_str = getattr(cert_obj, 'certificate_folio', None) if cert_obj else 'En Trámite / Programado'
        order_folio_str = getattr(order, 'folio', 'ORD-00001')

        hdr_table_data = [
            [
                Paragraph(f"<b>{(company_name or '').upper()}</b><br/><font size=7 color='#4A5568'>{company_legal} • RFC: {company_rfc} • Tel: {company_tel}</font><br/><b>HOJA TÉCNICA DE ORDEN DE SERVICIO OPERATIVO</b>", title_style),
                Paragraph(f"<b>FOLIO DE ORDEN:</b><br/>{order_folio_str}<br/><font color='#4A5568' size=7>Certificado: {cert_folio_str}</font><br/><font color='#2B6CB0' size=7.5>Estado: {status_label}</font>", folio_style)
            ]
        ]
        hdr_table = Table(hdr_table_data, colWidths=[380, 160])
        hdr_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(hdr_table)
        elements.append(Spacer(1, 8))

        # 2. DATOS DEL CLIENTE, SUCURSAL Y TÉCNICO
        branch = getattr(order, 'branch', None)
        client = getattr(branch, 'client', None) if branch else None
        tech = getattr(order, 'technician', None)

        start_time_str = order.service_start_date.strftime("%d/%m/%Y %H:%M") if getattr(order, 'service_start_date', None) else "N/A"
        end_time_str = order.service_end_date.strftime("%d/%m/%Y %H:%M") if getattr(order, 'service_end_date', None) else "N/A"

        client_legal = _safe_str(getattr(client, 'legal_name', None) or 'CLIENTE GENERAL')
        client_rfc_str = _safe_str(getattr(client, 'rfc', None) or 'XAXX010101000')

        info_rows = [
            [
                Paragraph("RAZÓN SOCIAL:", label_style),
                Paragraph(client_legal, val_style),
                Paragraph("RFC CLIENTE:", label_style),
                Paragraph(client_rfc_str, val_style)
            ],
            [
                Paragraph("SUCURSAL:", label_style),
                Paragraph(f"{_safe_str(branch.name if branch else '')} ({_safe_str(branch.classification if branch else 'Comercial')})", val_style),
                Paragraph("TELÉFONO SUCURSAL:", label_style),
                Paragraph(_safe_str(branch.phone if branch else 'N/A') or "N/A", val_style)
            ],
            [
                Paragraph("DIRECCIÓN:", label_style),
                Paragraph(_safe_str(branch.address if branch else 'Domicilio conocido'), val_style),
                Paragraph("RESPONSABLE SITIO:", label_style),
                Paragraph(_safe_str(branch.responsible_contact_name if branch else 'N/A') or "N/A", val_style)
            ],
            [
                Paragraph("TÉCNICO APLICADOR:", label_style),
                Paragraph(_safe_str(tech.full_name if tech else 'Técnico Asignado'), val_style),
                Paragraph("REGISTRO STPS DC-3:", label_style),
                Paragraph(_safe_str(getattr(tech, 'stps_registration_number', None) if tech else None) or "DC3-VIGENTE", val_style)
            ],
            [
                Paragraph("INICIO DE SERVICIO:", label_style),
                Paragraph(start_time_str, val_style),
                Paragraph("FIN DE SERVICIO:", label_style),
                Paragraph(end_time_str, val_style)
            ]
        ]
        info_table = Table(info_rows, colWidths=[110, 230, 90, 110])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 8))

        # 3. CHECKLIST OPERATIVO DE PLAGAS Y MÉTODOS
        pests_ck = []
        if getattr(order, 'pest_crawling_insects', False): pests_ck.append("Rastreros")
        if getattr(order, 'pest_flying_insects', False): pests_ck.append("Voladores")
        if getattr(order, 'pest_rodents', False): pests_ck.append("Roedores")
        if getattr(order, 'pest_others', None): pests_ck.append(_safe_str(order.pest_others))
        pests_joined = ", ".join(pests_ck) if pests_ck else "Control general preventivo"

        procs_ck = []
        if getattr(order, 'proc_aspersion', False): procs_ck.append("Aspersión líquida")
        if getattr(order, 'proc_baits', False): procs_ck.append("Cebado")
        if getattr(order, 'proc_traps', False): procs_ck.append("Trampas mecánicas/goma")
        if getattr(order, 'proc_gels', False): procs_ck.append("Aplicación de gel")
        if getattr(order, 'proc_ulv_fogging', False): procs_ck.append("Nebulización ULV en frío")
        if getattr(order, 'proc_thermofogging', False): procs_ck.append("Termonebulización")
        procs_joined = ", ".join(procs_ck) if procs_ck else "Aspersión focalizada"

        check_rows = [
            [
                Paragraph("<b>PLAGAS ATENDIDAS:</b>", label_style),
                Paragraph(pests_joined, val_style)
            ],
            [
                Paragraph("<b>PROCEDIMIENTOS TÉCNICOS:</b>", label_style),
                Paragraph(procs_joined, val_style)
            ]
        ]
        check_table = Table(check_rows, colWidths=[140, 400])
        check_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#EDF2F7")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(check_table)
        elements.append(Spacer(1, 8))

        # 4. PRODUCTOS Y QUÍMICOS APLICADOS
        elements.append(Paragraph("<b>REGISTRO DE PRODUCTOS Y PLAGUICIDAS APLICADOS</b>", sec_title_style))
        elements.append(Spacer(1, 3))

        chem_headers = [
            Paragraph("<b>Producto Comercial</b>", label_style),
            Paragraph("<b>Ingrediente Activo</b>", label_style),
            Paragraph("<b>Reg. CICOPLAFEST</b>", label_style),
            Paragraph("<b>Dosis / Litro</b>", label_style),
            Paragraph("<b>Área Tratada</b>", label_style),
            Paragraph("<b>Método</b>", label_style)
        ]
        chem_rows = [chem_headers]

        cert_applied = list(getattr(order.certificate, 'applied_chemicals', None) or []) if (order and order.certificate) else []
        if cert_applied:
            for item in cert_applied:
                chem = getattr(item, 'chemical', None)
                comm_name = _safe_str(getattr(chem, 'commercial_name', None) if chem else 'Insecticida')
                act_ing = _safe_str(getattr(chem, 'active_ingredient', None) if chem else 'Ingrediente Activo')
                cico_no = _safe_str(getattr(chem, 'cicoplafest_number', None) if chem else 'RSCO-URB')
                dose_str = _safe_str(getattr(item, 'dose_applied', None) or '10 ml / L')
                area_str = _safe_str(getattr(item, 'area_type', None))
                zone_str = _safe_str(getattr(item, 'treated_zones_description', None))
                area_comb = f"{area_str}: {zone_str}".strip(" :") if (area_str or zone_str) else "Áreas comunes"
                method_str = _safe_str(getattr(item, 'application_method', None) or 'Aspersión')

                chem_rows.append([
                    Paragraph(comm_name, val_style),
                    Paragraph(act_ing, val_style),
                    Paragraph(cico_no, val_style),
                    Paragraph(dose_str, val_style),
                    Paragraph(area_comb, val_style),
                    Paragraph(method_str, val_style)
                ])
        else:
            chem_rows.append([
                Paragraph("Servicio agendado / Sin químicos aplicados aún", val_style),
                Paragraph("-", val_style),
                Paragraph("-", val_style),
                Paragraph("-", val_style),
                Paragraph("-", val_style),
                Paragraph("-", val_style)
            ])

        chem_table = Table(chem_rows, colWidths=[100, 95, 95, 70, 110, 70])
        chem_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(chem_table)
        elements.append(Spacer(1, 8))

        # 5. DIAGNÓSTICO, OBSERVACIONES Y RECOMENDACIONES TÉCNICAS
        obs_text = order.observations or "Sin observaciones operativas particulares. Se atendieron las áreas requeridas conforme a los estándares de inocuidad."
        results_text = order.results_summary or "Servicio ejecutado con éxito bajo condiciones normales de inocuidad y control integrado de plagas."

        diag_rows = [
            [Paragraph("<b>DIAGNÓSTICO Y RESULTADOS EN SITIO:</b><br/>" + results_text, val_style)],
            [Paragraph("<b>OBSERVACIONES Y RECOMENDACIONES ESTRUCTURALES:</b><br/>" + obs_text, val_style)]
        ]
        diag_table = Table(diag_rows, colWidths=[540])
        diag_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(diag_table)
        elements.append(Spacer(1, 12))

        # 6. FIRMAS DE CONFORMIDAD
        sig_data = [
            [
                Paragraph(f"_____________________________<br/><b>{tech.full_name if tech else 'Técnico Aplicador'}</b><br/>Técnico Certificado STPS<br/>Reg: {(tech.stps_registration_number if tech else None) or 'DC3-VIGENTE'}", subtitle_style),
                Paragraph(f"_____________________________<br/><b>{branch.responsible_contact_name or 'Responsable en Sitio'}</b><br/>Recepción y Conformidad del Cliente<br/>Firma y Sello de la Unidad", subtitle_style)
            ]
        ]
        sig_table = Table(sig_data, colWidths=[270, 270])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(KeepTogether(sig_table))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()


class BitacoraPDFGenerator:
    """Generador de reportes PDF oficiales para Bitácoras NOM-256 / STPS / MIP."""

    @staticmethod
    def generate_epp_annual_pdf(rows, technician_name: str, year: int, config) -> bytes:
        """Genera la sábana anual de dotación y revisión de EPP en formato horizontal."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            leftMargin=20,
            rightMargin=20,
            topMargin=20,
            bottomMargin=20
        )
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'BitTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=12,
            textColor=colors.HexColor('#1E3A8A'),
            alignment=1
        )
        sub_style = ParagraphStyle(
            'BitSub',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            textColor=colors.HexColor('#475569'),
            alignment=1
        )
        cell_style = ParagraphStyle(
            'BitCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=6.5,
            leading=7.5,
            textColor=colors.HexColor('#1E293B')
        )
        cell_head = ParagraphStyle(
            'BitHead',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=6.5,
            leading=7.5,
            textColor=colors.white,
            alignment=1
        )

        company_name = getattr(config, 'company_name', 'FUMIFLOSA S.A. DE C.V.')
        elements.append(Paragraph(f"<b>{company_name}</b> - CONTROL INTEGRAL DE PLAGAS URBANAS", title_style))
        elements.append(Paragraph(f"BITÁCORA ANUAL DE CONTROL Y ENTREGA DE EQUIPO DE PROTECCIÓN PERSONAL (EPP) - AÑO {year}", title_style))
        elements.append(Paragraph(f"Técnico Responsable: <b>{technician_name}</b> | Conforme a la NOM-256-SSA1-2012 y NOM-017-STPS", sub_style))
        elements.append(Spacer(1, 8))

        # Tabla de 12 meses
        headers = ["EPP", "FRECUENCIA", "ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
        table_data = [[Paragraph(f"<b>{h}</b>", cell_head) for h in headers]]

        for r in rows:
            table_data.append([
                Paragraph(getattr(r, 'epp_item', ''), cell_style),
                Paragraph(getattr(r, 'frequency', ''), cell_style),
                Paragraph("✓" if getattr(r, 'jan_signed', False) else (getattr(r, 'jan_date', '') or "-"), cell_style),
                Paragraph("✓" if getattr(r, 'feb_signed', False) else (getattr(r, 'feb_date', '') or "-"), cell_style),
                Paragraph("✓" if getattr(r, 'mar_signed', False) else (getattr(r, 'mar_date', '') or "-"), cell_style),
                Paragraph("✓" if getattr(r, 'apr_signed', False) else (getattr(r, 'apr_date', '') or "-"), cell_style),
                Paragraph("✓" if getattr(r, 'may_signed', False) else (getattr(r, 'may_date', '') or "-"), cell_style),
                Paragraph("✓" if getattr(r, 'jun_signed', False) else (getattr(r, 'jun_date', '') or "-"), cell_style),
                Paragraph("✓" if getattr(r, 'jul_signed', False) else (getattr(r, 'jul_date', '') or "-"), cell_style),
                Paragraph("✓" if getattr(r, 'aug_signed', False) else (getattr(r, 'aug_date', '') or "-"), cell_style),
                Paragraph("✓" if getattr(r, 'sep_signed', False) else (getattr(r, 'sep_date', '') or "-"), cell_style),
                Paragraph("✓" if getattr(r, 'oct_signed', False) else (getattr(r, 'oct_date', '') or "-"), cell_style),
                Paragraph("✓" if getattr(r, 'nov_signed', False) else (getattr(r, 'nov_date', '') or "-"), cell_style),
                Paragraph("✓" if getattr(r, 'dec_signed', False) else (getattr(r, 'dec_date', '') or "-"), cell_style),
            ])

        col_widths = [140, 90] + [42] * 12
        matrix_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        matrix_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(matrix_table)
        elements.append(Spacer(1, 15))

        # Firmas al pie
        sig_data = [
            [
                Paragraph(f"______________________________________<br/><b>{technician_name}</b><br/>Firma de Recepción del Técnico", sub_style),
                Paragraph(f"______________________________________<br/><b>{getattr(config, 'sanitary_responsible_name', 'Responsable Técnico')}</b><br/>Responsable Técnico Sanitario", sub_style)
            ]
        ]
        sig_table = Table(sig_data, colWidths=[370, 370])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(KeepTogether(sig_table))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def generate_generic_log_pdf(title: str, subtitle: str, columns: list, rows: list, config) -> bytes:
        """Genera un reporte PDF estándar de auditoría para bitácoras operativas."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            leftMargin=25,
            rightMargin=25,
            topMargin=25,
            bottomMargin=25
        )
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'GenTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=13,
            textColor=colors.HexColor('#0F172A'),
            alignment=1
        )
        sub_style = ParagraphStyle(
            'GenSub',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            textColor=colors.HexColor('#475569'),
            alignment=1
        )
        cell_style = ParagraphStyle(
            'GenCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7,
            leading=8.5,
            textColor=colors.HexColor('#1E293B')
        )
        cell_head = ParagraphStyle(
            'GenHead',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7.5,
            leading=9,
            textColor=colors.white,
            alignment=1
        )

        company_name = getattr(config, 'company_name', 'FUMIFLOSA S.A. DE C.V.')
        elements.append(Paragraph(f"<b>{company_name}</b> - REGISTROS OPERATIVOS SANITARIOS", title_style))
        elements.append(Paragraph(title, title_style))
        elements.append(Paragraph(subtitle, sub_style))
        elements.append(Spacer(1, 10))

        table_data = [[Paragraph(f"<b>{c}</b>", cell_head) for c in columns]]
        for row in rows:
            table_data.append([Paragraph(str(val or '-'), cell_style) for val in row])

        col_count = len(columns)
        available_width = 742
        col_width = available_width / col_count
        log_table = Table(table_data, colWidths=[col_width] * col_count, repeatRows=1)
        log_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0284C7')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(log_table)

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

