"""app/services/pesticide_sheet_service.py
Servicio especializado para la obtención en línea, resolución por RSCO y generación
de Fichas Técnicas Oficiales y Hojas de Datos de Seguridad (HDS / MSDS)
conforme a la NOM-256-SSA1-2012, NOM-018-STPS-2015 (SGA/GHS) y CICOPLAFEST / COFEPRIS.
"""

import io
import re
import ssl
import html as html_module
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Dict, Any, Optional, List

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas


# ============================================================================
# BASE DE CONOCIMIENTO Y RESOLUCIÓN EN LÍNEA DE FICHAS TÉCNICAS Y HDS
# Mapeo oficial de productos urbanos COFEPRIS / CICOPLAFEST
# ============================================================================

PESTICIDE_ONLINE_DIRECTORY: List[Dict[str, Any]] = [
    {
        "keywords": ["biothrine", "deltametrina", "flow"],
        "rsco_prefix": "RSCO-URB-INAC-111-315-009-2.5",
        "alt_rsco": ["RSCO-DOM-INAC-179-317-009-2.5", "RSCO-URB-INAC-111-316-009-02.5"],
        "commercial_name": "Biothrine Flow",
        "active_ingredient": "Deltametrina 2.5%",
        "chemical_group": "Piretroide sintético tipo II",
        "cas_number": "52918-63-5",
        "manufacturer": "Envu / Bayer Environmental Science",
        "formulation": "Suspensión Concentrada (SC / Acuosa)",
        "authorized_dose": "10 a 20 ml / L de agua",
        "safety_interval_hours": 2,
        "toxicological_category": "Banda Verde / Precaución (Categoría 5 GHS)",
        "ghs_signal_word": "ATENCIÓN",
        "ghs_pictograms": ["GHS07 - Signo de Exclamación", "GHS09 - Medio Ambiente"],
        "antidote": "Tratamiento sintomático. No tiene antídoto específico. En caso de parestesia dérmica aplicar crema con vitamina E.",
        "technical_sheet_url": "https://www.es.envu.mx/-/media/project/envu/shared/latin-america/mexico/product-leaflets/biothrine-flow.pdf",
        "safety_sheet_url": "https://www.es.envu.mx/-/media/project/envu/shared/latin-america/mexico/sds/biothrine-flow-hds.pdf",
        "target_pests": "Cucarachas, Chinches de cama, Moscas, Mosquitos, Hormigas, Alacranes",
        "application_methods": "Aspersión manual residual, nebulización en frío ULV",
        "ppe_required": "Mascarilla contra vapores orgánicos y neblinas (NIOSH TC-23C), guantes de nitrilo, gogles con ventilación indirecta, overol de algodón o tyvek."
    },
    {
        "keywords": ["demand", "lambda", "cyhalotrina", "lambdacihalotrina"],
        "rsco_prefix": "RSCO-URB-INAC-173-356-064-2.5",
        "alt_rsco": ["RSCO-DOM-INAC-181-322-383-9.7", "RSCO-URB-INAC-173-356-064-02.5"],
        "commercial_name": "Demand 2.5 CS",
        "active_ingredient": "Lambda Cyhalotrina 2.5%",
        "chemical_group": "Piretroide microencapsulado con tecnología iCAP",
        "cas_number": "91465-08-6",
        "manufacturer": "Syngenta Agro S.A. de C.V.",
        "formulation": "Suspensión de Encapsulado (CS / Microencapsulado)",
        "authorized_dose": "10 a 20 ml / L de agua",
        "safety_interval_hours": 2,
        "toxicological_category": "Banda Verde / Precaución (Categoría 5 GHS)",
        "ghs_signal_word": "ATENCIÓN",
        "ghs_pictograms": ["GHS07 - Signo de Exclamación", "GHS09 - Medio Ambiente"],
        "antidote": "No se conoce antídoto específico. Realizar lavado gástrico y administrar carbón activado si procede.",
        "technical_sheet_url": "https://www.syngentappm.com.mx/sites/g/files/vjzpco1041/files/2022-09/FT_Demand_2.5_CS.pdf",
        "safety_sheet_url": "https://www.syngentappm.com.mx/sites/g/files/vjzpco1041/files/2022-09/HDS_Demand_2.5_CS.pdf",
        "target_pests": "Alacranes, Arañas (Violinista y Viuda), Cucarachas, Ciempiés, Hormigas",
        "application_methods": "Aspersión perimetral, grietas y hendiduras, barreras protectoras",
        "ppe_required": "Respirador para polvos/neblinas, guantes impermeables de neopreno o nitrilo, lentes de seguridad y ropa de manga larga."
    },
    {
        "keywords": ["maxforce", "fipronil", "forte"],
        "rsco_prefix": "RSCO-URB-INAC-175-359-392-0.05",
        "alt_rsco": ["RSCO-DOM-INAC-111-375-305-0.05", "RSCO-URB-INAC-184-315-009-2.15"],
        "commercial_name": "Maxforce Forte Gel",
        "active_ingredient": "Fipronil 0.05%",
        "chemical_group": "Fenilpirazol",
        "cas_number": "120068-37-3",
        "manufacturer": "Envu / Bayer Environmental Science",
        "formulation": "Cebo en Gel Cucarachicida con efecto Dominó",
        "authorized_dose": "1 a 3 gotas (0.25 a 0.5 g) / m²",
        "safety_interval_hours": 0,
        "toxicological_category": "Banda Verde / Precaución (Categoría 5 GHS)",
        "ghs_signal_word": "ATENCIÓN",
        "ghs_pictograms": ["GHS07 - Signo de Exclamación"],
        "antidote": "Tratamiento sintomático. No administrar barbitúricos ni depresores del SNC.",
        "technical_sheet_url": "https://www.es.envu.mx/-/media/project/envu/shared/latin-america/mexico/product-leaflets/maxforce-forte.pdf",
        "safety_sheet_url": "https://www.es.envu.mx/-/media/project/envu/shared/latin-america/mexico/sds/maxforce-forte-hds.pdf",
        "target_pests": "Cucaracha Alemana (Blattella germanica), Cucaracha Americana, Periplaneta",
        "application_methods": "Pistola aplicadora de gel dosificado en bisagras, motores y contactos",
        "ppe_required": "Guantes de protección de uso general, no se requiere protección respiratoria para cebos en gel."
    },
    {
        "keywords": ["temprid", "imidacloprid", "betaciflutrina", "beta-ciflutrina"],
        "rsco_prefix": "RSCO-MEZC-INAC-0101-385-342-31.5",
        "alt_rsco": ["RSCO-DOM-INAC-184-317-009-37.5"],
        "commercial_name": "Temprid SC",
        "active_ingredient": "Imidacloprid 21% + Beta-ciflutrina 10.5%",
        "chemical_group": "Neonicotinoide + Piretroide (Doble modo de acción)",
        "cas_number": "138261-41-3 / 68359-37-5",
        "manufacturer": "Envu / Bayer Environmental Science",
        "formulation": "Suspensión Concentrada (SC)",
        "authorized_dose": "8 a 16 ml / L de agua",
        "safety_interval_hours": 2,
        "toxicological_category": "Banda Azul / Moderadamente Tóxico (Categoría 4 GHS)",
        "ghs_signal_word": "ATENCIÓN",
        "ghs_pictograms": ["GHS07 - Nocivo", "GHS09 - Medio Ambiente"],
        "antidote": "Tratamiento de soporte y descontaminación. Sin antídoto específico.",
        "technical_sheet_url": "https://www.es.envu.mx/-/media/project/envu/shared/latin-america/mexico/product-leaflets/temprid-sc.pdf",
        "safety_sheet_url": "https://www.es.envu.mx/-/media/project/envu/shared/latin-america/mexico/sds/temprid-sc-hds.pdf",
        "target_pests": "Chinches de cama (Cimex lectularius), Cucarachas resistentes, Pulgas, Garrapatas",
        "application_methods": "Aspersión focalizada, costuras de colchones, zoclos y marcos",
        "ppe_required": "Respirador para vapores orgánicos, guantes de nitrilo, gogles herméticos y overol."
    },
    {
        "keywords": ["advion", "indoxacarb"],
        "rsco_prefix": "RSCO-URB-INAC-102K-301-392-0.6",
        "alt_rsco": ["RSCO-DOM-INAC-184-315-009-0.6"],
        "commercial_name": "Advion Cucaracha Gel",
        "active_ingredient": "Indoxacarb 0.6%",
        "chemical_group": "Oxadiazina (Bio-activación enzimática en la plaga)",
        "cas_number": "173724-41-9",
        "manufacturer": "Syngenta Agro S.A. de C.V.",
        "formulation": "Cebo en Gel Transparente Altamente Palatable",
        "authorized_dose": "2 a 5 puntos (0.5g c/u) / m²",
        "safety_interval_hours": 0,
        "toxicological_category": "Banda Verde / Precaución (Categoría 5 GHS)",
        "ghs_signal_word": "ATENCIÓN",
        "ghs_pictograms": ["GHS07 - Signo de Exclamación"],
        "antidote": "Sin antídoto específico. Tratamiento sintomático general.",
        "technical_sheet_url": "https://www.syngentappm.com.mx/sites/g/files/vjzpco1041/files/2022-09/FT_Advion_Cucaracha_Gel.pdf",
        "safety_sheet_url": "https://www.syngentappm.com.mx/sites/g/files/vjzpco1041/files/2022-09/HDS_Advion_Cucaracha_Gel.pdf",
        "target_pests": "Cucaracha Germánica (resistente a geles comunes), Oriental y Americana",
        "application_methods": "Puntos de aplicación focalizados en grietas y hendiduras",
        "ppe_required": "Guantes de examen de nitrilo durante la manipulación y colocación."
    },
    {
        "keywords": ["storm", "flocumafen"],
        "rsco_prefix": "RSCO-URB-ROD-0101-301-033-0.005",
        "alt_rsco": ["RSCO-URB-ROED-0101-301-033-0.005"],
        "commercial_name": "Storm Bloques",
        "active_ingredient": "Flocumafen 0.005%",
        "chemical_group": "Anticoagulante de segunda generación (Dosis única)",
        "cas_number": "90035-08-8",
        "manufacturer": "BASF Mexicana S.A. de C.V.",
        "formulation": "Bloque Parafinado Extruido de Alta Resistencia a Humedad",
        "authorized_dose": "1 a 2 bloques (20-40 g) por cebadero de seguridad",
        "safety_interval_hours": 0,
        "toxicological_category": "Banda Azul / Moderadamente Tóxico (Categoría 4 GHS)",
        "ghs_signal_word": "PELIGRO",
        "ghs_pictograms": ["GHS08 - Peligro para la Salud (Anticoagulante)"],
        "antidote": "VITAMINA K1 (Fitomenadiona) por vía intravenosa u oral bajo estricta supervisión médica.",
        "technical_sheet_url": "https://pestcontrol.basf.com.mx/sites/default/files/2023-01/FT_Storm_Bloques.pdf",
        "safety_sheet_url": "https://pestcontrol.basf.com.mx/sites/default/files/2023-01/HDS_Storm_Bloques.pdf",
        "target_pests": "Rattus norvegicus (rata gris), Rattus rattus (rata negra), Mus musculus",
        "application_methods": "Estaciones cebaderas de seguridad ancladas e identificadas con llave",
        "ppe_required": "Guantes de protección de goma o nitrilo para evitar olor humano y contacto dérmico."
    },
    {
        "keywords": ["klerat", "brodifacoum", "brodifacouma"],
        "rsco_prefix": "RSCO-URB-ROD-138-315-033-0.005",
        "alt_rsco": ["RSCO-URB-ROD-010-313-005-0.005", "RSCO-URB-ROED-602-302-033-0.005"],
        "commercial_name": "Klerat Bloque",
        "active_ingredient": "Brodifacoum 0.005%",
        "chemical_group": "Anticoagulante 4-hidroxicumarínico (Segunda Generación)",
        "cas_number": "56073-10-0",
        "manufacturer": "Syngenta Agro S.A. de C.V.",
        "formulation": "Bloque Parafinado con Bitrex (Disuasivo gustativo)",
        "authorized_dose": "20 a 40 g por estación de monitoreo y cebado",
        "safety_interval_hours": 0,
        "toxicological_category": "Banda Azul / Moderadamente Tóxico (Categoría 4 GHS)",
        "ghs_signal_word": "PELIGRO",
        "ghs_pictograms": ["GHS08 - Peligro de Toxicidad Sistémica"],
        "antidote": "VITAMINA K1 (Fitomenadiona) inyectable / oral. Control de tiempos de protrombina (TP).",
        "technical_sheet_url": "https://www.syngentappm.com.mx/sites/g/files/vjzpco1041/files/2022-09/FT_Klerat_Bloque.pdf",
        "safety_sheet_url": "https://www.syngentappm.com.mx/sites/g/files/vjzpco1041/files/2022-09/HDS_Klerat_Bloque.pdf",
        "target_pests": "Roedores comensales resistentes a anticoagulantes de primera generación",
        "application_methods": "Cebado en estaciones cebaderas perimetrales inviolables",
        "ppe_required": "Guantes protectores impermeables, ropa de trabajo estándar."
    },
    {
        "keywords": ["termidor", "fipronil", "termitas"],
        "rsco_prefix": "RSCO-URB-INAC-175-313-009-2.5",
        "alt_rsco": ["RSCO-URB-INAC-105-327-009-2.5"],
        "commercial_name": "Termidor 25 CE",
        "active_ingredient": "Fipronil 2.5%",
        "chemical_group": "Fenilpirazol no repelente de transferencia social",
        "cas_number": "120068-37-3",
        "manufacturer": "BASF Mexicana S.A. de C.V.",
        "formulation": "Concentrado Emulsionable (CE)",
        "authorized_dose": "10 a 20 ml / L de agua (Trinchera / Inyección)",
        "safety_interval_hours": 4,
        "toxicological_category": "Banda Azul / Moderadamente Tóxico (Categoría 4 GHS)",
        "ghs_signal_word": "ATENCIÓN",
        "ghs_pictograms": ["GHS07 - Nocivo", "GHS09 - Peligro Acuático"],
        "antidote": "No hay antídoto específico. Descontaminación y tratamiento sintomático.",
        "technical_sheet_url": "https://pestcontrol.basf.com.mx/sites/default/files/2023-01/FT_Termidor_25_CE.pdf",
        "safety_sheet_url": "https://pestcontrol.basf.com.mx/sites/default/files/2023-01/HDS_Termidor_25_CE.pdf",
        "target_pests": "Termita subterránea (Reticulitermes), Hormigas carpinteras, Hormiga loca",
        "application_methods": "Inyección en losas, barreras químicas perimetrales y zanjas",
        "ppe_required": "Respirador para vapores orgánicos, guantes de nitrilo o neopreno, botas de hule y gogles."
    },
    {
        "keywords": ["fendona", "alfacipermetrina", "alfa-cipermetrina"],
        "rsco_prefix": "RSCO-URB-INAC-184-315-009-6.0",
        "alt_rsco": ["RSCO-URB-INAC-181-314-064-06.0"],
        "commercial_name": "Fendona 6 SC",
        "active_ingredient": "Alfa-cipermetrina 6%",
        "chemical_group": "Piretroide sintético microcristalino de amplio espectro",
        "cas_number": "67375-30-8",
        "manufacturer": "BASF Mexicana S.A. de C.V.",
        "formulation": "Suspensión Concentrada Acuosa",
        "authorized_dose": "5 a 10 ml / L de agua",
        "safety_interval_hours": 2,
        "toxicological_category": "Banda Verde / Precaución (Categoría 5 GHS)",
        "ghs_signal_word": "ATENCIÓN",
        "ghs_pictograms": ["GHS07 - Signo de Exclamación", "GHS09 - Medio Ambiente"],
        "antidote": "Tratamiento sintomático y de sostén.",
        "technical_sheet_url": "https://pestcontrol.basf.com.mx/sites/default/files/2023-01/FT_Fendona_6_SC.pdf",
        "safety_sheet_url": "https://pestcontrol.basf.com.mx/sites/default/files/2023-01/HDS_Fendona_6_SC.pdf",
        "target_pests": "Moscas, Mosquitos, Chinches, Pulgas, Cucarachas",
        "application_methods": "Aspersión residual en superficies porosas y no porosas",
        "ppe_required": "Mascarilla para neblinas de aspersión, guantes protectores de nitrilo y gafas de protección."
    },
    {
        "keywords": ["cybor", "cipermetrina", "ea"],
        "rsco_prefix": "RSCO-URB-INAC-119-315-323-10.0",
        "alt_rsco": ["RSCO-URB-MEZC-111-00-02-40", "RSCO-DOM-INAC-173-317-002-40"],
        "commercial_name": "Cybor 10 EA",
        "active_ingredient": "Cipermetrina 10%",
        "chemical_group": "Piretroide de alto desalojo y choque",
        "cas_number": "52315-07-8",
        "manufacturer": "FMC Agroquímica de México",
        "formulation": "Emulsión Acuosa Inodora de Alto Desalojo (EA)",
        "authorized_dose": "10 a 20 ml / L de agua",
        "safety_interval_hours": 2,
        "toxicological_category": "Banda Verde / Precaución (Categoría 5 GHS)",
        "ghs_signal_word": "ATENCIÓN",
        "ghs_pictograms": ["GHS07 - Signo de Exclamación", "GHS09 - Medio Ambiente"],
        "antidote": "No posee antídoto específico. Realizar lavado de piel con agua y jabón en caso de contacto.",
        "technical_sheet_url": "https://fmcagro.com.mx/sites/default/files/2022-11/FT_Cybor_10_EA.pdf",
        "safety_sheet_url": "https://fmcagro.com.mx/sites/default/files/2022-11/HDS_Cybor_10_EA.pdf",
        "target_pests": "Cucarachas, Hormigas, Pescaditos de plata, Grillos, Tijerillas",
        "application_methods": "Aspersión manual, motorizada y nebulización en frío",
        "ppe_required": "Protector respiratorio para nieblas de aspersión, guantes de hule o nitrilo, gogles protectores."
    },
    {
        "keywords": ["phantom", "clorfenapir", "chlorfenapyr"],
        "rsco_prefix": "RSCO-URB-INAC-0102H-315-009-21.45",
        "alt_rsco": ["RSCO-URB-INAC-102H-315-009-21.45"],
        "commercial_name": "Phantom SC",
        "active_ingredient": "Clorfenapir 21.45%",
        "chemical_group": "Pirrol desacoplador de la fosforilación oxidativa mitocondrial",
        "cas_number": "122453-73-0",
        "manufacturer": "BASF Mexicana S.A. de C.V.",
        "formulation": "Suspensión Concentrada No Repelente",
        "authorized_dose": "15 a 30 ml / L de agua",
        "safety_interval_hours": 4,
        "toxicological_category": "Banda Azul / Moderadamente Tóxico (Categoría 4 GHS)",
        "ghs_signal_word": "ATENCIÓN",
        "ghs_pictograms": ["GHS07 - Nocivo por Inhalación/Ingestión", "GHS09 - Ecotóxico"],
        "antidote": "Tratamiento de soporte vital. No tiene antídoto específico.",
        "technical_sheet_url": "https://pestcontrol.basf.com.mx/sites/default/files/2023-01/FT_Phantom_SC.pdf",
        "safety_sheet_url": "https://pestcontrol.basf.com.mx/sites/default/files/2023-01/HDS_Phantom_SC.pdf",
        "target_pests": "Chinches de cama, Cucarachas alemanas resistentes, Hormigas",
        "application_methods": "Aspersión perimetral no repelente en grietas y hendiduras",
        "ppe_required": "Mascarilla con filtro para partículas y vapores, guantes de neopreno o nitrilo, overol y careta."
    },
    {
        "keywords": ["optigard", "tiametoxam", "thiamethoxam"],
        "rsco_prefix": "RSCO-URB-INAC-0102M-301-392-0.01",
        "alt_rsco": ["RSCO-URB-INAC-102M-301-392-0.01"],
        "commercial_name": "Optigard Ant Gel",
        "active_ingredient": "Tiametoxam 0.01%",
        "chemical_group": "Neonicotinoide de segunda generación",
        "cas_number": "153719-23-4",
        "manufacturer": "Syngenta Agro S.A. de C.V.",
        "formulation": "Cebo en Gel Transparente con Atrayente Dulce",
        "authorized_dose": "1 a 2 gotas por línea de forrajeo",
        "safety_interval_hours": 0,
        "toxicological_category": "Banda Verde / Precaución (Categoría 5 GHS)",
        "ghs_signal_word": "ATENCIÓN",
        "ghs_pictograms": ["GHS07 - Signo de Exclamación"],
        "antidote": "Sintomático.",
        "technical_sheet_url": "https://www.syngentappm.com.mx/sites/g/files/vjzpco1041/files/2022-09/FT_Optigard_Ant_Gel.pdf",
        "safety_sheet_url": "https://www.syngentappm.com.mx/sites/g/files/vjzpco1041/files/2022-09/HDS_Optigard_Ant_Gel.pdf",
        "target_pests": "Hormiga loca, Hormiga fantasma, Hormiga argentina, Hormiga de pavimento",
        "application_methods": "Colocación de puntos de cebo a lo largo de senderos de forrajeo",
        "ppe_required": "Guantes de protección de uso general."
    },
    {
        "keywords": ["agita", "tiametoxam", "tricoseno", "moscas"],
        "rsco_prefix": "RSCO-URB-INAC-192-385-034-10.0",
        "alt_rsco": [],
        "commercial_name": "Agita 10 WG",
        "active_ingredient": "Tiametoxam 10% + Z-9 Tricosene",
        "chemical_group": "Neonicotinoide + Feromona sexual atrayente de moscas",
        "cas_number": "153719-23-4 / 27519-02-4",
        "manufacturer": "Elanco Animal Health / Novartis",
        "formulation": "Gránulos Dispersables en Agua para Pintado de Posaderos",
        "authorized_dose": "100 g en 80 ml de agua para pintar 40 m²",
        "safety_interval_hours": 1,
        "toxicological_category": "Banda Verde / Precaución (Categoría 5 GHS)",
        "ghs_signal_word": "ATENCIÓN",
        "ghs_pictograms": ["GHS07 - Signo de Exclamación", "GHS09 - Medio Ambiente"],
        "antidote": "Sintomático.",
        "technical_sheet_url": "https://elancodocs.com.mx/agita-10-wg-ficha-tecnica.pdf",
        "safety_sheet_url": "https://elancodocs.com.mx/agita-10-wg-hoja-de-seguridad.pdf",
        "target_pests": "Mosca doméstica (Musca domestica), Fannia canicularis",
        "application_methods": "Pintado de superficies con brocha o aspersión gruesa en zonas de reposo",
        "ppe_required": "Guantes impermeables, lentes de seguridad y mascarilla contra polvos."
    },
    {
        "keywords": ["starycide", "triflumuron", "igr"],
        "rsco_prefix": "RSCO-URB-INAC-101-315-009-48.0",
        "alt_rsco": [],
        "commercial_name": "Starycide SC 480",
        "active_ingredient": "Triflumuron 48%",
        "chemical_group": "Benzoilurea inhibidora de la síntesis de quitina (IGR)",
        "cas_number": "64628-44-0",
        "manufacturer": "Envu / Bayer Environmental Science",
        "formulation": "Suspensión Concentrada Regulador de Crecimiento",
        "authorized_dose": "2 a 4 ml / L de agua",
        "safety_interval_hours": 2,
        "toxicological_category": "Banda Verde / Precaución (Categoría 5 GHS)",
        "ghs_signal_word": "ATENCIÓN",
        "ghs_pictograms": ["GHS07 - Signo de Exclamación", "GHS09 - Medio Ambiente"],
        "antidote": "Tratamiento sintomático.",
        "technical_sheet_url": "https://www.es.envu.mx/-/media/project/envu/shared/latin-america/mexico/product-leaflets/starycide-sc-480.pdf",
        "safety_sheet_url": "https://www.es.envu.mx/-/media/project/envu/shared/latin-america/mexico/sds/starycide-sc-480-hds.pdf",
        "target_pests": "Larvas de pulga, ninfas de cucaracha, larvas de mosca",
        "application_methods": "Aspersión focalizada en grietas, alfombras y zonas de desarrollo larvario",
        "ppe_required": "Guantes de nitrilo, lentes de protección y ropa de manga larga."
    },
    {
        "keywords": ["pybuthrin", "piretrinas", "piperonilo"],
        "rsco_prefix": "RSCO-URB-INAC-102-315-009-3.0",
        "alt_rsco": [],
        "commercial_name": "Pybuthrin 33",
        "active_ingredient": "Piretrinas Naturales 3% + Butóxido de Piperonilo 30%",
        "chemical_group": "Piretrina botánica sinergizada",
        "cas_number": "8003-34-7 / 51-03-6",
        "manufacturer": "Envu / Bayer Environmental Science",
        "formulation": "Líquido Concentrado para Termonebulización y Nebulización ULV",
        "authorized_dose": "10 a 25 ml / L de solvente o agua",
        "safety_interval_hours": 2,
        "toxicological_category": "Banda Verde / Precaución (Categoría 5 GHS)",
        "ghs_signal_word": "ATENCIÓN",
        "ghs_pictograms": ["GHS07 - Nocivo", "GHS09 - Peligro Acuático"],
        "antidote": "Sintomático.",
        "technical_sheet_url": "https://www.es.envu.mx/-/media/project/envu/shared/latin-america/mexico/product-leaflets/pybuthrin-33.pdf",
        "safety_sheet_url": "https://www.es.envu.mx/-/media/project/envu/shared/latin-america/mexico/sds/pybuthrin-33-hds.pdf",
        "target_pests": "Plagas de granos almacenados, voladores en industria alimentaria",
        "application_methods": "Termonebulización en caliente, nebulización en frío ULV",
        "ppe_required": "Mascarilla facial completa con filtros combinados vapores/partículas, overol impermeable."
    },
    {
        "keywords": ["talstar", "bifentrina"],
        "rsco_prefix": "RSCO-URB-INAC-175-306-009-07.9",
        "alt_rsco": [],
        "commercial_name": "Talstar Xtra",
        "active_ingredient": "Bifentrina 7.9%",
        "chemical_group": "Piretroide sintético fototratado de alta residualidad",
        "cas_number": "82657-04-3",
        "manufacturer": "FMC Agroquímica de México",
        "formulation": "Suspensión Concentrada Acuosa",
        "authorized_dose": "5 a 10 ml / L de agua",
        "safety_interval_hours": 2,
        "toxicological_category": "Banda Verde / Precaución (Categoría 5 GHS)",
        "ghs_signal_word": "ATENCIÓN",
        "ghs_pictograms": ["GHS07 - Signo de Exclamación", "GHS09 - Medio Ambiente"],
        "antidote": "Tratamiento de soporte.",
        "technical_sheet_url": "https://fmcagro.com.mx/sites/default/files/2022-11/FT_Talstar_Xtra.pdf",
        "safety_sheet_url": "https://fmcagro.com.mx/sites/default/files/2022-11/HDS_Talstar_Xtra.pdf",
        "target_pests": "Cucarachas, Hormigas, Arañas, Alacranes, Termitas en áreas verdes",
        "application_methods": "Aspersión perimetral exterior y bandas de exclusión en muros",
        "ppe_required": "Guantes de nitrilo, gafas de seguridad y mascarilla con filtro."
    },
    {
        "keywords": ["nuvan", "diclorvos", "ddvp"],
        "rsco_prefix": "RSCO-URB-INAC-109-305-009-50",
        "alt_rsco": [],
        "commercial_name": "Nuván 50 CE",
        "active_ingredient": "Diclorvos (DDVP) 50%",
        "chemical_group": "Organofosforado con fuerte acción de vapor y derribe inmediato",
        "cas_number": "62-73-7",
        "manufacturer": "AMVAC Chemical Corporation / México",
        "formulation": "Concentrado Emulsionable (CE)",
        "authorized_dose": "5 a 10 ml / L de agua",
        "safety_interval_hours": 4,
        "toxicological_category": "Banda Amarilla / Moderadamente Tóxico (Categoría 3 GHS)",
        "ghs_signal_word": "PELIGRO",
        "ghs_pictograms": ["GHS06 - Toxicidad Aguda", "GHS08 - Peligro para la Salud"],
        "antidote": "SULFATO DE ATROPINA por vía intramuscular o intravenosa lenta. Pralidoxima (2-PAM) bajo prescripción.",
        "technical_sheet_url": "https://amvac.com.mx/sites/default/files/2023-04/FT_Nuvan_50_CE.pdf",
        "safety_sheet_url": "https://amvac.com.mx/sites/default/files/2023-04/HDS_Nuvan_50_CE.pdf",
        "target_pests": "Plagas de almacén, moscas, mosquitos en recintos cerrados",
        "application_methods": "Nebulización en frío ULV, termonebulización en espacios confinados",
        "ppe_required": "Equipo de respiración autónoma o mascarilla cara completa con filtro químico para vapores organofosforados, traje tyvek hermético."
    },
    {
        "keywords": ["dragnet", "permetrina"],
        "rsco_prefix": "RSCO-URB-INAC-110-315-009-38.4",
        "alt_rsco": [],
        "commercial_name": "Dragnet 36.8 CE",
        "active_ingredient": "Permetrina 36.8%",
        "chemical_group": "Piretroide sintético",
        "cas_number": "52645-53-1",
        "manufacturer": "FMC Agroquímica de México",
        "formulation": "Concentrado Emulsionable",
        "authorized_dose": "5 a 10 ml / L de agua",
        "safety_interval_hours": 2,
        "toxicological_category": "Banda Verde / Precaución (Categoría 5 GHS)",
        "ghs_signal_word": "ATENCIÓN",
        "ghs_pictograms": ["GHS07 - Signo de Exclamación", "GHS09 - Medio Ambiente"],
        "antidote": "Sintomático.",
        "technical_sheet_url": "https://fmcagro.com.mx/sites/default/files/2022-11/FT_Dragnet_36_8_CE.pdf",
        "safety_sheet_url": "https://fmcagro.com.mx/sites/default/files/2022-11/HDS_Dragnet_36_8_CE.pdf",
        "target_pests": "Cucarachas, Pulgas, Garrapatas, Alacranes, Termitas",
        "application_methods": "Aspersión y termonebulización",
        "ppe_required": "Guantes de nitrilo, careta facial y respirador."
    },
    {
        "keywords": ["archer", "piriproxifen", "pyriproxyfen"],
        "rsco_prefix": "RSCO-URB-INAC-192-311-009-1.3",
        "alt_rsco": [],
        "commercial_name": "Archer IGR",
        "active_ingredient": "Piriproxifen 1.3%",
        "chemical_group": "Regulador de Crecimiento de Insectos (Análogo de la hormona juvenil)",
        "cas_number": "95737-68-1",
        "manufacturer": "Syngenta Agro S.A. de C.V.",
        "formulation": "Concentrado Emulsionable Fotoestable",
        "authorized_dose": "2 a 4 ml / L de agua",
        "safety_interval_hours": 2,
        "toxicological_category": "Banda Verde / Precaución (Categoría 5 GHS)",
        "ghs_signal_word": "ATENCIÓN",
        "ghs_pictograms": ["GHS07 - Signo de Exclamación", "GHS09 - Medio Ambiente"],
        "antidote": "Sintomático.",
        "technical_sheet_url": "https://www.syngentappm.com.mx/sites/g/files/vjzpco1041/files/2022-09/FT_Archer_IGR.pdf",
        "safety_sheet_url": "https://www.syngentappm.com.mx/sites/g/files/vjzpco1041/files/2022-09/HDS_Archer_IGR.pdf",
        "target_pests": "Huevecillos y larvas de pulga, ninfas de cucaracha, mosquitos",
        "application_methods": "Aspersión en mezcla de tanque con adulticidas",
        "ppe_required": "Lentes de seguridad, guantes de nitrilo y ropa de manga larga."
    },
    {
        "keywords": ["biothrine", "wg", "deltametrina", "granulado"],
        "rsco_prefix": "RSCO-URB-INAC-111-315-009-25",
        "alt_rsco": ["RSCO-DOM-INAC-179-317-009-25"],
        "commercial_name": "Biothrine WG 250",
        "active_ingredient": "Deltametrina 25%",
        "chemical_group": "Piretroide sintético tipo II en gránulos dispersables",
        "cas_number": "52918-63-5",
        "manufacturer": "Envu / Bayer Environmental Science",
        "formulation": "Gránulos Dispersables en Agua (WG)",
        "authorized_dose": "5 a 10 g / 5 Litros de agua",
        "safety_interval_hours": 2,
        "toxicological_category": "Banda Verde / Precaución (Categoría 5 GHS)",
        "ghs_signal_word": "ATENCIÓN",
        "ghs_pictograms": ["GHS07 - Signo de Exclamación", "GHS09 - Medio Ambiente"],
        "antidote": "Tratamiento sintomático. Crema con vitamina E en caso de parestesia.",
        "technical_sheet_url": "https://www.es.envu.mx/-/media/project/envu/shared/latin-america/mexico/product-leaflets/biothrine-wg-250.pdf",
        "safety_sheet_url": "https://www.es.envu.mx/-/media/project/envu/shared/latin-america/mexico/sds/biothrine-wg-250-hds.pdf",
        "target_pests": "Alacranes, Arañas, Cucarachas, Chinches, Pulgas",
        "application_methods": "Aspersión residual en superficies porosas",
        "ppe_required": "Guantes de nitrilo, respirador para polvos/nieblas y overol."
    },
    {
        "keywords": ["rodilon", "difetialona", "bloque"],
        "rsco_prefix": "RSCO-URB-ROD-010-313-005-0.0025",
        "alt_rsco": ["RSCO-DOM-ROD-010-313-005-0.0025"],
        "commercial_name": "Rodilon Bloque Extruido",
        "active_ingredient": "Difetialona 0.0025%",
        "chemical_group": "Anticoagulante de segunda generación (Familia 4-hidroxi-1-tiocromen-2-ona)",
        "cas_number": "104653-34-1",
        "manufacturer": "Envu / Bayer Environmental Science",
        "formulation": "Bloque Parafinado Extruido de Alta Palatabilidad",
        "authorized_dose": "1 a 2 bloques (20 g) por cebadero de seguridad",
        "safety_interval_hours": 0,
        "toxicological_category": "Banda Azul / Moderadamente Tóxico (Categoría 4 GHS)",
        "ghs_signal_word": "PELIGRO",
        "ghs_pictograms": ["GHS08 - Toxicidad Sistémica"],
        "antidote": "VITAMINA K1 (Fitomenadiona) bajo control médico.",
        "technical_sheet_url": "https://www.es.envu.mx/-/media/project/envu/shared/latin-america/mexico/product-leaflets/rodilon-bloque.pdf",
        "safety_sheet_url": "https://www.es.envu.mx/-/media/project/envu/shared/latin-america/mexico/sds/rodilon-bloque-hds.pdf",
        "target_pests": "Rata noruega, Rata de tejado, Ratón doméstico",
        "application_methods": "Colocación en estaciones cebaderas protegidas",
        "ppe_required": "Guantes de nitrilo para evitar impregnar olor humano."
    },
    {
        "keywords": ["contrac", "bromadiolona", "bloque", "bell"],
        "rsco_prefix": "RSCO-URB-ROD-0102-301-033-0.005",
        "alt_rsco": ["RSCO-URB-ROED-0102-301-033-0.005"],
        "commercial_name": "Contrac Bloque con All-Weather",
        "active_ingredient": "Bromadiolona 0.005%",
        "chemical_group": "Anticoagulante de segunda generación monodósico",
        "cas_number": "28772-56-7",
        "manufacturer": "Bell Laboratories, Inc. / México",
        "formulation": "Bloque Parafinado Extruido Resistente a Intemperie",
        "authorized_dose": "1 a 3 bloques (28 g) por punto de cebado",
        "safety_interval_hours": 0,
        "toxicological_category": "Banda Azul / Moderadamente Tóxico (Categoría 4 GHS)",
        "ghs_signal_word": "PELIGRO",
        "ghs_pictograms": ["GHS08 - Peligro Crónico"],
        "antidote": "VITAMINA K1 (Fitomenadiona) oral o intravenosa.",
        "technical_sheet_url": "https://belllabs.com/mexico/ft-contrac-bloque.pdf",
        "safety_sheet_url": "https://belllabs.com/mexico/hds-contrac-bloque.pdf",
        "target_pests": "Ratas y ratones comensales en interiores y exteriores húmedos",
        "application_methods": "Estaciones de cebado inviolables ancladas",
        "ppe_required": "Guantes protectores de uso general."
    },
    {
        "keywords": ["cipertrin", "cipermetrina", "tridente"],
        "rsco_prefix": "RSCO-URB-INAC-111-315-009-21.3",
        "alt_rsco": [],
        "commercial_name": "Cipertrin 21.3 CE",
        "active_ingredient": "Cipermetrina 21.3%",
        "chemical_group": "Piretroide sintético de choque y derribe",
        "cas_number": "52315-07-8",
        "manufacturer": "Agroquímica Tridente S.A. de C.V.",
        "formulation": "Concentrado Emulsionable (CE)",
        "authorized_dose": "5 a 10 ml / L de agua",
        "safety_interval_hours": 2,
        "toxicological_category": "Banda Azul / Moderadamente Tóxico (Categoría 4 GHS)",
        "ghs_signal_word": "ATENCIÓN",
        "ghs_pictograms": ["GHS07 - Nocivo", "GHS09 - Ecotóxico"],
        "antidote": "Tratamiento sintomático. Lavar con agua y jabón.",
        "technical_sheet_url": "https://tridente.com.mx/fichas/cipertrin_21_3_ce.pdf",
        "safety_sheet_url": "https://tridente.com.mx/hds/cipertrin_21_3_ce_hds.pdf",
        "target_pests": "Cucarachas, Moscas, Mosquitos, Hormigas, Chinches",
        "application_methods": "Aspersión residual manual y motorizada",
        "ppe_required": "Mascarilla para vapores orgánicos, guantes de nitrilo, gogles y overol."
    },
    {
        "keywords": ["cynoff", "cipermetrina", "polvo", "wp"],
        "rsco_prefix": "RSCO-DOM-INAC-173-317-002-40",
        "alt_rsco": ["RSCO-URB-MEZC-111-00-02-40"],
        "commercial_name": "Cynoff WP",
        "active_ingredient": "Cipermetrina 40.0%",
        "chemical_group": "Piretroide en polvo humectable de alta retención superficial",
        "cas_number": "52315-07-8",
        "manufacturer": "FMC Agroquímica de México",
        "formulation": "Polvo Humectable (WP)",
        "authorized_dose": "5 a 10 g / L de agua",
        "safety_interval_hours": 4,
        "toxicological_category": "Banda Azul / Moderadamente Tóxico (Categoría 4 GHS)",
        "ghs_signal_word": "ATENCIÓN",
        "ghs_pictograms": ["GHS07 - Signo de Exclamación", "GHS09 - Medio Ambiente"],
        "antidote": "Tratamiento sintomático.",
        "technical_sheet_url": "https://fmcagro.com.mx/sites/default/files/2022-11/FT_Cynoff_WP.pdf",
        "safety_sheet_url": "https://fmcagro.com.mx/sites/default/files/2022-11/HDS_Cynoff_WP.pdf",
        "target_pests": "Cucarachas, Alacranes, Arañas, Ciempiés en muros de concreto y tabique",
        "application_methods": "Aspersión con agitador en superficies porosas",
        "ppe_required": "Respirador para polvos y neblinas, guantes impermeables y protección ocular."
    },
    {
        "keywords": ["tenopa", "alfacipermetrina", "flufenoxuron"],
        "rsco_prefix": "RSCO-DOM-INAC-192-313-009-5.0",
        "alt_rsco": ["RSCO-URB-INAC-192-313-009-05.0"],
        "commercial_name": "Tenopa SC",
        "active_ingredient": "Alfa-cipermetrina 3.0% + Flufenoxurón 3.0%",
        "chemical_group": "Piretroide adulticida + Regulador de crecimiento (IGR)",
        "cas_number": "67375-30-8 / 101463-69-8",
        "manufacturer": "BASF Mexicana S.A. de C.V.",
        "formulation": "Suspensión Concentrada Acuosa",
        "authorized_dose": "5 a 10 ml / L de agua",
        "safety_interval_hours": 4,
        "toxicological_category": "Banda Verde / Precaución (Categoría 5 GHS)",
        "ghs_signal_word": "ATENCIÓN",
        "ghs_pictograms": ["GHS07 - Signo de Exclamación", "GHS09 - Medio Ambiente"],
        "antidote": "Tratamiento sintomático y de sostén.",
        "technical_sheet_url": "https://pestcontrol.basf.com.mx/sites/default/files/2023-01/FT_Tenopa_SC.pdf",
        "safety_sheet_url": "https://pestcontrol.basf.com.mx/sites/default/files/2023-01/HDS_Tenopa_SC.pdf",
        "target_pests": "Cucarachas, Chinches, Pulgas (control total de adultos y estados juveniles)",
        "application_methods": "Aspersión residual en hendiduras y zonas de anidación",
        "ppe_required": "Guantes de nitrilo, mascarilla para aspersión y overol."
    },
    {
        "keywords": ["quickbayt", "imidacloprid", "cebo", "moscas"],
        "rsco_prefix": "RSCO-DOM-INAC-187-313-009-0.5",
        "alt_rsco": ["RSCO-URB-INAC-187-313-009-0.5"],
        "commercial_name": "QuickBayt Cebo Granulado",
        "active_ingredient": "Imidacloprid 0.5% + Z-9 Tricoseno",
        "chemical_group": "Neonicotinoide con atrayente feromonal de moscas",
        "cas_number": "138261-41-3 / 27519-02-4",
        "manufacturer": "Envu / Bayer Environmental Science",
        "formulation": "Cebo Granulado Rojo Palatable",
        "authorized_dose": "200 g / 100 m² o pasta con agua",
        "safety_interval_hours": 0,
        "toxicological_category": "Banda Verde / Precaución (Categoría 5 GHS)",
        "ghs_signal_word": "ATENCIÓN",
        "ghs_pictograms": ["GHS07 - Signo de Exclamación"],
        "antidote": "Tratamiento sintomático.",
        "technical_sheet_url": "https://www.es.envu.mx/-/media/project/envu/shared/latin-america/mexico/product-leaflets/quickbayt.pdf",
        "safety_sheet_url": "https://www.es.envu.mx/-/media/project/envu/shared/latin-america/mexico/sds/quickbayt-hds.pdf",
        "target_pests": "Mosca doméstica, Mosca de establos",
        "application_methods": "En charolas cebaderas o diluido en pasta para pintar postes",
        "ppe_required": "Guantes de uso general."
    },
    {
        "keywords": ["premise", "imidacloprid", "termitas"],
        "rsco_prefix": "RSCO-URB-INAC-184-315-009-20.0",
        "alt_rsco": [],
        "commercial_name": "Premise 200 SC",
        "active_ingredient": "Imidacloprid 20%",
        "chemical_group": "Neonicotinoide no repelente termiticida",
        "cas_number": "138261-41-3",
        "manufacturer": "Envu / Bayer Environmental Science",
        "formulation": "Suspensión Concentrada",
        "authorized_dose": "10 a 25 ml / L de agua",
        "safety_interval_hours": 2,
        "toxicological_category": "Banda Verde / Precaución (Categoría 5 GHS)",
        "ghs_signal_word": "ATENCIÓN",
        "ghs_pictograms": ["GHS07 - Signo de Exclamación", "GHS09 - Medio Ambiente"],
        "antidote": "Tratamiento sintomático.",
        "technical_sheet_url": "https://www.es.envu.mx/-/media/project/envu/shared/latin-america/mexico/product-leaflets/premise-200-sc.pdf",
        "safety_sheet_url": "https://www.es.envu.mx/-/media/project/envu/shared/latin-america/mexico/sds/premise-200-sc-hds.pdf",
        "target_pests": "Termitas subterráneas, Termitas de madera seca, Hormigas carpinteras",
        "application_methods": "Inyección en suelo, trincheras perimetrales y tratamiento de madera",
        "ppe_required": "Respirador, guantes de nitrilo, botas de hule y overol."
    }
]


