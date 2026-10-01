import io
import os
from datetime import date, datetime
from typing import Optional
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
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=landscape(letter))
        page_width, page_height = landscape(letter)  # 792.0 x 612.0

        # 1. MARCO ORNAMENTAL
        if FRAME_PATH.exists():
            c.drawImage(str(FRAME_PATH), 8.25, 14.25, width=775.5, height=585.0, mask='auto')
        else:
            # Fallback dibujo de marco elegante con línea doble verde
            c.setStrokeColor(colors.HexColor("#738C7B"))
            c.setLineWidth(3)
            c.rect(20, 20, page_width - 40, page_height - 40)
            c.setLineWidth(0.8)
            c.rect(25, 25, page_width - 50, page_height - 50)

        # 2. MARCA DE AGUA CENTRAL
        if WATERMARK_PATH.exists():
            c.saveState()
            c.drawImage(str(WATERMARK_PATH), 185.25, 210.01, width=521.7, height=197.99, mask='auto')
            c.restoreState()

        # 3. ENCABEZADO CENTRADO
        c.setFont("Helvetica-Bold", 24)
        c.setFillColor(colors.HexColor("#1E3A2F"))
        c.drawCentredString(396, 488, "CERTIFICADO DE SERVICIO")

        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#222222"))
        
        responsible_title = company.company_name if company and company.company_name else "Marco Antonio Flores Sáenz (FLOSA Control de Plagas)"
        c.drawCentredString(396, 463, responsible_title)
        
        rfc_phone = f"{company.rfc if company else 'FOMS630329EA5'}    Tel: {company.phone if company else '6258373393'}"
        c.drawCentredString(396, 452, rfc_phone)
        
        address_text = company.address if company and company.address else "C10a 685 Col. Centro, Cd. Cuauhtémoc, Chih C.P. 31500"
        c.drawCentredString(396, 441, address_text)

        # 4. FOLIO Y FECHA (ALINEADOS A LA DERECHA)
        folio_str = cert.certificate_folio or (f"B/{order.folio}" if order.folio else "B/00001")
        issue_str = cert.issue_date.strftime("%d/%m/%y") if cert.issue_date else date.today().strftime("%d/%m/%y")

        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#1A202C"))
        c.drawRightString(645, 432, "Folio:")
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.HexColor("#9B2C2C"))
        c.drawString(652, 432, folio_str)

        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#1A202C"))
        c.drawRightString(645, 420, "Fecha De Expedición:")
        c.setFont("Helvetica", 9)
        c.drawString(652, 420, issue_str)

        # 5. DATOS DEL CLIENTE Y LUGAR DE SERVICIO
        client = order.branch.client
        branch = order.branch
        
        # Plagas a controlar
        pests_list = []
        if order.pest_crawling_insects:
            pests_list.append("INSECTOS RASTREROS")
        if order.pest_flying_insects:
            pests_list.append("INSECTOS VOLADORES")
        if order.pest_rodents:
            pests_list.append("ROEDORES")
        if order.pest_others:
            pests_list.append(order.pest_others.upper())
        pests_text = ", ".join(pests_list) if pests_list else "TODO TIPO DE INSECTOS RASTREROS"

        styles = getSampleStyleSheet()
        client_label_style = ParagraphStyle(
            'ClientLabel',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8.5,
            leading=10.5,
            textColor=colors.HexColor("#1A202C")
        )
        client_val_style = ParagraphStyle(
            'ClientVal',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=10.5,
            textColor=colors.HexColor("#2D3748")
        )

        client_rows = [
            [
                Paragraph("<b>Nombre Del Cliente:</b>", client_label_style),
                Paragraph(f"{client.legal_name.upper()} {f'({branch.name.upper()})' if branch.name and branch.name != client.legal_name else ''}", client_val_style)
            ],
            [
                Paragraph("<b>Dirección:</b>", client_label_style),
                Paragraph(branch.address.upper() if branch.address else "DOMICILIO CONOCIDO", client_val_style)
            ],
            [
                Paragraph("<b>Lugar De Servicio:</b>", client_label_style),
                Paragraph(f"{branch.name.upper()} - {branch.classification.value.upper()}", client_val_style)
            ],
            [
                Paragraph("<b>Plagas a controlar:</b>", client_label_style),
                Paragraph(pests_text, client_val_style)
            ]
        ]
        
        client_table = Table(client_rows, colWidths=[105, 515])
        client_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        # Render tabla cliente
        client_table.wrapOn(c, 620, 100)
        client_table.drawOn(c, 85, 362)

        # 6. TABLA DE QUÍMICOS / INGREDIENTES ACTIVOS (HASTA 4 LÍNEAS)
        chem_hdr_style = ParagraphStyle(
            'ChemHdr',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8.5,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1E3A2F")
        )
        chem_cell_style = ParagraphStyle(
            'ChemCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=9.5,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1A202C")
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

        applied = list(cert.applied_chemicals or [])
        # Rellenar filas reales
        for item in applied[:4]:
            chem = item.chemical
            chem_data.append([
                Paragraph(chem.active_ingredient.upper(), chem_cell_style),
                Paragraph(chem.cicoplafest_number.upper(), chem_cell_style),
                Paragraph(item.dose_applied.upper(), chem_cell_style),
                Paragraph(f"{item.area_type.value.upper()}: {item.treated_zones_description.upper()}", chem_cell_style),
                Paragraph(item.application_method.upper(), chem_cell_style)
            ])

        # Rellenar con filas vacías si hay menos de 4 para mantener el formato idéntico
        while len(chem_data) < 5:
            chem_data.append([
                Paragraph("&nbsp;", chem_cell_style),
                Paragraph("&nbsp;", chem_cell_style),
                Paragraph("&nbsp;", chem_cell_style),
                Paragraph("&nbsp;", chem_cell_style),
                Paragraph("&nbsp;", chem_cell_style)
            ])

        # Dimensiones de columnas idénticas a la imagen original (suma = 618.8 pt)
        chem_table = Table(chem_data, colWidths=[148.0, 224.0, 82.0, 82.0, 82.0], rowHeights=[19] * 5)
        chem_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#DDE5DF")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#718096")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))

        chem_table.wrapOn(c, 620, 100)
        chem_table.drawOn(c, 85, 260)

        # 7. RECOMENDACIONES AL CLIENTE
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(colors.HexColor("#1A202C"))
        c.drawString(85, 246, "Recomendaciones al cliente:")

        rec_style = ParagraphStyle(
            'RecStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.5,
            leading=9.5,
            alignment=TA_JUSTIFY,
            textColor=colors.HexColor("#2D3748")
        )
        recommendations_text = (
            "Si al momento de aplicar los productos se encuentran personas o niños retirarlos del lugar como mínimo una hora, "
            "se recomienda colocar este certificado en un lugar visible, la vigencia es de 30 días a partir de la fecha del presente documento. "
            "Para antídotos en caso de contacto o ingestión acudir al medico o llame a SINTOX. "
            "Es de gran importancia conservar el lugar limpio y ordenado para que sea efectivo el control de plagas."
        )

        rec_table = Table([[Paragraph(recommendations_text, rec_style)]], colWidths=[520])
        rec_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#A0AEC0")),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#FAFDF9")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        rec_table.wrapOn(c, 520, 50)
        rec_table.drawOn(c, 85, 192)

        # 8. PIE DE PÁGINA (3 COLUMNAS: LOGO, FIRMA TÉCNICA, SINTOX)
        # Logo izquierdo
        if LOGO_PATH.exists():
            c.drawImage(str(LOGO_PATH), 95, 100, width=175.0, height=75.0, mask='auto')

        # Firma Centro
        if SIGNATURE_PATH.exists():
            c.drawImage(str(SIGNATURE_PATH), 335, 118, width=125.0, height=50.0, mask='auto')

        c.setStrokeColor(colors.HexColor("#4A5568"))
        c.setLineWidth(0.8)
        c.line(300, 120, 490, 120)

        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(colors.HexColor("#1A202C"))
        c.drawCentredString(395, 108, cert.sanitary_responsible_name or "Marco Antonio Flores Sáenz")
        
        c.setFont("Helvetica", 8)
        c.drawCentredString(395, 97, "Responsable Técnico")

        license_no = cert.sanitary_license_number or (company.sanitary_license_number if company else "08 17 19 SA 0001")
        c.drawCentredString(395, 86, f"No. De Licencia Sanitaria: {license_no}")

        # Recuadro SINTOX (Derecha)
        sintox_hdr_style = ParagraphStyle(
            'SintoxHdr',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=6,
            leading=7.5,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#C53030")
        )
        sintox_body_style = ParagraphStyle(
            'SintoxBody',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=5.5,
            leading=7,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#2D3748")
        )

        sintox_content = (
            "<font color='#C53030'><b>EN CASO DE INTOXICACION DE PLAGUICIDAS SINTOX</b></font><br/>"
            "DEL INTERIOR SIN COSTO  <b>01-800-0092800</b><br/>"
            "AREA METROPOLITANA <b>01(55)5598-6659 Y (55)5611-2634</b><br/>"
            "<font color='#2B6CB0'><b>SERVICIO LAS 24 HORAS</b></font>"
        )
        sintox_table = Table([[Paragraph(sintox_content, sintox_body_style)]], colWidths=[205])
        sintox_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor("#E53E3E")),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#FFF5F5")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        sintox_table.wrapOn(c, 205, 55)
        sintox_table.drawOn(c, 500, 105)

        # 9. MARCA DE AGUA EN CASO DE CANCELACIÓN
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
        company_name = company.trade_name if company and company.trade_name else "FLOSA CONTROL DE PLAGAS"
        company_legal = company.company_name if company and company.company_name else "Marco Antonio Flores Sáenz"
        company_rfc = company.rfc if company else "FOMS630329EA5"
        company_tel = company.phone if company else "6258373393"

        status_label = (getattr(order, 'status', None) or 'COMPLETADO').upper()
        hdr_table_data = [
            [
                Paragraph(f"<b>{(company_name or '').upper()}</b><br/><font size=7 color='#4A5568'>{company_legal} • RFC: {company_rfc} • Tel: {company_tel}</font><br/><b>HOJA TÉCNICA DE ORDEN DE SERVICIO OPERATIVO</b>", title_style),
                Paragraph(f"<b>FOLIO DE ORDEN:</b><br/>{order.folio}<br/><font color='#4A5568' size=7>Certificado: {order.certificate.certificate_folio if order.certificate else 'En Trámite / Programado'}</font><br/><font color='#2B6CB0' size=7.5>Estado: {status_label}</font>", folio_style)
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
        branch = order.branch
        client = branch.client
        tech = order.technician

        start_time_str = order.service_start_date.strftime("%d/%m/%Y %H:%M") if order.service_start_date else "N/A"
        end_time_str = order.service_end_date.strftime("%d/%m/%Y %H:%M") if order.service_end_date else "N/A"

        info_rows = [
            [
                Paragraph("RAZÓN SOCIAL:", label_style),
                Paragraph(client.legal_name, val_style),
                Paragraph("RFC CLIENTE:", label_style),
                Paragraph(client.rfc, val_style)
            ],
            [
                Paragraph("SUCURSAL:", label_style),
                Paragraph(f"{branch.name} ({branch.classification.value})", val_style),
                Paragraph("TELÉFONO SUCURSAL:", label_style),
                Paragraph(branch.phone or "N/A", val_style)
            ],
            [
                Paragraph("DIRECCIÓN:", label_style),
                Paragraph(branch.address, val_style),
                Paragraph("RESPONSABLE SITIO:", label_style),
                Paragraph(branch.responsible_contact_name or "N/A", val_style)
            ],
            [
                Paragraph("TÉCNICO APLICADOR:", label_style),
                Paragraph(tech.full_name if tech else "Técnico Asignado", val_style),
                Paragraph("REGISTRO STPS DC-3:", label_style),
                Paragraph((tech.stps_registration_number if tech else None) or "DC3-VIGENTE", val_style)
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
        if order.pest_crawling_insects: pests_ck.append("Rastreros")
        if order.pest_flying_insects: pests_ck.append("Voladores")
        if order.pest_rodents: pests_ck.append("Roedores")
        if order.pest_others: pests_ck.append(order.pest_others)
        pests_joined = ", ".join(pests_ck) if pests_ck else "Control general preventivo"

        procs_ck = []
        if order.proc_aspersion: procs_ck.append("Aspersión líquida")
        if order.proc_baits: procs_ck.append("Cebado")
        if order.proc_traps: procs_ck.append("Trampas mecánicas/goma")
        if order.proc_gels: procs_ck.append("Aplicación de gel")
        if order.proc_ulv_fogging: procs_ck.append("Nebulización ULV en frío")
        if order.proc_thermofogging: procs_ck.append("Termonebulización")
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

        if order.certificate and order.certificate.applied_chemicals:
            for item in order.certificate.applied_chemicals:
                chem = item.chemical
                chem_rows.append([
                    Paragraph(chem.commercial_name, val_style),
                    Paragraph(chem.active_ingredient, val_style),
                    Paragraph(chem.cicoplafest_number, val_style),
                    Paragraph(item.dose_applied, val_style),
                    Paragraph(f"{item.area_type.value}: {item.treated_zones_description}", val_style),
                    Paragraph(item.application_method, val_style)
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
