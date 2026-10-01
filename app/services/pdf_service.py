import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_JUSTIFY

from app.models import ServiceOrder, Certificate


class OfficialCertificatePDFGenerator:
    @staticmethod
    def generate(order: ServiceOrder, cert: Certificate) -> bytes:
        """
        Genera el PDF oficial del Certificado de Servicio de Control de Plagas
        cumpliendo con la NOM-256-SSA1-2012, avisos SINTOX y espacios de sellos.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=30,
            bottomMargin=30
        )
        
        styles = getSampleStyleSheet()
        
        # Estilos tipográficos
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=15,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1A365D")
        )
        subtitle_style = ParagraphStyle(
            'SubTitleStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#4A5568")
        )
        header_tag = ParagraphStyle(
            'HeaderTag',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=11,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#C53030")
        )
        label_style = ParagraphStyle(
            'LabelStyle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#2D3748")
        )
        value_style = ParagraphStyle(
            'ValueStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1A202C")
        )
        legal_style = ParagraphStyle(
            'LegalStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=6.5,
            leading=8,
            alignment=TA_JUSTIFY,
            textColor=colors.HexColor("#4A5568")
        )

        elements = []

        # 1. ENCABEZADO Y LICENCIAS
        header_data = [
            [
                Paragraph("<b>FUMIFLOSA - CONTROL INTEGRAL DE PLAGAS URBANAS</b><br/>Servicios Especializados de Desinfección y Manejo Integrado de Plagas", title_style),
                Paragraph(f"<b>FOLIO OFICIAL:</b><br/>{cert.certificate_folio}<br/><b>ORDEN:</b> {order.folio}", header_tag)
            ]
        ]
        header_table = Table(header_data, colWidths=[380, 160])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(header_table)
        elements.append(Paragraph(
            "CUMPLIMIENTO ESTRICTO DE LA NORMA OFICIAL MEXICANA NOM-256-SSA1-2012 / COFEPRIS / STPS", subtitle_style
        ))
        elements.append(Spacer(1, 8))

        # 2. DATOS DEL CLIENTE Y SUCURSAL
        client = order.branch.client
        branch = order.branch
        
        info_data = [
            [
                Paragraph("RAZÓN SOCIAL (MATRIZ):", label_style),
                Paragraph(client.legal_name, value_style),
                Paragraph("RFC:", label_style),
                Paragraph(client.rfc, value_style)
            ],
            [
                Paragraph("SUCURSAL / UNIDAD:", label_style),
                Paragraph(f"{branch.name} ({branch.unit_code or 'S/N'})", value_style),
                Paragraph("CLASIFICACIÓN:", label_style),
                Paragraph(branch.classification.value, value_style)
            ],
            [
                Paragraph("DIRECCIÓN DE APLICACIÓN:", label_style),
                Paragraph(branch.address, value_style),
                Paragraph("TELÉFONO:", label_style),
                Paragraph(branch.phone, value_style)
            ],
            [
                Paragraph("RESPONSABLE EN SITIO:", label_style),
                Paragraph(branch.responsible_contact_name, value_style),
                Paragraph("CONTRATO MARCO:", label_style),
                Paragraph(client.master_contract_number or "N/A", value_style)
            ]
        ]
        info_table = Table(info_data, colWidths=[120, 230, 80, 110])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 8))

        # 3. VIGENCIA Y DATOS SANITARIOS
        dates_data = [
            [
                Paragraph("FECHA EXPEDICIÓN:", label_style),
                Paragraph(cert.issue_date.strftime("%d/%m/%Y"), value_style),
                Paragraph("VIGENCIA DEL SERVICIO:", label_style),
                Paragraph(f"<b>{cert.validity_start_date.strftime('%d/%m/%Y')} al {cert.validity_end_date.strftime('%d/%m/%Y')}</b>", value_style),
                Paragraph("LICENCIA SANITARIA:", label_style),
                Paragraph(cert.sanitary_license_number, value_style)
            ]
        ]
        dates_table = Table(dates_data, colWidths=[90, 80, 110, 120, 80, 60])
        dates_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#EDF2F7")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(dates_table)
        elements.append(Spacer(1, 8))

        # 4. TABLA DE QUÍMICOS DOSIFICADOS (NOM-256)
        elements.append(Paragraph("<b>DETALLE DE PRODUCTOS PLAGUICIDAS APLICADOS (AUTORIZADOS POR COFEPRIS / CICOPLAFEST)</b>", label_style))
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

        for item in cert.applied_chemicals:
            chem = item.chemical
            chem_rows.append([
                Paragraph(chem.commercial_name, value_style),
                Paragraph(chem.active_ingredient, value_style),
                Paragraph(chem.cicoplafest_number, value_style),
                Paragraph(item.dose_applied, value_style),
                Paragraph(f"{item.area_type.value}: {item.treated_zones_description}", value_style),
                Paragraph(item.application_method, value_style)
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

        # 5. AVISOS LEGALES, INTOXICACIÓN Y SINTOX (NOM-256-SSA1-2012)
        sintox_text = (
            "<b>EMERGENCIAS TOXICOLÓGICAS (SINTOX):</b> Atención médica las 24 hrs, los 365 días del año al <b>800-009-2800 / 01-800-0092800</b> "
            "o CDMX al <b>55-5598-6659</b>. En caso de intoxicación: Retire a la persona del área expuesta, lave la piel con abundante agua y jabón, "
            "no induzca el vómito sin indicación médica y presente esta constancia con los registros CICOPLAFEST correspondientes."
        )
        reentry_text = (
            "<b>MEDIDAS PREVENTIVAS Y SEGURIDAD:</b> Tiempo mínimo de reentrada a las áreas tratadas: <b>2 a 4 horas</b> posteriores a la aplicación. "
            "Ventilar el inmueble durante al menos 30 minutos antes de reanudar actividades habituales."
        )

        legal_table_data = [
            [Paragraph(sintox_text, legal_style)],
            [Paragraph(reentry_text, legal_style)]
        ]
        legal_table = Table(legal_table_data, colWidths=[540])
        legal_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#FFF5F5")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#FEB2B2")),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(legal_table)
        elements.append(Spacer(1, 6))

        # 6. FIRMAS TRADICIONALES
        signatures_data = [
            [
                Paragraph(f"_____________________________<br/><b>{cert.sanitary_responsible_name}</b><br/>Responsable Sanitario<br/>Céd. Prof. {cert.sanitary_responsible_id or 'En Trámite'}", subtitle_style),
                Paragraph(f"_____________________________<br/><b>{order.technician.full_name}</b><br/>Técnico Aplicador Certificado<br/>Reg. STPS: {order.technician.stps_registration_number or 'DC3-VIGENTE'}", subtitle_style),
                Paragraph("_____________________________<br/><b>Sello y Firma Institucional</b><br/>Recepción / Vigilancia Sanitaria<br/>Espacio para sello oficial", subtitle_style)
            ]
        ]
        sig_table = Table(signatures_data, colWidths=[180, 180, 180])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(sig_table)
        elements.append(Spacer(1, 6))

        # 7. BLOQUE DE FIRMA ELECTRÓNICA AVANZADA (FIEL / E.FIRMA SAT)
        from reportlab.graphics.barcode.qr import QrCodeWidget
        from reportlab.graphics.shapes import Drawing

        seal_style = ParagraphStyle(
            'SealStyle',
            parent=styles['Normal'],
            fontName='Courier',
            fontSize=5.5,
            leading=7,
            textColor=colors.HexColor("#2D3748")
        )
        seal_meta_style = ParagraphStyle(
            'SealMetaStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=6,
            leading=8,
            textColor=colors.HexColor("#4A5568")
        )

        if cert.is_signed and cert.digital_signature_seal:
            qr_data = f"https://fumiflosa.mx/verificar?folio={cert.certificate_folio}&uuid={cert.verification_uuid or cert.id}&rfc={cert.signed_by_rfc or 'RFC'}"
            qr_widget = QrCodeWidget(qr_data)
            qr_widget.barWidth = 60
            qr_widget.barHeight = 60
            qr_drawing = Drawing(60, 60)
            qr_drawing.add(qr_widget)

            fiel_info_html = (
                f"<b>FIRMA ELECTRÓNICA AVANZADA (e.firma / FIEL del SAT) - VALIDEZ OFICIAL NOM-256</b><br/>"
                f"<b>Serie Certificado SAT:</b> {cert.certificate_serial_number or 'N/A'} &nbsp;|&nbsp; "
                f"<b>Fecha de Firma:</b> {cert.signed_at.strftime('%Y-%m-%d %H:%M:%S UTC') if cert.signed_at else 'N/A'} &nbsp;|&nbsp; "
                f"<b>RFC Firmante:</b> {cert.signed_by_rfc or 'N/A'} ({cert.signed_by_name or 'FUMIFLOSA'})<br/>"
                f"<b>Cadena Original:</b><br/>"
                f"<font face='Courier' size='5'>{cert.original_chain or '||...||'}</font><br/>"
                f"<b>Sello Digital:</b><br/>"
                f"<font face='Courier' size='5'>{cert.digital_signature_seal}</font>"
            )

            fiel_table_data = [
                [qr_drawing, Paragraph(fiel_info_html, seal_style)]
            ]
            fiel_table = Table(fiel_table_data, colWidths=[65, 475])
            fiel_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F0FDF4")),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#86EFAC")),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(KeepTogether(fiel_table))
        else:
            pending_html = (
                "<b>ESTADO DE CERTIFICACIÓN:</b> DOCUMENTO PENDIENTE DE FIRMA ELECTRÓNICA AVANZADA (FIEL DEL SAT). "
                "<i>Este documento se encuentra en estado de borrador o revisión previa. Una vez validado por el responsable sanitario, "
                "se estampará la firma digital con validez plena ante COFEPRIS y Protección Civil.</i>"
            )
            pending_table = Table([[Paragraph(pending_html, seal_meta_style)]], colWidths=[540])
            pending_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#FEFCE8")),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#FDE047")),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(KeepTogether(pending_table))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