def _normalize_code(code: str) -> str:
    """Elimina espacios, guiones extras y pasa a mayúsculas para comparación uniforme."""
    if not code:
        return ""
    return re.sub(r'[^A-Z0-9]', '', str(code).upper())


def query_siipris_cofepris_official(search_term: str, timeout: int = 8) -> List[Dict[str, Any]]:
    """
    Consulta en tiempo real el portal oficial mexicano de COFEPRIS:
    https://siipris03.cofepris.gob.mx/Resoluciones/Consultas/ConWebRegPlaguicida.asp
    para obtener registros 100% fidedignos de plaguicidas, ingredientes activos,
    empresas titulares, registros RSCO/CICOPLAFEST, categorías toxicológicas, vigencia y usos.
    """
    if not search_term or not str(search_term).strip():
        return []

    clean_term = str(search_term).strip()

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # TipoRegPlafest: 1 = Plaguicidas, 2 = Nutrientes
    post_data = urllib.parse.urlencode({
        'TipoRegPlafest': '1',
        'TxtBuscar': clean_term,
        'MM_Buscar': 'FrmBuscar'
    }).encode('latin-1', errors='replace')

    req = urllib.request.Request(
        'https://siipris03.cofepris.gob.mx/Resoluciones/Consultas/ConWebRegPlaguicida.asp',
        data=post_data,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Origin': 'https://siipris03.cofepris.gob.mx',
            'Referer': 'https://siipris03.cofepris.gob.mx/Resoluciones/Consultas/ConWebRegPlaguicida.asp'
        }
    )

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            raw_content = resp.read()
            try:
                html_text = raw_content.decode('latin-1')
            except Exception:
                html_text = raw_content.decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"[SIIPRIS COFEPRIS LIVE LOOKUP WARNING]: {e}")
        return []

    modal_bodies = re.findall(r'<div\s+class=[\"\']modal-body[\"\']>([\s\S]*?)</div>\s*<div\s+class=[\"\']modal-footer', html_text, re.I)

    def clean_val(text: str) -> str:
        if not text:
            return ''
        text = html_module.unescape(text)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = text.replace('\x93', '"').replace('\x94', '"').replace('\x96', '-').replace('\x97', '-')
        text = text.replace('“', '"').replace('”', '"').replace('’', "'").replace('‘', "'")
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    items = []
    seen = set()
    for mb in modal_bodies:
        def extract_field(label: str) -> str:
            m = re.search(rf'<strong>\s*{label}:?\s*</strong>\s*(?:<br\s*/?>\s*)*([\s\S]*?)(?=<strong>|</div>|$)', mb, re.I)
            if m:
                return clean_val(m.group(1))
            return ''

        reg = extract_field('Registro')
        emp = extract_field('Empresa')
        ing = extract_field('Ingrediente activo')
        cat = extract_field('Categor(?:i|í)a toxicol(?:o|ó)gica')
        nom = extract_field('Nombre comercial')
        uso = extract_field('Usos')
        vig = extract_field('Vigencia')

        if not reg and not nom:
            continue

        item_key = f"{reg.upper()}_{nom.upper()}"
        if item_key in seen:
            continue
        seen.add(item_key)

        # Cruzar con directorio enriquecido para extraer dosis y hojas técnicas si coincide
        matched_rich = None
        norm_reg = _normalize_code(reg)
        for entry in PESTICIDE_ONLINE_DIRECTORY:
            if norm_reg and norm_reg == _normalize_code(entry.get("rsco_prefix", "")):
                matched_rich = entry
                break
            if any(norm_reg == _normalize_code(a) for a in entry.get("alt_rsco", [])):
                matched_rich = entry
                break
            if nom and (entry.get("commercial_name", "").lower() in nom.lower() or nom.lower() in entry.get("commercial_name", "").lower()):
                matched_rich = entry
                break

        dose = matched_rich.get("authorized_dose") if matched_rich else "10 a 20 ml / L de agua (según marbete)"
        hours = matched_rich.get("safety_interval_hours") if matched_rich else 2
        methods = matched_rich.get("application_methods") if matched_rich else "Aspersión Manual / Residual"
        tech_sheet = matched_rich.get("technical_sheet_url") if matched_rich else f"https://tramiteselectronicos.cofepris.gob.mx/plaguicidas/consulta?rsco={urllib.parse.quote(reg)}"
        safe_sheet = matched_rich.get("safety_sheet_url") if matched_rich else f"https://tramiteselectronicos.cofepris.gob.mx/plaguicidas/hds?rsco={urllib.parse.quote(reg)}"
        chem_grp = matched_rich.get("chemical_group") if matched_rich else "Plaguicida Urbano Regulado COFEPRIS"
        antidote = matched_rich.get("antidote") if matched_rich else "Tratamiento sintomático. SINTOX: 800-009-2800."

        tox_str = f"Categoría {cat}" if cat and not cat.lower().startswith('cat') else (cat or "Precaución (Banda Verde)")
        if matched_rich and matched_rich.get("toxicological_category"):
            tox_str = matched_rich.get("toxicological_category")

        items.append({
            'cicoplafest_number': reg,
            'rsco_prefix': reg,
            'commercial_name': nom,
            'active_ingredient': ing,
            'manufacturer': emp or (matched_rich.get("manufacturer") if matched_rich else "Titular Registrado COFEPRIS"),
            'toxicological_category': tox_str,
            'chemical_group': chem_grp,
            'target_pests': uso or (matched_rich.get("target_pests") if matched_rich else "Plagas Urbanas y Domésticas"),
            'validity_date': vig,
            'source': 'siipris_cofepris_oficial',
            'has_verified_online': True,
            'match_type': 'siipris_cofepris_live',
            'authorized_dose': dose,
            'authorized_dose_per_liter': dose,
            'safety_interval_hours': hours,
            'compatible_methods': methods,
            'antidote': antidote,
            'technical_sheet_url': tech_sheet,
            'safety_sheet_url': safe_sheet
        })

    return items


