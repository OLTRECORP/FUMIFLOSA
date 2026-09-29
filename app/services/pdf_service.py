import io
from typing import Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_JUSTIFY

from app.models import ServiceOrder, Certificate, CompanyConfig


class OfficialCertificatePDFGenerator:
    @staticmethod
    def generate(order: ServiceOrder, cert: Certificate, company: Optional[CompanyConfig] = None) -> bytes:
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
        
        # Datos de la Empresa Prestadora
        company_trade = company.trade_name if company else "FUMIFLOSA - CONTROL INTEGRAL DE PLAGAS URBANAS"
        company_legal = company.company_name if company else "FUMIFLOSA S.A. DE C.V."
        company_rfc = company.rfc if company else "FUM200101XYZ"
        company_phone = company.phone if company else "55-1234-5678"
        sintox_phones = company.sintox_emergency_phones if company else "01-800-0092800 / 800-009-2800 / CDMX 55-5598-6659"
        reentry_hours = company.default_reentry_hours if company else 2

        # Estilos tipográficos
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=14,
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
                Paragraph(f"<b>{company_trade.upper()}</b><br/><font size=7 color='#4A5568'>{company_legal} • RFC: {company_rfc} • Tel: {company_phone}</font><br/>Servicios Especializados de Desinfección y Manejo Integrado de Plagas", title_style),
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
            f"<b>EMERGENCIAS TOXICOLÓGICAS (SINTOX):</b> Atención médica las 24 hrs, los 365 días del año al <b>{sintox_phones}</b>. "
            "En caso de intoxicación: Retire a la persona del área expuesta, lave la piel con abundante agua y jabón, "
            "no induzca el vómito sin indicación médica y presente esta constancia con los registros CICOPLAFEST correspondientes."
        )
        reentry_text = (
            f"<b>MEDIDAS PREVENTIVAS Y SEGURIDAD:</b> Tiempo mínimo de reentrada a las áreas tratadas: <b>{reentry_hours} a 4 horas</b> posteriores a la aplicación. "
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
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(legal_table)
        elements.append(Spacer(1, 12))

        # 6. FIRMAS Y ESPACIO PARA SELLO INSTITUCIONAL
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
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(KeepTogether(sig_table))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