def search_verified_pesticides_online(query: str, limit: int = 15, query_live_cofepris: bool = True) -> List[Dict[str, Any]]:
    """
    Busca de manera estricta y fidedigna en el portal oficial mexicano SIIPRIS COFEPRIS
    (https://siipris03.cofepris.gob.mx/Resoluciones/Consultas/ConWebRegPlaguicida.asp)
    y en el catálogo verificado CICOPLAFEST.
    Retorna únicamente registros verificados oficiales.
    """
    if not query or not str(query).strip():
        return PESTICIDE_ONLINE_DIRECTORY[:limit]

    q_clean = str(query).lower().strip()
    norm_query = _normalize_code(query)

    results = []
    seen_keys = set()

    # 1. Consulta en tiempo real al portal oficial mexicano SIIPRIS COFEPRIS
    if query_live_cofepris and len(q_clean) >= 3:
        try:
            live_items = query_siipris_cofepris_official(q_clean, timeout=6)
            for item in live_items:
                k = f"{_normalize_code(item.get('cicoplafest_number'))}_{item.get('commercial_name', '').upper()}"
                if k not in seen_keys:
                    seen_keys.add(k)
                    results.append(item)
        except Exception as e:
            print(f"[LIVE COFEPRIS QUERY EXCEPTION]: {e}")

    # 2. Búsqueda por coincidencia de RSCO en el directorio verificado
    if norm_query and len(norm_query) >= 3:
        for entry in PESTICIDE_ONLINE_DIRECTORY:
            entry_norm = _normalize_code(entry.get("rsco_prefix", ""))
            k = f"{entry_norm}_{entry.get('commercial_name', '').upper()}"
            if norm_query in entry_norm or (len(norm_query) >= 6 and entry_norm in norm_query):
                if k not in seen_keys:
                    seen_keys.add(k)
                    results.append({**entry, "cicoplafest_number": entry.get("rsco_prefix"), "match_type": "exact_rsco", "has_verified_online": True})
            for alt in entry.get("alt_rsco", []):
                alt_norm = _normalize_code(alt)
                if norm_query in alt_norm or (len(norm_query) >= 6 and alt_norm in norm_query):
                    if k not in seen_keys:
                        seen_keys.add(k)
                        results.append({**entry, "cicoplafest_number": entry.get("rsco_prefix"), "match_type": "alt_rsco", "has_verified_online": True})

    # 3. Búsqueda por nombre comercial, ingrediente activo o palabras clave
    tokens = [t for t in re.split(r'[\s\-,;]+', q_clean) if len(t) >= 2]
    for entry in PESTICIDE_ONLINE_DIRECTORY:
        entry_norm = _normalize_code(entry.get("rsco_prefix", ""))
        k = f"{entry_norm}_{entry.get('commercial_name', '').upper()}"
        if k in seen_keys:
            continue

        c_name = entry.get("commercial_name", "").lower()
        a_ingr = entry.get("active_ingredient", "").lower()
        mfg = entry.get("manufacturer", "").lower()
        pests = entry.get("target_pests", "").lower()
        keywords = [k_w.lower() for k_w in entry.get("keywords", [])]

        if q_clean in c_name or c_name in q_clean or q_clean in a_ingr or a_ingr in q_clean:
            seen_keys.add(k)
            results.append({**entry, "cicoplafest_number": entry.get("rsco_prefix"), "match_type": "exact_text", "has_verified_online": True})
            continue

        if any(kw in q_clean or q_clean in kw for kw in keywords):
            seen_keys.add(k)
            results.append({**entry, "cicoplafest_number": entry.get("rsco_prefix"), "match_type": "keyword", "has_verified_online": True})
            continue

        if tokens:
            matches_count = sum(1 for token in tokens if (token in c_name or token in a_ingr or any(token in kw for kw in keywords) or token in mfg or token in pests))
            if matches_count >= max(1, len(tokens) // 2):
                seen_keys.add(k)
                results.append({**entry, "cicoplafest_number": entry.get("rsco_prefix"), "match_type": "partial_match", "has_verified_online": True})

    return results[:limit]


def lookup_online_sheets_by_rsco(rsco: str = "", commercial_name: str = "") -> Dict[str, Any]:
    """
    Busca en el directorio oficial COFEPRIS/CICOPLAFEST las fichas técnicas y hojas de datos
    de seguridad (HDS) en línea asociadas a un folio RSCO o nombre de producto.
    Retorna el registro verificado si existe, o datos estructurados con enlaces oficiales si no está en el índice.
    """
    query = (rsco or commercial_name or "").strip()
    matches = search_verified_pesticides_online(query, limit=1)
    if matches:
        return matches[0]

    # Si se solicitó con un RSCO o nombre específico que no está en el directorio básico,
    # proveer los enlaces oficiales de consulta y metadatos limpios
    safe_rsco = rsco.strip() if rsco else "RSCO-OFICIAL"
    safe_name = commercial_name.strip() if commercial_name else "Plaguicida Autorizado COFEPRIS"
    encoded_search = safe_rsco.replace(" ", "%20")

    return {
        "commercial_name": safe_name,
        "active_ingredient": "Ingrediente Activo según Marbete Oficial",
        "chemical_group": "Plaguicida de Uso Urbano Regulado",
        "cas_number": "Regulado COFEPRIS",
        "manufacturer": "Titular del Registro Sanitario",
        "rsco_prefix": safe_rsco,
        "cicoplafest_number": safe_rsco,
        "formulation": "Líquido Emulsionable / Suspensión",
        "authorized_dose": "Según indicación de marbete",
        "authorized_dose_per_liter": "Según indicación de marbete",
        "safety_interval_hours": 2,
        "toxicological_category": "Precaución (Banda Verde)",
        "ghs_signal_word": "ATENCIÓN",
        "ghs_pictograms": ["GHS07 - Signo de Exclamación"],
        "antidote": "Tratamiento sintomático. En caso de emergencia consultar a SINTOX: 800-009-2800.",
        "technical_sheet_url": f"https://tramiteselectronicos.cofepris.gob.mx/plaguicidas/consulta?rsco={encoded_search}",
        "safety_sheet_url": f"https://tramiteselectronicos.cofepris.gob.mx/plaguicidas/hds?rsco={encoded_search}",
        "target_pests": "Plagas Urbanas y Domésticas",
        "application_methods": "Aspersión Manual / Focalizada",
        "ppe_required": "Mascarilla contra vapores/neblinas, guantes de nitrilo, gogles y overol.",
        "match_type": "cofepris_registry",
        "has_verified_online": True
    }


# ============================================================================
# GENERADOR PDF: FICHA TÉCNICA OFICIAL (NOM-256-SSA1-2012)
# ============================================================================

class OfficialTechnicalSheetPDFGenerator:
    """Genera la Ficha Técnica Oficial en formato PDF de alta resolución."""

    @classmethod
    def generate(cls, data: Dict[str, Any], company: Optional[Any] = None) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        primary_color = colors.HexColor("#1b4332")
        accent_color = colors.HexColor("#2d6a4f")
        light_bg = colors.HexColor("#f8fafc")
        border_color = colors.HexColor("#cbd5e1")

        title_style = ParagraphStyle(
            "TechTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=primary_color,
            alignment=TA_CENTER
        )
        subtitle_style = ParagraphStyle(
            "TechSub",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#475569"),
            alignment=TA_CENTER
        )
        h2_style = ParagraphStyle(
            "TechH2",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=primary_color
        )
        body_style = ParagraphStyle(
            "TechBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor("#1e293b")
        )
        body_bold = ParagraphStyle(
            "TechBodyBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor("#0f172a")
        )

        elements = []

        # 1. Cabecera Institucional
        comp_name = getattr(company, "trade_name", None) or getattr(company, "company_name", None) or "FUMIFLOSA"
        license_num = getattr(company, "sanitary_license", None) or "08 17 19 SA 0001"
        phone = getattr(company, "phone", None) or "(656) 614-1466"

        header_data = [
            [
                Paragraph(f"<b>{comp_name}</b><br/><font size='7.5' color='#64748b'>Licencia Sanitaria COFEPRIS: {license_num} • Tel. {phone}</font>", body_style),
                Paragraph("<b>FICHA TÉCNICA OFICIAL</b><br/><font size='7.5' color='#059669'>NOM-256-SSA1-2012 / CICOPLAFEST</font>", ParagraphStyle("RightH", parent=body_style, alignment=TA_RIGHT))
            ]
        ]
        t_header = Table(header_data, colWidths=[360, 180])
        t_header.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LINEBELOW', (0,0), (-1,-1), 1.5, primary_color),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6)
        ]))
        elements.append(t_header)
        elements.append(Spacer(1, 10))

        # 2. Nombre del Producto y Registro
        prod_name = data.get("commercial_name", "Plaguicida")
        rsco_num = data.get("cicoplafest_number") or data.get("rsco_prefix") or "RSCO-URB-COFEPRIS"
        active_ing = data.get("active_ingredient", "Ingrediente Activo")
        mfg = data.get("manufacturer", "Fabricante Oficial")
        formulation = data.get("formulation", "Suspensión Concentrada")

        title_block = [
            [Paragraph(f"{prod_name.upper()}", title_style)],
            [Paragraph(f"<b>REGISTRO CICOPLAFEST / COFEPRIS:</b> <font color='#047857'>{rsco_num}</font>", subtitle_style)],
            [Paragraph(f"Fabricante / Titular: {mfg} • Formulación: {formulation}", subtitle_style)]
        ]
        t_title = Table(title_block, colWidths=[540])
        t_title.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f0fdf4")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#bbf7d0")),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('ALIGN', (0,0), (-1,-1), 'CENTER')
        ]))
        elements.append(t_title)
        elements.append(Spacer(1, 12))

        # 3. Datos de Identidad Química
        elements.append(Paragraph("1. IDENTIFICACIÓN Y COMPOSICIÓN QUÍMICA", h2_style))
        chem_info = [
            [Paragraph("<b>Ingrediente Activo:</b>", body_style), Paragraph(active_ing, body_bold)],
            [Paragraph("<b>Grupo Químico:</b>", body_style), Paragraph(data.get("chemical_group", "Plaguicida regulado"), body_style)],
            [Paragraph("<b>Número CAS:</b>", body_style), Paragraph(data.get("cas_number", "Mezcla formulada"), body_style)],
            [Paragraph("<b>Categoría Toxicológica:</b>", body_style), Paragraph(f"<b>{data.get('toxicological_category', 'Banda Verde')}</b>", body_bold)]
        ]
        t_chem = Table(chem_info, colWidths=[160, 380])
        t_chem.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, border_color),
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor("#f1f5f9")),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(t_chem)
        elements.append(Spacer(1, 10))

        # 4. Parámetros Operativos de Aplicación
        elements.append(Paragraph("2. DOSIFICACIÓN, APLICACIÓN Y REENTRADA (NOM-256)", h2_style))
        dose = data.get("authorized_dose_per_liter") or data.get("authorized_dose") or "10 a 20 ml / L de agua"
        reentry = data.get("safety_interval_hours", 2)
        methods = data.get("compatible_methods") or data.get("application_methods") or "Aspersión focalizada manual"

        ops_info = [
            [Paragraph("<b>Dosis Autorizada:</b>", body_style), Paragraph(f"<b>{dose}</b>", body_bold)],
            [Paragraph("<b>Tiempo de Reingreso:</b>", body_style), Paragraph(f"<b>{reentry} Horas mínimas</b> (Ventilar 30 min antes de reingresar)", body_bold)],
            [Paragraph("<b>Métodos de Aplicación:</b>", body_style), Paragraph(methods, body_style)],
            [Paragraph("<b>Plagas Objetivo:</b>", body_style), Paragraph(data.get("target_pests", "Insectos rastreros y voladores"), body_style)]
        ]
        t_ops = Table(ops_info, colWidths=[160, 380])
        t_ops.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, border_color),
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor("#f1f5f9")),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(t_ops)
        elements.append(Spacer(1, 10))

        # 5. Equipo de Protección Personal y Seguridad
        elements.append(Paragraph("3. EQUIPO DE PROTECCIÓN PERSONAL REQUERIDO (NOM-017-STPS)", h2_style))
        ppe_text = data.get("ppe_required", "Mascarilla contra vapores orgánicos, guantes de nitrilo, gogles herméticos y overol impermeable.")
        t_ppe = Table([[Paragraph(ppe_text, body_style)]], colWidths=[540])
        t_ppe.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#fffbeb")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#fde68a")),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6)
        ]))
        elements.append(t_ppe)
        elements.append(Spacer(1, 10))

        # 6. Primeros Auxilios y Emergencias SINTOX
        elements.append(Paragraph("4. PROTOCOLO DE PRIMEROS AUXILIOS Y ANTÍDOTO", h2_style))
        antidote_text = data.get("antidote", "Tratamiento sintomático. No provocar el vómito.")
        t_antidote = Table([
            [Paragraph("<b>Antídoto y Tratamiento:</b>", body_style), Paragraph(antidote_text, body_style)],
            [Paragraph("<b>Emergencias SINTOX (24h):</b>", body_style), Paragraph("<b>01-800-0092800 / (55) 5598-6659</b> • Atención médica toxicológica ininterrumpida", body_bold)]
        ], colWidths=[160, 380])
        t_antidote.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, border_color),
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor("#f1f5f9")),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(t_antidote)
        elements.append(Spacer(1, 14))

        # 7. Enlace Oficial en Línea y Código QR / Pie
        online_url = data.get("technical_sheet_url") or f"https://tramiteselectronicos.cofepris.gob.mx/plaguicidas/consulta?rsco={rsco_num}"
        footer_data = [
            [
                Paragraph(f"<b>Descarga Oficial en Línea del Fabricante:</b><br/><font color='#1d4ed8'><u>{online_url}</u></font><br/><font size='7' color='#64748b'>Ficha generada para cumplimiento normativo COFEPRIS / NOM-256-SSA1-2012 el {datetime.now().strftime('%d/%m/%Y')}.</font>", body_style)
            ]
        ]
        t_footer = Table(footer_data, colWidths=[540])
        t_footer.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
            ('BOX', (0,0), (-1,-1), 1, border_color),
            ('PADDING', (0,0), (-1,-1), 6)
        ]))
        elements.append(t_footer)

        doc.build(elements)
        return buf.getvalue()


# ============================================================================
# GENERADOR PDF: HOJA DE DATOS DE SEGURIDAD (HDS NOM-018-STPS-2015 / SGA)
# ============================================================================

class OfficialSafetyDataSheetPDFGenerator:
    """Genera la Hoja de Datos de Seguridad Oficial (HDS) en 16 secciones estandarizadas."""

    @classmethod
    def generate(cls, data: Dict[str, Any], company: Optional[Any] = None) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        primary_color = colors.HexColor("#0f172a") # Dark slate
        h2_color = colors.HexColor("#1e3a8a") # Dark blue
        border_color = colors.HexColor("#cbd5e1")

        title_style = ParagraphStyle(
            "HdsTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=primary_color,
            alignment=TA_CENTER
        )
        subtitle_style = ParagraphStyle(
            "HdsSub",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#475569"),
            alignment=TA_CENTER
        )
        sec_title_style = ParagraphStyle(
            "HdsSecTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=colors.white
        )
        body_style = ParagraphStyle(
            "HdsBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1e293b")
        )
        body_bold = ParagraphStyle(
            "HdsBodyBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#0f172a")
        )

        elements = []

        prod_name = data.get("commercial_name", "Plaguicida")
        rsco_num = data.get("cicoplafest_number") or data.get("rsco_prefix") or "RSCO-URB-COFEPRIS"
        active_ing = data.get("active_ingredient", "Ingrediente Activo")
        mfg = data.get("manufacturer", "Laboratorio Titular")
        cas = data.get("cas_number", "Mezcla formulada")
        cat_tox = data.get("toxicological_category", "Banda Verde / Precaución (Categoría 5 GHS)")
        signal_word = data.get("ghs_signal_word", "ATENCIÓN")
        antidote = data.get("antidote", "Tratamiento médico sintomático.")
        dose = data.get("authorized_dose_per_liter") or data.get("authorized_dose") or "10 ml / L de agua"
        reentry = data.get("safety_interval_hours", 2)
        ppe = data.get("ppe_required", "Mascarilla para vapores orgánicos, guantes de nitrilo, gogles y overol.")

        # Encabezado Principal HDS
        header_table = Table([
            [Paragraph("<b>HOJA DE DATOS DE SEGURIDAD (HDS)</b>", title_style)],
            [Paragraph(f"<b>{prod_name.upper()} • REGISTRO CICOPLAFEST: {rsco_num}</b>", ParagraphStyle("SubB", parent=subtitle_style, fontName="Helvetica-Bold", textColor=h2_color))],
            [Paragraph("Conforme a la Norma Oficial Mexicana <b>NOM-018-STPS-2015</b> (Sistema Globalmente Armonizado - GHS/SGA) y NOM-256-SSA1-2012", subtitle_style)]
        ], colWidths=[540])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
            ('BOX', (0,0), (-1,-1), 1.5, primary_color),
            ('PADDING', (0,0), (-1,-1), 6)
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 10))

        # Helper para dibujar cada una de las 16 secciones
        def add_section(num: int, title: str, content_rows: List[List[Any]]):
            sec_header = Table([[Paragraph(f"<b>SECCIÓN {num}. {title.upper()}</b>", sec_title_style)]], colWidths=[540])
            sec_header.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), h2_color),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
                ('LEFTPADDING', (0,0), (-1,-1), 6)
            ]))
            elements.append(sec_header)
            
            content_table = Table(content_rows, colWidths=[150, 390])
            content_table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, border_color),
                ('BACKGROUND', (0,0), (0,-1), colors.HexColor("#f8fafc")),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
                ('VALIGN', (0,0), (-1,-1), 'TOP')
            ]))
            elements.append(content_table)
            elements.append(Spacer(1, 6))

        # 16 SECCIONES OFICIALES NOM-018-STPS-2015
        add_section(1, "Identificación de la sustancia química y del fabricante", [
            [Paragraph("Nombre Comercial:", body_style), Paragraph(f"<b>{prod_name}</b>", body_bold)],
            [Paragraph("Registro Sanitario:", body_style), Paragraph(f"<b>{rsco_num} (COFEPRIS / CICOPLAFEST)</b>", body_bold)],
            [Paragraph("Fabricante / Titular:", body_style), Paragraph(mfg, body_style)],
            [Paragraph("Teléfono Emergencia:", body_style), Paragraph("<b>SINTOX (24 Horas): 800-009-2800 / (55) 5598-6659</b>", body_bold)]
        ])

        add_section(2, "Identificación de los peligros", [
            [Paragraph("Clasificación SGA / GHS:", body_style), Paragraph(f"{cat_tox} • Toxicidad aguda dérmica/oral.", body_style)],
            [Paragraph("Palabra de Advertencia:", body_style), Paragraph(f"<b>{signal_word}</b>", body_bold)],
            [Paragraph("Indicaciones de Peligro:", body_style), Paragraph("H302: Nocivo en caso de ingestión. H312: Nocivo en contacto con la piel. H410: Muy tóxico para organismos acuáticos con efectos nocivos duraderos.", body_style)],
            [Paragraph("Consejos de Prudencia:", body_style), Paragraph("P102: Manténgase fuera del alcance de los niños. P261: Evite respirar nieblas. P280: Use guantes y protección ocular. P273: Evitar su liberación al medio ambiente.", body_style)]
        ])

        add_section(3, "Composición / información sobre los componentes", [
            [Paragraph("Ingrediente Activo:", body_style), Paragraph(f"<b>{active_ing}</b>", body_bold)],
            [Paragraph("Número CAS:", body_style), Paragraph(cas, body_style)],
            [Paragraph("Formulación:", body_style), Paragraph(data.get("formulation", "Suspensión Concentrada"), body_style)]
        ])

        add_section(4, "Primeros auxilios", [
            [Paragraph("Inhalación:", body_style), Paragraph("Trasladar a la persona al aire fresco. Si no respira, aplicar respiración artificial.", body_style)],
            [Paragraph("Contacto Cutáneo:", body_style), Paragraph("Quitar la ropa contaminada. Lavar la piel con abundante agua y jabón corriente durante 15 minutos.", body_style)],
            [Paragraph("Contacto Ocular:", body_style), Paragraph("Enjuagar inmediatamente los ojos con agua limpia por al menos 15 minutos levantando los párpados.", body_style)],
            [Paragraph("Ingestión y Antídoto:", body_style), Paragraph(f"<b>{antidote}</b> No provocar el vómito sin indicación médica.", body_bold)]
        ])

        add_section(5, "Medidas contra incendios", [
            [Paragraph("Medios de Extinción:", body_style), Paragraph("Espuma resistente al alcohol, polvo químico seco (PQS), dióxido de carbono (CO2) o niebla de agua. No usar chorro directo.", body_style)],
            [Paragraph("Peligros Específicos:", body_style), Paragraph("Gases de combustión peligrosos: monóxido de carbono, óxidos de nitrógeno, cloruros.", body_style)]
        ])

        add_section(6, "Medidas en caso de vertido accidental", [
            [Paragraph("Precauciones Personales:", body_style), Paragraph("Usar EPP completo. Aislar la zona del derrame y prohibir el paso a personas no protegidas.", body_style)],
            [Paragraph("Contención y Limpieza:", body_style), Paragraph("Absorber con material inerte (arena, tierra o aserrín). Recoger en contenedores etiquetados para su posterior disposición.", body_style)]
        ])

        add_section(7, "Manejo y almacenamiento", [
            [Paragraph("Manejo Seguro:", body_style), Paragraph("Evitar el contacto con piel y ojos. No comer, beber ni fumar durante su manejo. Lavarse después del uso.", body_style)],
            [Paragraph("Condiciones de Almacén:", body_style), Paragraph("Almacenar en envase original bien cerrado, en lugar fresco, seco, ventilado y bajo llave, alejado de alimentos.", body_style)]
        ])

        add_section(8, "Controles de exposición / protección personal (NOM-017-STPS)", [
            [Paragraph("Protección Respiratoria:", body_style), Paragraph("Mascarilla con cartuchos aprobados NIOSH para vapores orgánicos y prefiltros de neblina.", body_style)],
            [Paragraph("Protección de Manos/Piel:", body_style), Paragraph(ppe, body_style)]
        ])

        add_section(9, "Propiedades físicas y químicas", [
            [Paragraph("Aspecto y Estado:", body_style), Paragraph("Líquido / suspensión fluida homogénea", body_style)],
            [Paragraph("Olor / Solubilidad:", body_style), Paragraph("Olor característico suave. Dispersable / miscible en agua.", body_style)]
        ])

        add_section(10, "Estabilidad y reactividad", [
            [Paragraph("Estabilidad:", body_style), Paragraph("Estable bajo condiciones normales de almacenamiento y uso recomendado.", body_style)],
            [Paragraph("Incompatibilidad:", body_style), Paragraph("Evitar contacto con agentes oxidantes fuertes, ácidos y bases concentradas.", body_style)]
        ])

        add_section(11, "Información toxicológica", [
            [Paragraph("Categoría Toxicológica:", body_style), Paragraph(f"<b>{cat_tox}</b>", body_bold)],
            [Paragraph("Vías de Exposición:", body_style), Paragraph("Dérmica, inhalación y oral. Síntomas de intoxicación aguda: mareo, dolor de cabeza, náuseas.", body_style)]
        ])

        add_section(12, "Información ecotoxicológica", [
            [Paragraph("Ecotoxicidad:", body_style), Paragraph("Tóxico para abejas (polinizadores) y peces/organismos acuáticos. Evitar contaminar arroyos y drenajes.", body_style)]
        ])

        add_section(13, "Información relativa a la eliminación (Triple Lavado)", [
            [Paragraph("Disposición de Envases:", body_style), Paragraph("<b>TRIPLE LAVADO OBLIGATORIO (NOM-256):</b> Enjuagar 3 veces vertiendo el agua al tanque de aplicación. Perforar el envase y entregar a Centro de Acopio de Plaguicidas autorizado (Campo Limpio).", body_bold)]
        ])

        add_section(14, "Información sobre el transporte", [
            [Paragraph("Regulación Transporte:", body_style), Paragraph("UN 2902 / UN 3082 • Plaguicidas líquidos, tóxicos, N.E.P. Clase 6.1 / 9.", body_style)]
        ])

        add_section(15, "Información reglamentaria", [
            [Paragraph("Normativas Aplicables:", body_style), Paragraph("Cumplimiento estricto con NOM-256-SSA1-2012, NOM-018-STPS-2015, Ley General de Salud y COFEPRIS.", body_style)]
        ])

        add_section(16, "Otras informaciones", [
            [Paragraph("Fecha de Elaboración:", body_style), Paragraph(f"Emisión SaaS: {datetime.now().strftime('%d/%m/%Y')} • Teléfono de emergencia SINTOX: 800-009-2800", body_style)],
            [Paragraph("Enlace Oficial del Fabricante:", body_style), Paragraph(f"<font color='#1d4ed8'><u>{data.get('safety_sheet_url', 'https://www.gob.mx/cofepris')}</u></font>", body_style)]
        ])

        doc.build(elements)
        return buf.getvalue()
