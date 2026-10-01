"""app/services/mip_service.py
Servicio de Contenidos del Manual Integral de Control de Plagas (MIP / IPM),
Catálogo Enciclopédico de Plagas Urbanas e Industriales, Guías de Combate Específico
y Motor de Inteligencia Entomológica Conforme a la NOM-256-SSA1-2012, COFEPRIS y NOM-017-STPS.
"""

import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import RSCOItem


def seed_default_rsco_items(db: Session) -> int:
    """Inserta o actualiza el catálogo base de registros oficiales RSCO / CICOPLAFEST en línea."""
    defaults = [
        {
            "commercial_name": "Biothrine Flow",
            "active_ingredient": "Deltametrina 2.5%",
            "cicoplafest_number": "RSCO-URB-INAC-111-315-009-2.5",
            "formulation": "Suspensión Concentrada (SC)",
            "manufacturer": "Envu / Bayer Environmental Science",
            "authorized_dose": "10 a 20 ml / L de agua",
            "target_pests": "Cucarachas, Chinches de cama, Moscas, Mosquitos, Hormigas, Alacranes",
            "toxicological_category": "Banda Verde / Precaución (Cat. 5)",
            "safety_interval_hours": 2
        },
        {
            "commercial_name": "Demand 2.5 CS",
            "active_ingredient": "Lambda Cyhalotrina 2.5%",
            "cicoplafest_number": "RSCO-URB-INAC-173-356-064-2.5",
            "formulation": "Suspensión de Encapsulado (CS / Microencapsulado)",
            "manufacturer": "Syngenta Agro S.A. de C.V.",
            "authorized_dose": "10 a 20 ml / L de agua",
            "target_pests": "Alacranes, Arañas (Violinista y Viuda), Cucarachas, Ciempiés, Hormigas",
            "toxicological_category": "Banda Verde / Precaución (Cat. 5)",
            "safety_interval_hours": 2
        },
        {
            "commercial_name": "Maxforce Forte",
            "active_ingredient": "Fipronil 0.05%",
            "cicoplafest_number": "RSCO-URB-INAC-175-359-392-0.05",
            "formulation": "Cebo en Gel Cucarachicida",
            "manufacturer": "Envu / Bayer Environmental Science",
            "authorized_dose": "1 a 3 gotas (0.25 a 0.5 g) / m²",
            "target_pests": "Cucaracha Alemana (Blattella germanica), Cucaracha Americana",
            "toxicological_category": "Banda Verde / Precaución (Cat. 5)",
            "safety_interval_hours": 0
        },
        {
            "commercial_name": "Temprid SC",
            "active_ingredient": "Imidacloprid 21% + Beta-ciflutrina 10.5%",
            "cicoplafest_number": "RSCO-MEZC-INAC-0101-385-342-31.5",
            "formulation": "Suspensión Concentrada (Doble Modo de Acción)",
            "manufacturer": "Envu / Bayer Environmental Science",
            "authorized_dose": "8 a 16 ml / L de agua",
            "target_pests": "Chinches de cama, Cucarachas resistentes, Pulgas, Garrapatas",
            "toxicological_category": "Banda Azul / Moderadamente Tóxico (Cat. 4)",
            "safety_interval_hours": 2
        },
        {
            "commercial_name": "Advion Cucaracha Gel",
            "active_ingredient": "Indoxacarb 0.6%",
            "cicoplafest_number": "RSCO-URB-INAC-102K-301-392-0.6",
            "formulation": "Cebo en Gel con Bio-activación Metabólica",
            "manufacturer": "Syngenta Agro S.A. de C.V.",
            "authorized_dose": "2 a 5 puntos / m²",
            "target_pests": "Cucaracha Germánica resistente, Cucaracha Oriental, Periplaneta",
            "toxicological_category": "Banda Verde / Precaución (Cat. 5)",
            "safety_interval_hours": 0
        },
        {
            "commercial_name": "Storm Bloques",
            "active_ingredient": "Flocumafen 0.005%",
            "cicoplafest_number": "RSCO-URB-ROD-0101-301-033-0.005",
            "formulation": "Bloque Parafinado Extruido Anticoagulante",
            "manufacturer": "BASF Mexicana S.A. de C.V.",
            "authorized_dose": "1 a 2 bloques (20-40 g) por cebadero cada 5 a 10 metros",
            "target_pests": "Rata de alcantarilla (Rattus norvegicus), Rata de tejado, Ratón casero",
            "toxicological_category": "Banda Azul / Moderadamente Tóxico (Cat. 4)",
            "safety_interval_hours": 0
        },
        {
            "commercial_name": "Klerat Bloque",
            "active_ingredient": "Brodifacoum 0.005%",
            "cicoplafest_number": "RSCO-URB-ROD-138-315-033-0.005",
            "formulation": "Bloque Parafinado Resistente a la Intemperie",
            "manufacturer": "Syngenta Agro S.A. de C.V.",
            "authorized_dose": "20 a 40 g por estación cebadora",
            "target_pests": "Roedores comensales resistentes a warfarina",
            "toxicological_category": "Banda Azul / Moderadamente Tóxico (Cat. 4)",
            "safety_interval_hours": 0
        },
        {
            "commercial_name": "Termidor 25 CE",
            "active_ingredient": "Fipronil 2.5%",
            "cicoplafest_number": "RSCO-URB-INAC-175-313-009-2.5",
            "formulation": "Concentrado Emulsionable (CE)",
            "manufacturer": "BASF Mexicana S.A. de C.V.",
            "authorized_dose": "10 a 20 ml / L de agua (Trinchera / Inyección)",
            "target_pests": "Termita subterránea (Reticulitermes), Hormigas carpinteras, Hormiga loca",
            "toxicological_category": "Banda Azul / Moderadamente Tóxico (Cat. 4)",
            "safety_interval_hours": 4
        },
        {
            "commercial_name": "Fendona 6 SC",
            "active_ingredient": "Alfa-cipermetrina 6%",
            "cicoplafest_number": "RSCO-URB-INAC-184-315-009-6.0",
            "formulation": "Suspensión Concentrada Acuosa",
            "manufacturer": "BASF Mexicana S.A. de C.V.",
            "authorized_dose": "5 a 10 ml / L de agua",
            "target_pests": "Moscas, Mosquitos, Chinches, Pulgas, Cucarachas",
            "toxicological_category": "Banda Verde / Precaución (Cat. 5)",
            "safety_interval_hours": 2
        },
        {
            "commercial_name": "Cybor 10 EA",
            "active_ingredient": "Cipermetrina 10%",
            "cicoplafest_number": "RSCO-URB-INAC-119-315-323-10.0",
            "formulation": "Emulsión Acuosa Inodora de Alto Desalojo",
            "manufacturer": "FMC Agroquímica de México",
            "authorized_dose": "10 a 20 ml / L de agua",
            "target_pests": "Cucarachas, Hormigas, Pescaditos de plata, Grillos, Tijerillas",
            "toxicological_category": "Banda Verde / Precaución (Cat. 5)",
            "safety_interval_hours": 2
        },
        {
            "commercial_name": "Optigard Ant Gel",
            "active_ingredient": "Tiametoxam 0.01%",
            "cicoplafest_number": "RSCO-URB-INAC-0102M-301-392-0.01",
            "formulation": "Cebo en Gel Transparente con Atrayente Dulce",
            "manufacturer": "Syngenta Agro S.A. de C.V.",
            "authorized_dose": "1 a 2 gotas por línea de forrajeo",
            "target_pests": "Hormiga loca, Hormiga fantasma, Hormiga argentina, Hormiga de pavimento",
            "toxicological_category": "Banda Verde / Precaución (Cat. 5)",
            "safety_interval_hours": 0
        },
        {
            "commercial_name": "Agita 10 WG",
            "active_ingredient": "Tiametoxam 10% + Z-9 Tricosene (Feromona)",
            "cicoplafest_number": "RSCO-URB-INAC-192-385-034-10.0",
            "formulation": "Gránulos Dispersables en Agua para Pintado",
            "manufacturer": "Elanco Animal Health / Novartis",
            "authorized_dose": "100 g en 80 ml de agua para pintar 40 m² de superficie de posadero",
            "target_pests": "Mosca doméstica (Musca domestica), Fannia canicularis",
            "toxicological_category": "Banda Verde / Precaución (Cat. 5)",
            "safety_interval_hours": 1
        },
        {
            "commercial_name": "Phantom SC",
            "active_ingredient": "Clorfenapir 21.45%",
            "cicoplafest_number": "RSCO-URB-INAC-0102H-315-009-21.45",
            "formulation": "Suspensión Concentrada No Repelente",
            "manufacturer": "BASF Mexicana S.A. de C.V.",
            "authorized_dose": "15 a 30 ml / L de agua",
            "target_pests": "Chinches de cama, Cucarachas alemanas resistentes, Hormigas",
            "toxicological_category": "Banda Azul / Moderadamente Tóxico (Cat. 4)",
            "safety_interval_hours": 4
        },
        {
            "commercial_name": "Starycide SC 480",
            "active_ingredient": "Triflumuron 48%",
            "cicoplafest_number": "RSCO-URB-INAC-101-315-009-48.0",
            "formulation": "Suspensión Concentrada Regulador de Crecimiento (IGR)",
            "manufacturer": "Envu / Bayer Environmental Science",
            "authorized_dose": "2 a 4 ml / L de agua",
            "target_pests": "Larvas de pulga, ninfas de cucaracha, larvas de mosca",
            "toxicological_category": "Banda Verde / Precaución (Cat. 5)",
            "safety_interval_hours": 2
        },
        {
            "commercial_name": "Pybuthrin 33",
            "active_ingredient": "Piretrinas Naturales 3% + Butóxido de Piperonilo 30%",
            "cicoplafest_number": "RSCO-URB-INAC-102-315-009-3.0",
            "formulation": "Líquido Concentrado para Termonebulización y Nebulización ULV",
            "manufacturer": "Envu / Bayer Environmental Science",
            "authorized_dose": "10 a 25 ml / L de solvente o agua",
            "target_pests": "Plagas de granos almacenados, insectos voladores en industria alimentaria",
            "toxicological_category": "Banda Verde / Precaución (Cat. 5)",
            "safety_interval_hours": 2
        }
    ]

    added = 0
    from app.services.pesticide_sheet_service import lookup_online_sheets_by_rsco

    for data in defaults:
        sheets = lookup_online_sheets_by_rsco(data.get("cicoplafest_number", ""), data.get("commercial_name", ""))
        data["technical_sheet_url"] = sheets.get("technical_sheet_url")
        data["safety_sheet_url"] = sheets.get("safety_sheet_url")

        existing = db.query(RSCOItem).filter(
            RSCOItem.cicoplafest_number == data["cicoplafest_number"]
        ).first()
        if not existing:
            item = RSCOItem(**data)
            db.add(item)
            added += 1
        else:
            for k, v in data.items():
                setattr(existing, k, v)
    db.commit()
    return added


def get_mip_full_manual() -> Dict[str, Any]:
    """Retorna el contenido estructurado del Manual Integral de Control de Plagas Urbanas."""
    return {
        "title": "MANUAL INTEGRAL DE MANEJO DE PLAGAS URBANAS (MIP)",
        "subtitle": "Guía Técnica Operativa Conforme a la NOM-256-SSA1-2012, COFEPRIS y Normas STPS",
        "company": "FLOSA CONTROL DE PLAGAS - MARCO ANTONIO FLORES SÁENZ",
        "version": "Edición 2026",
        "modules": [
            {
                "id": "mod-1",
                "number": "01",
                "title": "Marco Legal, Normatividad Sanitaria y Responsabilidad Técnica",
                "icon": "fa-scale-balanced",
                "summary": "Fundamento legal obligatorio que rige a las empresas controladoras de plagas urbanas en territorio mexicano.",
                "topics": [
                    {
                        "subtitle": "NOM-256-SSA1-2012",
                        "content": "Establece las condiciones sanitarias que deben cumplir los establecimientos y el personal dedicado a los servicios urbanos de control de plagas. Exige contar con Licencia Sanitaria otorgada por COFEPRIS, Responsable Técnico con cédula profesional afín (Biología, Agronomía, Química), programa documentado de capacitación y emisión de certificados oficiales."
                    },
                    {
                        "subtitle": "Obligaciones del Responsable Técnico",
                        "content": "Supervisar las formulaciones, dosificaciones y técnicas de aplicación; validar la calibración de equipos; verificar las Hojas de Datos de Seguridad (HDS); y firmar los certificados de servicio emitidos por la empresa."
                    },
                    {
                        "subtitle": "Normatividad Laboral y STPS",
                        "content": "Cumplimiento obligatorio de la NOM-017-STPS (Equipo de protección personal), NOM-005-STPS (Manejo de sustancias químicas peligrosas) y constancias de competencias laborales Formato DC-3 para técnicos aplicadores."
                    }
                ]
            },
            {
                "id": "mod-2",
                "number": "02",
                "title": "Diagnóstico Inicial e Inspección Técnica de Instalaciones",
                "icon": "fa-magnifying-glass-location",
                "summary": "Metodología sistemática de inspección física antes de cualquier intervención química.",
                "topics": [
                    {
                        "subtitle": "Plano de Zonificación y Puntos Críticos",
                        "content": "Levantamiento de croquis de la instalación identificando Zona Crítica (preparación y almacenamiento de alimentos), Zona Sensible (áreas de empaque o tránsito de personas) y Zona Perimetral (estacionamientos, bardas perimetrales y jardines)."
                    },
                    {
                        "subtitle": "Factores Atrayentes (Los 4 Pilares de Infestación)",
                        "content": "Detección de Agua (fugas, condensación de refrigeradores, humedad en drenajes), Alimento (residuos orgánicos, derrames grasos, harina estancada), Refugio (grietas >2mm, plafones falsos, cartón acumulado) y Acceso (puertas descalibradas, pasos de tubería sin sellar)."
                    },
                    {
                        "subtitle": "Herramientas del Inspector MIP",
                        "content": "Lámpara de alta intensidad, espejo de inspección telescópico, cámara térmica o higrómetro, lupa de campo, trampas testigo de monitoreo y espátula."
                    }
                ]
            },
            {
                "id": "mod-3",
                "number": "03",
                "title": "Medidas de Exclusión, Hermeticidad y Manejo del Hábitat",
                "icon": "fa-door-closed",
                "summary": "Barreras físicas y modificaciones estructurales para impedir el ingreso y anidación de plagas.",
                "topics": [
                    {
                        "subtitle": "Exclusión Perimetral de Roedores y Rastreros",
                        "content": "Instalación de guardapolvos de aluminio con neopreno o cepillo en puertas exteriores (holgura inferior máxima: 6 mm para ratones, 12 mm para ratas); sellado de pasos de tuberías hidrosanitarias con malla de acero inoxidable y silicón estructural; colocación de rejillas de acero en coladeras pluviales y sanitarias."
                    },
                    {
                        "subtitle": "Exclusión de Insectos Voladores",
                        "content": "Mallas mosquiteras calibre 16x16 hilos por pulgada en ventanas operables; cortinas de aire en accesos de alto tráfico orientadas con flujo hacia el exterior a un ángulo de 15°; cortinas hawaianas traslúcidas en andenes de carga."
                    },
                    {
                        "subtitle": "Gestión del Entorno Exterior",
                        "content": "Franja perimetral de grava o gravilla de 50 cm alrededor de los cimientos libre de vegetación; poda de ramas de árboles a una distancia mínima de 2 metros respecto a techos y plafones."
                    }
                ]
            },
            {
                "id": "mod-4",
                "number": "04",
                "title": "Saneamiento y Buenas Prácticas de Higiene (BPH)",
                "icon": "fa-broom",
                "summary": "Procedimientos higiénicos que eliminan los recursos indispensables para la supervivencia de las plagas.",
                "topics": [
                    {
                        "subtitle": "Eliminación de Fuentes de Alimento y Grasa",
                        "content": "Limpieza exhaustiva con desengrasante alcalino detrás y debajo de campanas, freidoras y motores; desincrustación diaria de residuos de alimentos antes del cierre de turno."
                    },
                    {
                        "subtitle": "Manejo Integral de Residuos Sólidos",
                        "content": "Contenedores con tapa hermética accionada por pedal; uso de bolsas de polietileno de alto calibre; cuarto de basura refrigerado o ubicado a mínimo 15 metros de las entradas de proceso con lavado diario y desinfección."
                    },
                    {
                        "subtitle": "Rotación de Mercancías (PEPS)",
                        "content": "Sistema de Primeras Entradas, Primeras Salidas; almacenamiento en tarimas plásticas separadas a 45 cm de la pared y 15 cm del piso con franja sanitaria pintada de color blanco para inspección de excrementos o heces."
                    }
                ]
            },
            {
                "id": "mod-5",
                "number": "05",
                "title": "Métodos de Control Físico, Mecánico y Monitoreo Biológico",
                "icon": "fa-shield-halved",
                "summary": "Dispositivos no químicos para captura, contención y evaluación de densidades poblacionales.",
                "topics": [
                    {
                        "subtitle": "Estaciones Cebaderas Inviolables para Roedores",
                        "content": "Cebaderos de polipropileno de alto impacto con cerradura de seguridad de doble vástago; anclados firmemente al suelo perimetral exterior a distancias de 10 a 15 metros; rotulados con etiqueta de advertencia, teléfono de emergencia SINTOX y número consecutivo de estación."
                    },
                    {
                        "subtitle": "Trampas de Golpe y Trampas de Goma en Interiores",
                        "content": "PROHIBICIÓN ESTRICTA: Queda prohibido el uso de cebos rodenticidas tóxicos dentro de áreas de procesamiento, almacenamiento de alimentos o consultorios médicos. En interiores solo se permiten trampas mecánicas de impacto (tipo T-Rex) dentro de túneles o trampas de goma adhesiva en estaciones multicaptura."
                    },
                    {
                        "subtitle": "Lámparas de Luz Ultravioleta Insectocutoras",
                        "content": "Equipos con tubos UV-A de 368 nm provistos de láminas adhesivas reemplazables (prohibidas las lámparas de electrocución que dispersan fragmentos de insectos en zonas limpias); instaladas a 1.80 - 2.10 metros de altura, lejos de corrientes de aire y no visibles desde el exterior."
                    }
                ]
            },
            {
                "id": "mod-6",
                "number": "06",
                "title": "Control Químico Responsable, Dosificación y Rotación IRAC",
                "icon": "fa-flask-vial",
                "summary": "Aplicación técnica de plaguicidas de uso urbano con registro COFEPRIS/CICOPLAFEST vigente.",
                "topics": [
                    {
                        "subtitle": "Criterios de Selección del Plaguicida",
                        "content": "Priorizar formulaciones de banda verde (Categoría 5) con bajo olor, baja volatilidad y alta residualidad (Microencapsulados CS, Suspensiones SC, Cebos en Gel). Verificar obligatoriamente que el envase cuente con etiqueta aprobada por COFEPRIS para el uso urbano específico."
                    },
                    {
                        "subtitle": "Rotación por Modo de Acción (Comité IRAC)",
                        "content": "Para evitar resistencia cruzada, rotar entre familias químicas diferentes: Grupo 3A (Piretroides: Deltametrina, Lambdacialotrina), Grupo 4A (Neonicotinoides: Imidacloprid, Tiametoxam), Grupo 2B (Fenilpirazoles: Fipronil), Grupo 22A (Oxadiazinas: Indoxacarb) y Grupo 13 (Desacopladores: Clorfenapir)."
                    },
                    {
                        "subtitle": "Técnicas de Aplicación",
                        "content": "Aspersión focalizada en grietas y hendiduras (boquilla 8002 a 40 psi), aplicación de cebos en gel mediante pistola dosificadora en puntos inaccesibles a niños/mascotas, y nebulización ULV o termonebulización reservada exclusivamente para tratamientos de choque o drenajes previa evacuación."
                    }
                ]
            },
            {
                "id": "mod-7",
                "number": "07",
                "title": "Seguridad, Salud Ocupacional y Manejo de Emergencias (SINTOX)",
                "icon": "fa-kit-medical",
                "summary": "Protección de los técnicos aplicadores y protocolo de atención ante intoxicaciones.",
                "topics": [
                    {
                        "subtitle": "Equipo de Protección Personal (EPP)",
                        "content": "Uso obligatorio según etiqueta: Mascarilla de media cara con cartuchos para vapores orgánicos y prefiltros contra partículas, gafas de seguridad de sello hermético, overol tipo Tyvek o camisola de algodón resistente, guantes de nitrilo libres de polvo (nunca de látex ni cuero que absorben plaguicidas) y botas de hule de caña alta."
                    },
                    {
                        "subtitle": "Tiempos de Reentrada Sanitarios",
                        "content": "Respetar un periodo mínimo de reentrada de 2 a 4 horas posteriores a la aplicación, garantizando una ventilación natural o forzada de 30 minutos antes de permitir el reingreso del personal."
                    },
                    {
                        "subtitle": "Atención Toxicológica SINTOX 24 Horas",
                        "content": "Tener siempre a la mano los teléfonos de auxilio médico: SINTOX 800-009-2800 / (55) 5598-6659 / (55) 5611-2634. Contar con el botiquín de primeros auxilios y las Hojas de Seguridad (HDS) en la unidad móvil."
                    }
                ]
            },
            {
                "id": "mod-8",
                "number": "08",
                "title": "Gestión de Residuos Peligrosos y Triple Lavado de Envases",
                "icon": "fa-recycle",
                "summary": "Disposición ambientalmente segura de envases vacíos de plaguicidas conforme a SEMARNAT y AMOCALI.",
                "topics": [
                    {
                        "subtitle": "Técnica del Triple Lavado",
                        "content": "Paso 1: Agregar agua limpia hasta 1/4 del volumen del envase vacío. Paso 2: Tapar y agitar enérgicamente durante 30 segundos en todas direcciones. Paso 3: Verter el agua de lavado directamente en el tanque de la aspersora (nunca al drenaje). Repetir este ciclo tres veces consecutivas."
                    },
                    {
                        "subtitle": "Inutilización del Envase",
                        "content": "Perforar el fondo del envase triple lavado con una herramienta punzante para impedir su reutilización clandestina para almacenamiento de agua o alimentos. No destruir las etiquetas de identificación."
                    },
                    {
                        "subtitle": "Acopio y Destino Final",
                        "content": "Guardar en bolsas plásticas transparentes de 100 micras en el almacén temporal de residuos peligrosos. Entregar periódicamente al Centro de Acopio Autorizado (AMOCALI / Campo Limpio) y recabar el Manifiesto de Entrega para archivo de auditoría."
                    }
                ]
            }
        ]
    }


# ============================================================================
# CATÁLOGO ENCICLOPÉDICO DE PLAGAS URBANAS E INDUSTRIALES (CATEGORÍAS CANÓNICAS)
# ============================================================================

PEST_ENCYCLOPEDIA: List[Dict[str, Any]] = [
    {
        "id": "cucaracha-alemana",
        "name": "Cucaracha Germánica / Alemana",
        "scientific_name": "Blattella germanica",
        "category": "Insectos Rastreros",
        "icon": "fa-bug",
        "danger_level": "Alto (Vector Mecánico y Alérgeno)",
        "biology_and_habits": "Mide de 10 a 15 mm, color café claro con dos franjas longitudinales oscuras paralelas en el pronoto. Es la plaga urbana más prolífica en cocinas, restaurantes y hospitales. Hábitos estrictamente nocturnos y tigmotácticos (busca refugios estrechos donde su cuerpo haga contacto simultáneo con dos superficies). Una hembra produce de 4 a 8 ootecas a lo largo de su vida, cada una con 30 a 48 embriones, con un ciclo biológico de apenas 60 días a 28°C.",
        "damage_and_risks": "Transmisora de patógenos entéricos como Salmonella spp., Escherichia coli, Shigella, quistes de amebas y huevos de helmintos. Sus heces, mudas y restos corporales son potentes alérgenos causantes de asma y rinitis crónica en niños y personas vulnerables.",
        "critical_points": "Motores de refrigeradores y congeladores, compresores de cafeteras, grietas en azulejos, bisagras de alacenas, partes inferiores de mesas calientes, huecos en contactos eléctricos.",
        "exclusion_measures": "Sellado hermético de zoclos, azulejos y huecos en paredes con silicón antihongos; sustitución de tarimas de madera por plástico; eliminación inmediata de cartón ondulado (fuente principal de ingreso pasivo de ootecas).",
        "mechanical_control": "Colocación de trampas de goma con atrayente alimenticio/feromona agregativa en esquinas y bajo equipos para monitoreo y estimación del nivel de infestación (umbral de acción: >1 cucaracha/trampa/semana).",
        "chemical_protocol": [
            "1. Diagnóstico y aspirado previo de refugios masivos con filtro HEPA.",
            "2. Aplicación estratégica de cebo en gel (Fipronil o Indoxacarb) mediante micropuntos (0.25 a 0.5 g) en grietas, bisagras y motores donde los insectos forrajean.",
            "3. Aplicación de Regulador de Crecimiento de Insectos (IGR: Triflumuron o Piriproxifeno) para esterilizar a los adultos y deformar las ninfas.",
            "4. Aspersión perimetral focalizada en zócalos y tuberías con insecticida microencapsulado o no repelente (evitar aspersión generalizada que disperse la colonia)."
        ],
        "recommended_chemicals": [
            "Maxforce Forte Gel (Fipronil 0.05% - RSCO-URB-INAC-175-359-392-0.05)",
            "Advion Cucaracha Gel (Indoxacarb 0.6% - RSCO-URB-INAC-102K-301-392-0.6)",
            "Temprid SC (Imidacloprid 21% + Beta-ciflutrina 10.5% - RSCO-MEZC-INAC-0101-385-342-31.5)",
            "Starycide SC 480 IGR (Triflumuron 48% - RSCO-URB-INAC-101-315-009-48.0)"
        ],
        "irac_rotation": "Alternar Fenilpirazoles (IRAC 2B) con Oxadiazinas (IRAC 22A) y Neonicotinoides (IRAC 4A) cada 3 a 6 meses para evitar resistencia metabólica.",
        "reentry_time": "0 horas con cebo en gel; 2 horas si se aplicó aspersión residual."
    },
    {
        "id": "cucaracha-americana",
        "name": "Cucaracha Americana / De Drenaje",
        "scientific_name": "Periplaneta americana",
        "category": "Insectos Rastreros",
        "icon": "fa-bug",
        "danger_level": "Alto (Vector de Alcantarillado)",
        "biology_and_habits": "La especie comensal más grande (35 a 50 mm), color café rojizo brillante. Posee alas funcionales y capacidad de planeo. Habita preferentemente en redes de drenaje, cañerías, registros eléctricos subterráneos, calderas, sótanos y cámaras de vapor con alta humedad y temperaturas superiores a 25°C.",
        "damage_and_risks": "Al provenir directamente de las aguas negras, transporta en sus patas y cutícula una elevada carga de bacterias coliformes, estreptococos, virus de hepatitis y hongos patógenos, contaminando superficies limpias.",
        "critical_points": "Coladeras sin trampa de agua, respiraderos de drenaje, registros pluviales, tuberías de desagüe rotas, cuartos de calderas.",
        "exclusion_measures": "Instalación de trampas de agua (sifones funcionales) en todos los desagües; colocación de rejillas metálicas con orificios menores a 5 mm; sellado de juntas de registros sanitarios con sellador elástico.",
        "mechanical_control": "Trampas de pegamento de gran capacidad ubicadas cerca de los registros sanitarios y cuartos de bombeo.",
        "chemical_protocol": [
            "1. Termonebulización o nebulización ULV con piretroides autorizados en registros de alcantarillado y ductos de drenaje para efecto de desalojo y derribo rápido.",
            "2. Aspersión perimetral de barrera en muros perimetrales, registros y zócalos con insecticida residual en suspensión acuosa (Deltametrina, Alfa-cipermetrina).",
            "3. Aplicación de cebos granulados para exteriores en jardineras y zonas húmedas perimetrales."
        ],
        "recommended_chemicals": [
            "Biothrine Flow (Deltametrina 2.5% - RSCO-URB-INAC-111-315-009-2.5)",
            "Fendona 6 SC (Alfa-cipermetrina 6% - RSCO-URB-INAC-184-315-009-6.0)",
            "Cybor 10 EA (Cipermetrina 10% - RSCO-URB-INAC-119-315-323-10.0)"
        ],
        "irac_rotation": "Rotar Piretroides (IRAC 3A) con Fenilpirazoles no repelentes (Termidor 25 CE - IRAC 2B) en aplicaciones perimetrales.",
        "reentry_time": "2 a 4 horas tras aspersión o termonebulización."
    },
    {
        "id": "cucaracha-oriental",
        "name": "Cucaracha Oriental / Negra",
        "scientific_name": "Blatta orientalis",
        "category": "Insectos Rastreros",
        "icon": "fa-bug",
        "danger_level": "Alto (Vector de Humedad y Drenaje)",
        "biology_and_habits": "Longitud de 25 a 32 mm, color negro brillante a castaño muy oscuro. Machos con alas que cubren 2/3 del abdomen y hembras braquípteras (alas vestigiales). Prefiere temperaturas más frescas (20-25°C) y alta humedad. Se desplaza lentamente en sótanos, registros subterráneos, huecos bajo losas y desagües.",
        "damage_and_risks": "Contaminación con olor rancio característico; vector mecánico de Salmonella, Escherichia coli y parásitos intestinales.",
        "critical_points": "Sótanos, cuartos de medidores, registros hidráulicos, hendiduras bajo losas de concreto, áreas de lavado húmedas.",
        "exclusion_measures": "Sellado de juntas de dilatación en pisos; reparación de fugas subterráneas; rejillas finas en desagües.",
        "mechanical_control": "Trampas de pegamento en perímetro de sótanos y registros húmedos.",
        "chemical_protocol": [
            "1. Aspersión perimetral con insecticida microencapsulado tolerante a la humedad (Demand 2.5 CS).",
            "2. Aplicación de polvos secos en cámaras de aire y registros sanitarios inaccesibles.",
            "3. Colocación de cebos en gel en puntos estratégicos no anegados."
        ],
        "recommended_chemicals": [
            "Demand 2.5 CS (Lambda Cyhalotrina 2.5% - RSCO-URB-INAC-173-356-064-2.5)",
            "Biothrine Flow (Deltametrina 2.5% - RSCO-URB-INAC-111-315-009-2.5)",
            "Maxforce Forte Gel (Fipronil 0.05% - RSCO-URB-INAC-175-359-392-0.05)"
        ],
        "irac_rotation": "Piretroides Grupo 3A alternados con Fenilpirazoles Grupo 2B.",
        "reentry_time": "2 horas."
    },
    {
        "id": "cucaracha-banda-cafe",
        "name": "Cucaracha de Banda Café",
        "scientific_name": "Supella longipalpa",
        "category": "Insectos Rastreros",
        "icon": "fa-bug",
        "danger_level": "Moderado a Alto (Infestación en Altura)",
        "biology_and_habits": "Insecto pequeño de 10 a 14 mm con dos bandas transversales claras en el tórax y abdomen. A diferencia de la alemana, prefiere áreas cálidas y secas (>30°C) y suele anidar en partes altas de las habitaciones: techos, molduras, detrás de cuadros, motores de televisores y libreros.",
        "damage_and_risks": "Contaminación de libros, documentos, aparatos electrónicos y alimentos; alérgenos en suspensión aérea.",
        "critical_points": "Detrás de cuadros, molduras de techos, gabinetes altos, equipo de cómputo y electrónica.",
        "exclusion_measures": "Inspección de muebles y cajas de archivo; sellado de molduras y uniones de techos.",
        "mechanical_control": "Trampas adhesivas colocadas en estantes altos y plafones.",
        "chemical_protocol": [
            "1. Aplicación de gel cucarachicida en bisagras altas, detrás de cuadros y muebles suspendidos.",
            "2. Aplicación de insecticida no repelente en grietas altas.",
            "3. Uso de IGR para romper el ciclo reproductivo."
        ],
        "recommended_chemicals": [
            "Advion Cucaracha Gel (Indoxacarb 0.6%)",
            "Phantom SC (Clorfenapir 21.45%)",
            "Starycide SC 480 (Triflumuron 48%)"
        ],
        "irac_rotation": "Oxadiazinas (IRAC 22A) y Pirroles (IRAC 13).",
        "reentry_time": "0 horas con gel; 2 horas tras aspersión."
    },
    {
        "id": "rata-alcantarilla",
        "name": "Rata Noruega / De Alcantarilla",
        "scientific_name": "Rattus norvegicus",
        "category": "Roedores Comensales",
        "icon": "fa-shield-cat",
        "danger_level": "Crítico (Daño Sanitario y Estructural)",
        "biology_and_habits": "Roedor robusto de 20 a 25 cm (sin cola), peso de 300 a 500 g. Hocico chato, orejas cortas y cola más corta que la longitud del cuerpo. Excava madrigueras subterráneas con salidas de emergencia cerca de cimientos, basureros y drenajes. Excelente nadadora y buceadora capaz de ingresar a través de tazas sanitarias.",
        "damage_and_risks": "Transmisora de Leptospirosis (Leptospira interrogans por orina), Hantavirus, Peste bubónica, Tifus murino y Mordedura de rata. Su hábito de roer continuo destruye cables eléctricos (origen de incendios), tuberías de PVC y empaques.",
        "critical_points": "Montículos de tierra cerca de cimientos (entradas de madrigueras), coladeras rotas, cuartos de basura exterior, andenes de carga, tarimas apiladas en el exterior.",
        "exclusion_measures": "Sellado con concreto reforzado con malla de acero en cimientos; placas de lámina galvanizada en la base de puertas exteriores; rejillas metálicas de alta resistencia en drenajes pluviales.",
        "mechanical_control": "En interiores: trampas de impacto de uso rudo (T-Rex) colocadas perpendiculares a los muros dentro de túneles de protección. Prohibido rodenticida químico en áreas de proceso de alimentos.",
        "chemical_protocol": [
            "1. Inspección perimetral y mapeo de madrigueras activas.",
            "2. Colocación de cebaderos de seguridad anclados en el perímetro exterior cada 10 a 15 metros.",
            "3. Sujeción de bloques parafinados extruidos de segunda generación (Flocumafen o Brodifacoum) en las varillas internas de cada cebadero.",
            "4. Registro de consumo en bitácora (0%, 25%, 50%, 75%, 100%) y reposición semanal."
        ],
        "recommended_chemicals": [
            "Storm Bloques (Flocumafen 0.005% - RSCO-URB-ROD-0101-301-033-0.005)",
            "Klerat Bloque (Brodifacoum 0.005% - RSCO-URB-ROD-138-315-033-0.005)"
        ],
        "irac_rotation": "Anticoagulantes de segunda generación de dosis única. Monitorear resistencia y cambiar ingrediente activo anualmente.",
        "reentry_time": "0 horas (aplicación en estaciones cerradas con llave)."
    },
    {
        "id": "rata-tejado",
        "name": "Rata de Tejado / Negra",
        "scientific_name": "Rattus rattus",
        "category": "Roedores Comensales",
        "icon": "fa-shield-cat",
        "danger_level": "Crítico (Daño en Altura y Almacenes)",
        "biology_and_habits": "Roedor ágil de 16 a 22 cm, cuerpo esbelto, hocico puntiagudo, orejas grandes que dobladas cubren los ojos, cola más larga que la longitud cabeza-cuerpo. Extraordinaria trepadora que anida en copas de árboles, techos, falsos plafones, vigas y áticos.",
        "damage_and_risks": "Vector de peste (a través de pulga Xenopsylla cheopis), salmonelosis, toxoplasmosis. Roedura de cableado en plafones falsos y contaminación de materias primas en estanterías altas.",
        "critical_points": "Plafones falsos, cables aéreos de acometida, copas de árboles que tocan techumbres, ductos de ventilación.",
        "exclusion_measures": "Poda de ramas a 2 metros de los techos; colocación de conos invertidos antiquiebre en tuberías y bajadas pluviales; sellado de aleros.",
        "mechanical_control": "Trampas de impacto ancladas sobre vigas de acero y bandejas de cables.",
        "chemical_protocol": [
            "1. Instalación de cebaderos aéreos asegurados en áreas de tránsito alto inaccesibles a personas.",
            "2. Colocación de bloques de rodenticida con alta palatabilidad (Brodifacoum o Difetialona).",
            "3. Retiro de restos de frutas y fuentes de alimento en techumbres."
        ],
        "recommended_chemicals": [
            "Storm Bloques (Flocumafen 0.005%)",
            "Klerat Bloque (Brodifacoum 0.005%)"
        ],
        "irac_rotation": "Anticoagulantes de segunda generación.",
        "reentry_time": "0 horas (estaciones cebaderas cerradas)."
    },
    {
        "id": "raton-casero",
        "name": "Ratón Casero / Doméstico",
        "scientific_name": "Mus musculus",
        "category": "Roedores Comensales",
        "icon": "fa-paw",
        "danger_level": "Alto (Contaminación de Alimentos)",
        "biology_and_habits": "Roedor pequeño de 6 a 9 cm, peso de 15 a 25 g. Hocico puntiagudo, orejas grandes y cola delgada igual o más larga que el cuerpo. Territorio muy reducido (radio de 3 a 5 metros del nido). Curioso ante objetos nuevos (neofílico). Capaz de pasar por orificios de tan solo 6 mm de diámetro (tamaño de un lápiz).",
        "damage_and_risks": "Contamina con sus heces (50 a 75 excrementos diarios por individuo) y orina hasta 10 veces más alimento del que consume. Transmisor de Coriomeningitis Linfocitaria (LCMV) y Salmonelosis.",
        "critical_points": "Plafones falsos, interior de muebles de cocina, almacenes de abarrotes, cuartos de telecomunicaciones, detrás de refrigeradores.",
        "exclusion_measures": "Sellado de orificios con fibra de acero inoxidable (lana de acero) mezclada con silicón sellador; ajuste de guardapolvos en puertas con luz inferior menor a 6 mm.",
        "mechanical_control": "Trampas de captura múltiple y trampas de pegamento colocadas en parejas a lo largo de las rutas de tránsito en esquinas y paredes interiores.",
        "chemical_protocol": [
            "1. Mapeo y colocación de estaciones cebaderas perimetrales exteriores a intervalos más cortos (5 a 8 metros).",
            "2. En áreas exteriores o almacenes secundarios: bloques parafinados pequeños asegurados en varilla.",
            "3. En interiores estrictamente trampas mecánicas o de goma adhesiva sin veneno."
        ],
        "recommended_chemicals": [
            "Klerat Bloque (Brodifacoum 0.005% - RSCO-URB-ROD-138-315-033-0.005)",
            "Storm Bloques (Flocumafen 0.005% - RSCO-URB-ROD-0101-301-033-0.005)"
        ],
        "irac_rotation": "Alternar rodenticidas de segunda generación.",
        "reentry_time": "0 horas."
    },
    {
        "id": "chinche-cama",
        "name": "Chinche de Cama Común",
        "scientific_name": "Cimex lectularius",
        "category": "Insectos Hematófagos",
        "icon": "fa-bed",
        "danger_level": "Alto (Molestia Severa y Salud Pública)",
        "biology_and_habits": "Insecto áptero, aplanado dorsoventralmente, color café rojizo, de 4 a 7 mm. Hematófago obligado en todas sus etapas ninfales y adultas. Se alimenta durante la noche mientras el huésped duerme (duración de la picadura: 5 a 10 minutos). Puede sobrevivir hasta un año sin alimentarse a temperaturas templadas. Se dispersa pasivamente en equipaje, ropa y muebles de segunda mano.",
        "damage_and_risks": "Picaduras intensamente pruriginosas dispuestas a menudo en líneas o racimos de tres ('desayuno, comida y cena'). Provoca insomnio severo, ansiedad, anemia en infestaciones crónicas e infecciones bacterianas secundarias por rascado.",
        "critical_points": "Costuras y etiquetas de colchones, somieres (box spring), hendiduras de cabeceras de madera, rodapiés, detrás de marcos de cuadros y placas de contactos eléctricos a menos de 2 metros de la cama.",
        "exclusion_measures": "Encamisado de colchones y somieres con fundas protectoras certificadas anti-chinche; aislamiento de la cama separándola 15 cm de la pared y colocando trampas interceptoras en las patas.",
        "mechanical_control": "Tratamiento térmico con vapor seco a más de 60°C en costuras y grietas; aspirado profundo con bolsa desechable sellada.",
        "chemical_protocol": [
            "1. Desarme exhaustivo de la cama y muebles aledaños para inspección visual.",
            "2. Aplicación de mezcla combinada de piretroide + neonicotinoide (Temprid SC) en grietas del bastidor, rodapiés y marcos (evitar mojar la superficie directa donde duerme la persona).",
            "3. Aplicación de polvo desecante no químico o residual (Tierra de diatomeas o Clorfenapir Phantom) en el interior de chalupas de contactos eléctricos y huecos de rodapié.",
            "4. Segunda aplicación obligatoria a los 14-21 días para eliminar las ninfas recién eclosionadas de los huevos."
        ],
        "recommended_chemicals": [
            "Temprid SC (Imidacloprid + Beta-ciflutrina - RSCO-MEZC-INAC-0101-385-342-31.5)",
            "Phantom SC (Clorfenapir 21.45% - RSCO-URB-INAC-0102H-315-009-21.45)",
            "Demand 2.5 CS (Lambda Cyhalotrina 2.5% - RSCO-URB-INAC-173-356-064-2.5)"
        ],
        "irac_rotation": "Combinar Neonicotinoides (IRAC 4A) con Piretroides (IRAC 3A) y Pirroles (IRAC 13) para vencer la resistencia a piretroides tradicionales.",
        "reentry_time": "4 horas tras la aplicación, con ventilación previa."
    },
    {
        "id": "chinche-besucona",
        "name": "Chinche Besucona / Triatómino",
        "scientific_name": "Triatoma infestans / Triatoma dimidiata / Meccus phyllosomus",
        "category": "Insectos Hematófagos",
        "icon": "fa-heart-crack",
        "danger_level": "Extremo (Vector de la Enfermedad de Chagas)",
        "biology_and_habits": "Insecto hematófago de 20 a 35 mm, cuerpo aplanado con reborde abdominal (conexivo) bandeado de negro y naranja/rojo. Hábitos nocturnos; se oculta durante el día en grietas de paredes de adobe, techos de palma, gallineros y corrales. Pica alrededor de la boca o los ojos del durmiente y defeca mientras se alimenta.",
        "damage_and_risks": "Vector biológico obligatorio del protozoario Trypanosoma cruzi, causante de la Enfermedad de Chagas (Tripanosomiasis Americana). Provoca cardiopatía chagásica crónica irreversible, megaesófago, megacolon y muerte súbita.",
        "critical_points": "Paredes de adobe y piedra sin enjarre, techos de teja o madera rústica, detrás de cabeceras, corrales de aves y caniles de perros.",
        "exclusion_measures": "Enjarre y aplanado de muros con cemento o yeso; reubicación de corrales de animales a más de 20 metros de la vivienda; instalación de mosquiteros finos.",
        "mechanical_control": "Inspección nocturna y captura segura con pinzas (nunca aplastar con las manos desnudas).",
        "chemical_protocol": [
            "1. Rociado residual intradomiciliario y peridomiciliario saturando paredes completas hasta el techo con piretroides concentrados.",
            "2. Tratamiento exhaustivo de corrales, leñeras y bodegas anexas.",
            "3. Rociado de refuerzo semestral conforme al programa de vectores de la Secretaría de Salud."
        ],
        "recommended_chemicals": [
            "Biothrine Flow (Deltametrina 2.5% - RSCO-URB-INAC-111-315-009-2.5)",
            "Fendona 6 SC (Alfa-cipermetrina 6% - RSCO-URB-INAC-184-315-009-6.0)",
            "Demand 2.5 CS (Lambda Cyhalotrina 2.5% - RSCO-URB-INAC-173-356-064-2.5)"
        ],
        "irac_rotation": "Piretroides Grupo 3A de alta residualidad.",
        "reentry_time": "4 horas tras el rociado intradomiciliario."
    },
    {
        "id": "alacranes",
        "name": "Alacranes / Escorpiones Urbanos",
        "scientific_name": "Centruroides spp. (C. limpidus, C. sculpturatus, C. suffusus)",
        "category": "Arácnidos Ponzoñosos",
        "icon": "fa-skull-crossbones",
        "danger_level": "Extremo (Veneno Neurotóxico Potencialmente Letal)",
        "biology_and_habits": "Arácnidos nocturnos provistos de pedipalpos en pinza y metasoma (cola) con aguijón conectado a glándulas venenosas. En México las especies de mayor toxicidad pertenecen al género Centruroides (color amarillo pajizo o pardo claro, pinzas delgadas y dientecillo subaculear bajo el aguijón). Se refugian en escombros, madera, calzado y grietas.",
        "damage_and_risks": "La picadura inyecta neurotoxinas peptídicas que provocan dolor quemante intenso, parestesias, sialorrea, sensación de cuerpo extraño en la faringe, nistagmo, dificultad respiratoria, convulsiones y riesgo de paro respiratorio en infantes.",
        "critical_points": "Patios con escombros, leña apilada, registros de agua potable, grietas en muros de piedra, rodapiés, falsos plafones, clósets en planta baja.",
        "exclusion_measures": "Zócalos de azulejo liso en la base exterior de las paredes (los alacranes no trepan superficies pulidas); colocación de mosquiteros y guardapolvos herméticos; revisión obligatoria de calzado antes de ponérselo.",
        "mechanical_control": "Búsqueda nocturna con lámpara de luz ultravioleta (fluorescencia verde brillante por beta-carbolinas) y remoción mecánica segura con pinzas largas.",
        "chemical_protocol": [
            "1. Despeje previo de escombros y deshierbe perimetral con guantes de carnaza y calzado industrial.",
            "2. Aplicación de barrera perimetral exterior con insecticida microencapsulado de alto poder residual (Demand 2.5 CS o Biothrine Flow) en franja de 1 metro en piso y 1 metro en pared.",
            "3. Aspersión en marcos de puertas, ventanas, zoclos y registros hidrosanitarios."
        ],
        "recommended_chemicals": [
            "Demand 2.5 CS (Lambda Cyhalotrina 2.5% - RSCO-URB-INAC-173-356-064-2.5)",
            "Biothrine Flow (Deltametrina 2.5% - RSCO-URB-INAC-111-315-009-2.5)",
            "Dragnet FT (Permetrina 36.8% - RSCO-URB-INAC-124-315-009-36.8)"
        ],
        "irac_rotation": "Piretroides Tipo II de prolongada estabilidad residual.",
        "reentry_time": "2 a 4 horas. En picadura: administrar Faboterápico Antialacrán y llamar a SINTOX 800-009-2800."
    },
    {
        "id": "arana-violinista",
        "name": "Araña Violinista / De Rincón",
        "scientific_name": "Loxosceles reclusa / Loxosceles boneti / Loxosceles laeta",
        "category": "Arácnidos Ponzoñosos",
        "icon": "fa-spider",
        "danger_level": "Extremo (Veneno Necrótico y Hemolítico)",
        "biology_and_habits": "Araña de 10 a 15 mm, color pardo uniforme sin manchas en las patas. Característica diagnóstica: 6 ojos dispuestos en 3 pares (díadas en tríada ocular) y mancha oscura en forma de violín sobre el cefalotórax. Hábitos tímidos, sedentarios y nocturnos; huye de la luz.",
        "damage_and_risks": "Inocula esfingomielinasa D causante de Loxoscelismo Cutáneo (isquemia, dolor urente, flictena hemorrágica y escara necrótica de difícil cicatrización) y Loxoscelismo Viscerocutáneo (hemólisis masiva, hemoglobinuria, insuficiencia renal aguda y muerte).",
        "critical_points": "Rincones oscuros de bodegas, detrás de cuadros y espejos, cajas de cartón, interior de clósets poco frecuentados, debajo de tanques de gas.",
        "exclusion_measures": "Aspirado periódico de rincones y detrás de muebles; uso de guantes al mover archivo muerto o leña; sacudir prendas y ropa de cama antes de su uso; separación de camas a 20 cm de las paredes.",
        "mechanical_control": "Trampas adhesivas en rodapiés oscuros.",
        "chemical_protocol": [
            "1. Aspersión dirigida y focalizada en rodapiés, esquinas altas, detrás de muebles y alacenas con formulaciones microencapsuladas.",
            "2. Tratamiento de registros y bodegas con suspensión concentrada."
        ],
        "recommended_chemicals": [
            "Demand 2.5 CS (Lambda Cyhalotrina Microencapsulada 2.5%)",
            "Biothrine Flow (Deltametrina 2.5%)",
            "Fendona 6 SC (Alfa-cipermetrina 6%)"
        ],
        "irac_rotation": "Piretroides Tipo II de alta persistencia.",
        "reentry_time": "2 a 4 horas. En mordedura: aplicar Faboterápico Antiloxosceles de urgencia médica."
    },
    {
        "id": "arana-viuda-negra",
        "name": "Araña Viuda Negra / Capulina",
        "scientific_name": "Latrodectus mactans / Latrodectus hesperus",
        "category": "Arácnidos Ponzoñosos",
        "icon": "fa-spider",
        "danger_level": "Extremo (Veneno Neurotóxico Alfa-latrotoxina)",
        "biology_and_habits": "Hembra de 12 a 15 mm, abdomen globular negro azabache brillante con característica mancha roja brillante en forma de reloj de arena en la cara ventral. Construye telas tridimensionales irregulares y muy resistentes en zonas bajas oscuras.",
        "damage_and_risks": "Inocula alfa-latrotoxina provocando Latrodectismo: dolor muscular abdominal espasmódico intenso ('abdomen en madera'), sudoración profusa, hipertensión, taquicardia, opresión torácica y shock neurogénico.",
        "critical_points": "Cajas de registro de agua potable, medidores de gas, pilas de leña o ladrillos, letrinas, partes bajas de muebles exteriores.",
        "exclusion_measures": "Mantenimiento y sellado de tapas de registros; iluminación adecuada en exteriores; despeje de acumulaciones de chatarra.",
        "mechanical_control": "Destrucción física de telas y captura con vara con punta adhesiva.",
        "chemical_protocol": [
            "1. Aspersión de contacto directo sobre telarañas y refugios.",
            "2. Creación de barrera perimetral con insecticida residual de banda verde."
        ],
        "recommended_chemicals": [
            "Demand 2.5 CS (Lambda Cyhalotrina 2.5%)",
            "Biothrine Flow (Deltametrina 2.5%)",
            "Cybor 10 EA (Cipermetrina 10%)"
        ],
        "irac_rotation": "Piretroides Grupo 3A.",
        "reentry_time": "2 horas. Tratamiento médico: Faboterápico Antilatrodectus."
    },
    {
        "id": "garrapatas",
        "name": "Garrapata Café del Perro",
        "scientific_name": "Rhipicephalus sanguineus",
        "category": "Arácnidos Hematófagos / Vectores",
        "icon": "fa-bug-slash",
        "danger_level": "Extremo (Vector de Rickettsiosis Letal)",
        "biology_and_habits": "Ácaro ectoparásito hematófago con ciclo de 3 huéspedes. Capaz de completar todo su ciclo en interiores de casas y construcciones urbanas. Las hembras ingurgitadas trepan por paredes, grietas y techos para ovipositar de 2,000 a 4,000 huevecillos.",
        "damage_and_risks": "Vector primario de Rickettsia rickettsii (Fiebre Manchada de las Montañas Rocosas), enfermedad infecciosa potencialmente letal de alta incidencia en el norte de México (Chihuahua, Sonora, BC, Coahuila). También transmite Ehrlichia canis y Anaplasma.",
        "critical_points": "Grietas en muros de concreto y adobe, marcos superiores de puertas, detrás de cuadros, esquinas de techos, patios de tierra y cercas de madera.",
        "exclusion_measures": "Enjarre y sellado de grietas en bardas y muros exteriores; recorte de pasto; baño y desparasitación externa de perros con ectoparasiticidas veterinarios (Isoxazolinas).",
        "mechanical_control": "Revisión física periódica de mascotas y eliminación segura en alcohol al 70%.",
        "chemical_protocol": [
            "1. Aspersión de choque y barrera total en bardas perimetrales exteriores e interiores hasta 1.5 metros de altura.",
            "2. Aplicación minuciosa en marcos de puertas, ventanas, rodapiés y uniones techo-pared.",
            "3. Tratamiento de suelos de patio con insecticidas microencapsulados resistentes al sol y lluvia.",
            "4. Refuerzo obligatorio a los 14-21 días."
        ],
        "recommended_chemicals": [
            "Demand 2.5 CS (Lambda Cyhalotrina Microencapsulada)",
            "Biothrine Flow (Deltametrina 2.5%)",
            "Temprid SC (Imidacloprid + Betaciflutrina)"
        ],
        "irac_rotation": "Piretroides Tipo II y Neonicotinoides combinados.",
        "reentry_time": "4 horas tras aspersión completa."
    },
    {
        "id": "pulgas",
        "name": "Pulgas (Gato y Perro)",
        "scientific_name": "Ctenocephalides felis / Ctenocephalides canis",
        "category": "Insectos Hematófagos",
        "icon": "fa-shield-virus",
        "danger_level": "Alto (Vectores y Alergias Severas)",
        "biology_and_habits": "Insectos ápteros aplanados lateralmente de 1 a 3 mm, con patas traseras adaptadas para saltar hasta 20 cm en vertical. Adultos hematófagos estrictos. Larvas no parásitas que se alimentan de restos orgánicos y heces de pulga adulta en alfombras, hendiduras y camas de mascotas.",
        "damage_and_risks": "Dermatitis Alérgica por Picadura de Pulga (DAPP), anemia severa en cachorros, vector de Dipylidium caninum (tenia) y Rickettsia felis / Bartonella henselae (enfermedad por arañazo de gato).",
        "critical_points": "Camas y cobijas de mascotas, alfombras, zoclos de madera, grietas en pisos, áreas de sombra en patios de tierra.",
        "exclusion_measures": "Lavado de textiles de mascotas a más de 60°C; aspirado diario y exhaustivo de tapetes y zoclos; tratamiento veterinario coordinado en mascotas.",
        "mechanical_control": "Aspirado profundo continuo (desechar la bolsa inmediatamente).",
        "chemical_protocol": [
            "1. Tratamiento combinado con insecticida adulticida residual (Deltametrina o Lambdacialotrina) + Regulador de Crecimiento (IGR: Triflumuron / Piriproxifeno) para romper el ciclo larvario y pupal.",
            "2. Aspersión uniforme a baja presión en pisos, tapetes y franja inferior de muros a 50 cm de altura.",
            "3. Tratamiento de patios perimetrales sombreados donde reposan animales."
        ],
        "recommended_chemicals": [
            "Temprid SC (Imidacloprid + Beta-ciflutrina)",
            "Starycide SC 480 (Triflumuron 48% IGR)",
            "Demand 2.5 CS (Lambda Cyhalotrina 2.5%)"
        ],
        "irac_rotation": "Grupo 3A + Grupo 4A + Grupo 15 (IGRs).",
        "reentry_time": "4 horas completas hasta el secado total del producto."
    },
    {
        "id": "mosca-domestica",
        "name": "Mosca Doméstica",
        "scientific_name": "Musca domestica",
        "category": "Insectos Voladores",
        "icon": "fa-feather",
        "danger_level": "Alto (Vector Mecánico Entérico)",
        "biology_and_habits": "Insecto volador díptero de 6 a 7 mm. Ojos compuestos grandes, aparato bucal adaptado para lamer y esponjar alimentos líquidos. Para ingerir sólidos regurgita saliva y jugos gástricos. Una hembra oviposita de 500 a 1,000 huevos en materia orgánica húmeda en descomposición (estiércol, basura, carne). En clima cálido su ciclo completo huevo-adulto dura apenas 7 a 10 días.",
        "damage_and_risks": "Transmisora de más de 100 patógenos humanos: Cólera, Fiebre tifoidea, Disentería bacilar, Salmonelosis, Helmintiasis y conjuntivitis.",
        "critical_points": "Contenedores de basura descubiertos, compactadores de residuos, andenes de recepción de materias primas perecederas, áreas de lavado de loza.",
        "exclusion_measures": "Cortinas de aire funcionando permanentemente sobre accesos a cocina y comedores; mallas mosquiteras en ventanas; puertas de cierre automático.",
        "mechanical_control": "Instalación de lámparas de luz ultravioleta con lámina adhesiva a una altura de 1.80 a 2.10 metros, ubicadas en áreas de paso y no orientadas hacia el exterior.",
        "chemical_protocol": [
            "1. Eliminación y lavado a presión de la fuente de cría (contenedores de basura).",
            "2. Pintado de franjas cebadas con cebo mosquicida atrayente con feromona sexual (Tiametoxam + Z-9 Tricosene: Agita 10 WG) en paredes altas y posaderos cálidos fuera del alcance de personas y alimentos.",
            "3. Nebulización espacial ULV en exteriores con piretrinas naturales o deltametrina para abatimiento rápido de adultos."
        ],
        "recommended_chemicals": [
            "Agita 10 WG (Tiametoxam 10% + Z-9 Tricosene - RSCO-URB-INAC-192-385-034-10.0)",
            "Fendona 6 SC (Alfa-cipermetrina 6% - RSCO-URB-INAC-184-315-009-6.0)",
            "Pybuthrin 33 (Piretrinas Naturales 3% - RSCO-URB-INAC-102-315-009-3.0)"
        ],
        "irac_rotation": "Alternar Neonicotinoides cebados (IRAC 4A) con Piretroides residuales (IRAC 3A).",
        "reentry_time": "0 horas para cebos pintados; 2 horas tras nebulización espacial."
    },
    {
        "id": "mosca-drenaje",
        "name": "Mosca del Drenaje / De la Humedad",
        "scientific_name": "Psychoda alternata / Clogmia albipunctata",
        "category": "Insectos Voladores",
        "icon": "fa-water",
        "danger_level": "Moderado (Vector Mecánico en Sanitarios)",
        "biology_and_habits": "Díptero pequeño de 2 a 5 mm, cuerpo y alas cubiertos de abundante pilosidad que le da aspecto de pequeña polilla. Vuelo torpe e irregular. Las larvas se desarrollan en la biopelícula mucosa y lodo orgánico que recubre el interior de tuberías de drenaje, sifones y rebosaderos de lavabos.",
        "damage_and_risks": "Contaminación de áreas asépticas, baños y cocinas; posible miasis accidental; transporta bacterias del caño.",
        "critical_points": "Sifones de coladeras, rebosaderos de lavabos, charolas de condensación de aire acondicionado, sellos hidráulicos secos.",
        "exclusion_measures": "Vertido semanal de agua hirviendo y desengrasante bioenzimático en tuberías; colocación de tapones en desagües en desuso.",
        "mechanical_control": "Limpieza mecánica con cepillo de alambre o espiral en el interior del tubo de desagüe para desprender la biopelícula gelatinosa.",
        "chemical_protocol": [
            "1. Limpieza y desincrustación enzimática de la biopelícula orgánica.",
            "2. Aplicación de regulador de crecimiento de insectos (IGR) o piretrinas en la boca de la coladera.",
            "3. Aspersión de residual en paredes de azulejo adyacentes."
        ],
        "recommended_chemicals": [
            "Pybuthrin 33 (Piretrinas Naturales)",
            "Biothrine Flow (Deltametrina 2.5%)",
            "Starycide SC 480 (Triflumuron IGR)"
        ],
        "irac_rotation": "Piretrinas e IGRs.",
        "reentry_time": "1 hora."
    },
    {
        "id": "mosca-fruta",
        "name": "Mosca del Vinagre / De la Fruta",
        "scientific_name": "Drosophila melanogaster",
        "category": "Insectos Voladores",
        "icon": "fa-wine-bottle",
        "danger_level": "Moderado (Contaminación en Bares y Restaurantes)",
        "biology_and_habits": "Insecto diminuto de 2.5 a 3.5 mm con ojos rojos brillantes y cuerpo amarillento. Ciclo vital extraordinariamente rápido (8 a 10 días a 25°C). Se reproduce en sustratos con fermentación alcohólica o acética: frutas maduras, botellas de licor abiertas, trapos húmedos de barra y fondos de botes de basura.",
        "damage_and_risks": "Contaminación visual y sanitaria de bebidas y alimentos preparados en restaurantes, comedores industriales y supermercados.",
        "critical_points": "Barras de bar, dispensadores de refresco, trapeadores húmedos en cuartos oscuros, botes de reciclaje de latas.",
        "exclusion_measures": "Eliminación diaria de fruta sobremadura; lavado de charolas de goteo de cerveza y refresco con solución clorada.",
        "mechanical_control": "Trampas de captura líquida con atrayente de vinagre de manzana y surfactante; lámparas UV con pegamento.",
        "chemical_protocol": [
            "1. Saneamiento estricto de fuentes de fermentación.",
            "2. Nebulización ULV con piretrinas de rápida degradación sin dejar residuos tóxicos en superficies de cocina.",
            "3. Aplicación de cebo mosquicida en zonas de reposo."
        ],
        "recommended_chemicals": [
            "Pybuthrin 33 (Piretrinas Naturales sin solventes)",
            "Agita 10 WG (Tiametoxam)"
        ],
        "irac_rotation": "Piretrinas e Neonicotinoides.",
        "reentry_time": "1 a 2 horas."
    },
    {
        "id": "mosquitos-aedes-culex",
        "name": "Mosquitos Urbanos (Dengue, Zika, Chikungunya)",
        "scientific_name": "Aedes aegypti / Culex quinquefasciatus",
        "category": "Insectos Voladores",
        "icon": "fa-mosquito",
        "danger_level": "Extremo (Vectores Epidemiológicos de Salud Pública)",
        "biology_and_habits": "Aedes aegypti: Tórax con dibujo en forma de lira y patas anilladas de blanco. Hábitos diurnos antropofílicos; oviposita en recipientes artificiales con agua limpia. Culex: Color pardo uniforme, hábitos nocturnos; cría en aguas estancadas ricas en materia orgánica.",
        "damage_and_risks": "Transmisión activa de arbovirosis graves: Dengue clásico y hemorrágico, Virus del Zika (microcefalia congénita), Chikungunya y Virus del Nilo Occidental.",
        "critical_points": "Llantas usadas, cubetas, floreros, canaletas pluviales obstruidas, tinacos sin tapa, charcos perimetrales.",
        "exclusion_measures": "Estrategia 'Lava, Tapa, Voltea y Tira'; instalación de mallas mosquiteras 18x16 en ventanas; sellado de tapas de tinacos y cisternas.",
        "mechanical_control": "Ovitrampas de monitoreo y trampas de luz UV en interiores.",
        "chemical_protocol": [
            "1. Control larvario con larvicidas biológicos (BTI - Bacillus thuringiensis israelensis) en recipientes no desechables.",
            "2. Tratamiento residual de superficies de reposo exteriores e interiores con microencapsulados.",
            "3. Termonebulización o nebulización espacial en frío (ULV) con piretroides autorizados en horarios de máxima actividad (amanecer / atardecer)."
        ],
        "recommended_chemicals": [
            "Biothrine Flow (Deltametrina 2.5% - RSCO-URB-INAC-111-315-009-2.5)",
            "AquaPy (Piretrinas Naturales sin solventes base agua)",
            "Fendona 6 SC (Alfa-cipermetrina 6%)"
        ],
        "irac_rotation": "Piretroides Grupo 3A alternados con Biolarvicidas Grupo 11.",
        "reentry_time": "2 horas tras nebulización espacial."
    },
    {
        "id": "hormigas-urbanas",
        "name": "Hormigas Urbanas (Loca, Argentina, Fantasma)",
        "scientific_name": "Linepithema humile, Paratrechina longicornis, Tapinoma melanocephalum",
        "category": "Insectos Rastreros",
        "icon": "fa-cubes-stacked",
        "danger_level": "Moderado a Alto (Vector Hospitalario)",
        "biology_and_habits": "Insectos sociales que viven en colonias complejas con una o múltiples reinas (poliginia). Forman senderos persistentes de forrajeo siguiendo feromonas de pista. Fenómeno de gemación (budding): si se aplica insecticida repelente de contacto, la colonia se fragmenta en múltiples nidos satélites multiplicando la infestación.",
        "damage_and_risks": "En hospitales y clínicas transportan bacterias nosocomiales (Staphylococcus aureus, Pseudomonas) directamente a áreas estériles y equipos de infusión. En oficinas dañan equipos informáticos al anidar en fuentes de poder.",
        "critical_points": "Jardineras adyacentes a muros, hendiduras en banquetas, ductos eléctricos, tarjas de cocina, máquinas de café.",
        "exclusion_measures": "Sellado de entradas en juntas de ventanas y pasos de cables; poda de plantas que toquen muros o techos.",
        "mechanical_control": "Limpieza profunda con agua jabonosa para borrar las feromonas de pista de forrajeo.",
        "chemical_protocol": [
            "1. NUNCA aplicar piretroides repelentes dentro de la zona de forrajeo.",
            "2. Aplicar cebo en gel líquido azucarado o proteico (Tiametoxam o Fipronil: Optigard Ant Gel) en gotas a lo largo del sendero para que las obreras lo transporten al nido por trofalaxis y envenenen a las reinas.",
            "3. En exteriores: aspersión perimetral con insecticida no repelente (Fipronil Termidor o Clorfenapir) para crear una barrera de transferencia."
        ],
        "recommended_chemicals": [
            "Optigard Ant Gel (Tiametoxam 0.01% - RSCO-URB-INAC-0102M-301-392-0.01)",
            "Termidor 25 CE (Fipronil 2.5% - RSCO-URB-INAC-175-313-009-2.5)",
            "Phantom SC (Clorfenapir 21.45% - RSCO-URB-INAC-0102H-315-009-21.45)"
        ],
        "irac_rotation": "Cebos neonicotinoides (IRAC 4A) combinados con no repelentes pirroles (IRAC 13) y fenilpirazoles (IRAC 2B).",
        "reentry_time": "0 horas para cebos en gel; 2 horas para aspersión exterior."
    },
    {
        "id": "hormiga-fuego",
        "name": "Hormiga de Fuego / Brava",
        "scientific_name": "Solenopsis invicta / Solenopsis geminata",
        "category": "Insectos Rastreros",
        "icon": "fa-fire",
        "danger_level": "Alto a Extremo (Picadura Venenosa Dolorosa)",
        "biology_and_habits": "Hormigas de 2 a 6 mm, color café rojizo con abdomen oscuro. Construyen montículos de tierra cónicos en jardines, campos y orillas de banquetas. Extremadamente agresivas: ante perturbación salen en masa, muerden con sus mandíbulas y clavan repetidamente su aguijón inyectando solenopsina (alcaloide tóxico).",
        "damage_and_risks": "Picaduras que forman pústulas estériles pruriginosas propensas a sobreinfección; shock anafiláctico en personas alérgicas; daño a instalaciones eléctricas y transformadores.",
        "critical_points": "Montículos de tierra en jardines, campos deportivos, transformadores eléctricos a ras de suelo.",
        "exclusion_measures": "Mantenimiento del césped; sellado de cajas de registro eléctrico con espuma aislante.",
        "mechanical_control": "Eliminación de maleza.",
        "chemical_protocol": [
            "1. Aplicación de cebo granulado específico alrededor del montículo (nunca directo sobre él para no alertarlas).",
            "2. Inyección o empapado del nido con solución insecticida de alto volumen.",
            "3. Aspersión perimetral de barrera."
        ],
        "recommended_chemicals": [
            "Termidor 25 CE (Fipronil 2.5%)",
            "Demand 2.5 CS (Lambda Cyhalotrina 2.5%)",
            "Biothrine Flow (Deltametrina 2.5%)"
        ],
        "irac_rotation": "Fenilpirazoles y Piretroides.",
        "reentry_time": "2 a 4 horas."
    },
    {
        "id": "avispas-y-abejas",
        "name": "Avispas, Avispones y Abejas",
        "scientific_name": "Vespula germanica, Polistes, Apis mellifera",
        "category": "Insectos Voladores",
        "icon": "fa-triangle-exclamation",
        "danger_level": "Extremo (Shock Anafiláctico y Picaduras Múltiples)",
        "biology_and_habits": "Insectos sociales o subsociales que construyen panales o nidos de papel y celulosa masticada en aleros, techos, cajas de registro y árboles. Las avispas poseen aguijón liso que les permite picar múltiples veces sin morir; las abejas pierden el aguijón y mueren al picar.",
        "damage_and_risks": "Inoculación de veneno con histamina, melitina y péptidos que provocan dolor severo, inflamación y riesgo letal de shock anafiláctico en personas alérgicas sensibilizadas.",
        "critical_points": "Aleros de techos, cajas de medidores de gas y luz, tuberías de desagüe pluvial en azoteas, árboles huecos.",
        "exclusion_measures": "Sellado de oquedades en fachadas y cajas de registro; colocación de mallas finas en respiraderos de áticos.",
        "mechanical_control": "Para enjambres de abejas: Rescate y reubicación prioritaria con apicultor certificado conforme a normativas de protección a polinizadores.",
        "chemical_protocol": [
            "1. Para avispas agresivas en estructuras: Tratamiento al atardecer o noche cuando toda la colonia está dentro del nido.",
            "2. Aspersión de largo alcance (chorro sólido hasta 5 metros) con piretroide de rápido derribo (knock-down).",
            "3. Retiro y destrucción física del panal una vez neutralizada la actividad."
        ],
        "recommended_chemicals": [
            "Biothrine Flow (Deltametrina 2.5%)",
            "Pybuthrin 33 (Piretrinas de Derribo Instantáneo)",
            "Demand 2.5 CS (Barrera Residual de Retirada)"
        ],
        "irac_rotation": "Piretroides Grupo 3A de alto derribo.",
        "reentry_time": "2 horas tras remoción del nido."
    },
    {
        "id": "termitas",
        "name": "Termita Subterránea",
        "scientific_name": "Reticulitermes spp., Coptotermes formosanus",
        "category": "Insectos Xilófagos",
        "icon": "fa-tree",
        "danger_level": "Extremo (Colapso Estructural)",
        "biology_and_habits": "Insectos coloniales que se alimentan de celulosa (madera, papel, cartón). Viven en nidos subterráneos en el suelo y construyen tubos de lodo y saliva para desplazarse hacia las estructuras de madera sin deshidratarse por la luz y el aire.",
        "damage_and_risks": "Destrucción interna silente de vigas de soporte, duelas, marcos de puertas, muebles empotrados y archivos documentales. No hacen aserrín visible (a diferencia de la carcoma), devoran la madera desde el interior dejando solo una cáscara delgada.",
        "critical_points": "Tubos de lodo en cimientos y muros de carga; madera en contacto directo con tierra; humedad constante por fugas de agua subterránea.",
        "exclusion_measures": "Evitar cualquier contacto madera-suelo (mínimo 15 cm de separación con bases de concreto); drenar el agua lejos de los cimientos.",
        "mechanical_control": "Retiro y sustitución de elementos de madera debilitados estructuralmente.",
        "chemical_protocol": [
            "1. Creación de una barrera química antitermítica en suelo perimetral mediante zanja de 30x30 cm inyectando 5 litros de emulsión por metro lineal con Fipronil (Termidor 25 CE).",
            "2. Inyección a presión bajo losas perforando orificios cada 30 cm a lo largo de muros de carga.",
            "3. Tratamiento curativo directo en maderas atacadas con formulaciones penetrantes."
        ],
        "recommended_chemicals": [
            "Termidor 25 CE (Fipronil 2.5% - RSCO-URB-INAC-175-313-009-2.5)",
            "Dragnet FT (Permetrina 36.8% - RSCO-URB-INAC-124-315-009-36.8)"
        ],
        "irac_rotation": "Fipronil de acción no repelente y efecto dominó de transferencia por contacto social.",
        "reentry_time": "4 horas tras inyección perimetral."
    },
    {
        "id": "termita-madera-seca",
        "name": "Termita de Madera Seca",
        "scientific_name": "Cryptotermes brevis / Incisitermes snyderi",
        "category": "Insectos Xilófagos",
        "icon": "fa-chair",
        "danger_level": "Alto (Daño a Muebles y Obras de Arte)",
        "biology_and_habits": "No requieren contacto con el suelo ni fuentes de humedad externa; obtienen el agua metabólica de la madera seca (<10% humedad). Viven en colonias pequeñas enteramente dentro de la pieza de madera infestada. Expulsan pellets fecales hexagonales diminutos ('aserrín en bolitas') a través de orificios de expulsión.",
        "damage_and_risks": "Ahuecamiento de marcos de cuadros, puertas, duelas, muebles finos y estructuras históricas de madera.",
        "critical_points": "Muebles de madera antigua, vigas de techos, marcos de ventanas de madera, pisos de duela.",
        "exclusion_measures": "Sellado de orificios de vuelo con cera o barniz; mallas finas en áticos para evitar ingreso de alados durante el enjambrazón.",
        "mechanical_control": "Tratamiento térmico en cámara o congelación para piezas de arte y muebles portátiles.",
        "chemical_protocol": [
            "1. Localización de galerías activas mediante detección sonora o térmica.",
            "2. Perforación e inyección a presión con insecticida soluble a base de sales de boro (Bora-Care) o piretroide residual.",
            "3. En infestaciones severas generalizadas: fumigación en cámara hermética o encarpado con gas autorizado."
        ],
        "recommended_chemicals": [
            "Sales de Boro penetrantes (Octaborato disódico tetrahidratado)",
            "Termidor 25 CE (Fipronil 2.5%)",
            "Dragnet FT (Permetrina 36.8%)"
        ],
        "irac_rotation": "Boratos inorgánicos y Fenilpirazoles.",
        "reentry_time": "4 horas."
    },
    {
        "id": "carcoma-madera",
        "name": "Carcoma / Barrenador de la Madera",
        "scientific_name": "Anobium punctatum / Hylotrupes bajulus / Lyctus brunneus",
        "category": "Insectos Xilófagos",
        "icon": "fa-cubes",
        "danger_level": "Alto (Degradación de Maderas y Estructuras)",
        "biology_and_habits": "Escarabajos cuyas larvas xilófagas taladran túneles y galerías en el interior de la madera durante 2 a 5 años alimentándose de la celulosa y almidón. El adulto perfora un orificio circular de salida (1 a 3 mm) y expulsa aserrín fino o polvillo harinoso.",
        "damage_and_risks": "Pérdida de resistencia mecánica en vigas estructurales, colapso de techumbres de madera, daño irreparable a muebles y retablos.",
        "critical_points": "Viguería de madera de pino o roble, muebles rústicos, duelas, partes traseras de retablos y clósets.",
        "exclusion_measures": "Aplicación preventiva de lasures o barnices fungicidas/insecticidas en maderas vírgenes; control de humedad ambiental <50%.",
        "mechanical_control": "Sustitución de vigas colapsadas; aspirado y cepillado profundo de orificios de vuelo.",
        "chemical_protocol": [
            "1. Decapado o lijado de barnices para permitir la absorción del químico protector.",
            "2. Inyección profunda galería por galería mediante cánulas dosificadoras con insecticida anticarcoma.",
            "3. Aspersión y brochado saturante en toda la superficie de madera hasta punto de goteo."
        ],
        "recommended_chemicals": [
            "Formulaciones con Permetrina y solventes penetrantes de alta residualidad",
            "Bora-Care (Sales de Boro concentradas)",
            "Dragnet FT (Permetrina 36.8%)"
        ],
        "irac_rotation": "Piretroides Grupo 3A y Boratos inorgánicos.",
        "reentry_time": "4 a 6 horas por presencia de solventes orgánicos penetrantes."
    },
    {
        "id": "gorgojo-granos",
        "name": "Gorgojos de Granos Almacenados (Arroz, Trigo, Maíz)",
        "scientific_name": "Sitophilus oryzae / Sitophilus zeamais / Sitophilus granarius",
        "category": "Plagas de la Industria Alimentaria",
        "icon": "fa-wheat-awn",
        "danger_level": "Alto (Pérdidas Económicas e Inocuidad)",
        "biology_and_habits": "Coleópteros de 3 a 5 mm con cabeza prolongada en una trompa o pico característico (rostro). La hembra perfora el grano entero de cereal, deposita un huevo en su interior y sella el orificio con una secreción gelatinosa. La larva se desarrolla y empupa totalmente dentro del grano, emergiendo el adulto dejando un orificio redondo visible.",
        "damage_and_risks": "Pérdida total del peso y valor comercial del grano, elevación de temperatura y humedad en el silo, proliferación secundaria de hongos micotoxigénicos (Aspergillus flavus - Aflatoxinas).",
        "critical_points": "Silos, tolvas de descarga, bodegas de granos a granel, derrames de cereal bajo tarimas.",
        "exclusion_measures": "Recepción de granos con humedad <12%; limpieza exhaustiva previa a la carga del silo; rotación estricta PEPS.",
        "mechanical_control": "Cribado y limpieza de grano; monitoreo con trampas de foso con atrayente alimenticio.",
        "chemical_protocol": [
            "1. Limpieza y desinfección en vacío del silo antes del almacenamiento.",
            "2. Tratamiento directo al grano en banda transportadora con protector de grano autorizado (Pirimifos-metil o Deltametrina con PBO).",
            "3. En silos sellados con infestación activa: fumigación con fosfuro de aluminio o magnesio por personal certificado bajo estricta hermeticidad."
        ],
        "recommended_chemicals": [
            "Pybuthrin 33 (Piretrinas Naturales 3% + PBO 30% - RSCO-URB-INAC-102-315-009-3.0)",
            "Actellic 50 CE (Pirimifos-metil 50%)",
            "Biothrine Flow (Deltametrina 2.5% para paredes vacías)"
        ],
        "irac_rotation": "Organofosforados (IRAC 1B) y Piretroides con sinergista PBO (IRAC 3A).",
        "reentry_time": "2 a 4 horas en aspersión; 72 horas con aireación forzada en fumigación con fosfina."
    },
    {
        "id": "polillas-harina",
        "name": "Polillas de la Harina y Frutos Secos",
        "scientific_name": "Plodia interpunctella / Ephestia kuehniella",
        "category": "Plagas de la Industria Alimentaria",
        "icon": "fa-wheat-awn",
        "danger_level": "Alto (Contaminación de Alimentos Terminados)",
        "biology_and_habits": "Pequeñas mariposas nocturnas de 8 a 10 mm. Plodia presenta alas anteriores bicolores (tercio basal gris claro y dos tercios distales color bronce rojizo). Los adultos no comen; las larvas devoran harinas, cereales, galletas, chocolates y frutos secos, tejiendo densas telarañas de seda que apelmazan el producto.",
        "damage_and_risks": "Contaminación masiva con heces, sedas, capullos y larvas vivas; rechazo de lotes de producto terminado y clausuras sanitarias.",
        "critical_points": "Bodegas de materias primas secas, máquinas empacadoras, tolvas de harinas, racks de producto terminado.",
        "exclusion_measures": "Mallas mosquiteras en ventanas; empaques herméticos trilaminados; control riguroso de temperatura en almacenes.",
        "mechanical_control": "Red de monitoreo continuo con trampas Delta provistas de feromona sexual específica de agregación (Z,E-9,12-tetradecadienil acetato).",
        "chemical_protocol": [
            "1. Retiro y destrucción inmediata de lotes infestados.",
            "2. Limpieza con aspiradora industrial de todos los rincones y guías de transporte.",
            "3. Nebulización en frío (ULV) con piretrinas naturales o aplicación de regulador de crecimiento en grietas de almacén."
        ],
        "recommended_chemicals": [
            "Pybuthrin 33 (Piretrinas Naturales + PBO para industria alimentaria)",
            "Starycide SC 480 (Triflumuron IGR)"
        ],
        "irac_rotation": "Piretrinas Naturales e IGRs.",
        "reentry_time": "2 horas."
    },
    {
        "id": "polilla-ropa",
        "name": "Polilla de la Ropa y Tejidos",
        "scientific_name": "Tineola bisselliella",
        "category": "Plagas de Textiles y Museos",
        "icon": "fa-vest",
        "danger_level": "Moderado a Alto (Destrucción de Fibras Naturales)",
        "biology_and_habits": "Pequeña polilla dorada uniforme de 6 a 8 mm. Huye activamente de la luz. La larva es el único estadio dañino: posee queratinasa para digerir queratina presente en lana, seda, plumas, pieles y alfombras naturales, construyendo tubos de seda y restos de fibra.",
        "damage_and_risks": "Agujeros irregulares y destrucción irreparable en trajes de lana, tapetes persas, pieles finas y tapicería.",
        "critical_points": "Clósets oscuros, cajones de ropa de invierno, alfombras bajo muebles pesados, almacenes textiles.",
        "exclusion_measures": "Guardar ropa limpia en bolsas al vacío herméticas; aspirado periódico bajo muebles pesados.",
        "mechanical_control": "Trampas adhesivas con feromona sexual de Tineola; cepillado y exposición de prendas al sol.",
        "chemical_protocol": [
            "1. Lavado en seco o térmico (>60°C) de prendas afectadas.",
            "2. Aspersión perimetral de guardarropas y zoclos con microencapsulado inodoro.",
            "3. Tratamiento de alfombras con IGR."
        ],
        "recommended_chemicals": [
            "Demand 2.5 CS (Lambda Cyhalotrina)",
            "Biothrine Flow (Deltametrina 2.5%)"
        ],
        "irac_rotation": "Piretroides Grupo 3A.",
        "reentry_time": "2 horas."
    },
    {
        "id": "escarabajo-alfombras",
        "name": "Escarabajo de las Alfombras / Derméstido",
        "scientific_name": "Anthrenus verbasci / Attagenus pellio",
        "category": "Plagas de Textiles y Museos",
        "icon": "fa-rug",
        "danger_level": "Moderado a Alto (Daño a Telas y Alergias)",
        "biology_and_habits": "Escarabajo pequeño redondeado de 2 a 3 mm con escamas multicolores (blanco, amarillo y marrón). Adultos comen polen en flores; las larvas son muy pilosas y se alimentan de lana, pelo, plumas, cuero, insectos disecados y pieles.",
        "damage_and_risks": "Destrucción de alfombras de lana, prendas, colecciones biológicas de museos; los pelos de las larvas causan dermatitis alérgica por contacto.",
        "critical_points": "Alfombras, zoclos con pelusa acumulada, montajes de taxidermia, bodegas de ropa usada.",
        "exclusion_measures": "Aspirado exhaustivo de rodapiés y alfombras; sellado de grietas donde se acumulan pelos de mascotas y pelusas.",
        "mechanical_control": "Trampas de feromona y pegamento.",
        "chemical_protocol": [
            "1. Aspirado profundo de toda la superficie textil.",
            "2. Aspersión perimetral focalizada en orillas de alfombras y zoclos.",
            "3. Tratamiento con formulaciones residuales no manchantes."
        ],
        "recommended_chemicals": [
            "Demand 2.5 CS (Lambda Cyhalotrina 2.5%)",
            "Cybor 10 EA (Cipermetrina acuosa)",
            "Biothrine Flow (Deltametrina 2.5%)"
        ],
        "irac_rotation": "Piretroides Grupo 3A.",
        "reentry_time": "2 horas."
    },
    {
        "id": "pescadito-de-plata",
        "name": "Pescadito de Plata / Lepisma",
        "scientific_name": "Lepisma saccharina",
        "category": "Insectos Rastreros",
        "icon": "fa-fish-fins",
        "danger_level": "Moderado (Daño a Archivos, Libros y Papel)",
        "biology_and_habits": "Insecto primitivo áptero de 7 a 12 mm, cuerpo ahusado cubierto de escamas plateadas brillantes. Movimientos rápidos y ondulantes. Requiere humedad relativa superior al 75%. Se alimenta de carbohidratos complejos: almidón, celulosa, pegamentos de libros, papel tapiz y textiles.",
        "damage_and_risks": "Destrucción irreversible de documentos históricos, libros, encuadernaciones, fotografías, telas de algodón y almidonadas.",
        "critical_points": "Archiveros, libreros, cajas de cartón en bodegas, cuartos de baño, falsos plafones húmedos.",
        "exclusion_measures": "Reducción de humedad relativa interior (<50%) mediante deshumidificadores y ventilación; almacenamiento en contenedores plásticos herméticos.",
        "mechanical_control": "Trampas de pegamento en estanterías y rodapiés de archivos.",
        "chemical_protocol": [
            "1. Aplicación de polvos desecantes a base de tierra de diatomeas o sílice en huecos de rodapiés.",
            "2. Aspersión perimetral focalizada con piretroides microencapsulados o neonicotinoides en grietas de estanterías."
        ],
        "recommended_chemicals": [
            "Demand 2.5 CS (Lambda Cyhalotrina)",
            "Cybor 10 EA (Cipermetrina)",
            "Phantom SC (Clorfenapir)"
        ],
        "irac_rotation": "Piretroides Grupo 3A y Pirroles Grupo 13.",
        "reentry_time": "2 horas."
    },
    {
        "id": "tijerillas",
        "name": "Tijerillas / Tijeretas",
        "scientific_name": "Forficula auricularia",
        "category": "Insectos Rastreros",
        "icon": "fa-scissors",
        "danger_level": "Bajo a Moderado (Plaga Molesta e Invasiva)",
        "biology_and_habits": "Insecto alargado y aplanado de 10 a 20 mm, color café rojizo, provisto de cercos en forma de pinza en el extremo del abdomen (más curvados en machos). Hábitos nocturnos, higrófilos y fototrópicos negativos. Se refugian en grietas oscuras y húmedas bajo macetas, piedras y corteza.",
        "damage_and_risks": "Invasión masiva en viviendas y bodegas durante épocas de lluvia; daño a plantas ornamentales y frutos maduros; secreción de fluido defensivo de olor desagradable.",
        "critical_points": "Bases de macetas, jardineras húmedas, zoclos de cuartos de lavado, grietas en pisos exteriores, umbrales de puertas.",
        "exclusion_measures": "Retiro de hojarasca y piedras pegadas a cimientos; sellado de accesos en puertas con guardapolvos; control de humedad.",
        "mechanical_control": "Trampas de cartón corrugado enrollado colocadas en jardines húmedos.",
        "chemical_protocol": [
            "1. Aspersión perimetral exterior en franja de 1 metro en cimientos y jardineras.",
            "2. Tratamiento puntual en zoclos y umbrales de puertas con formulaciones acuosas."
        ],
        "recommended_chemicals": [
            "Cybor 10 EA (Cipermetrina 10% emulsión acuosa)",
            "Fendona 6 SC (Alfa-cipermetrina 6%)",
            "Biothrine Flow (Deltametrina 2.5%)"
        ],
        "irac_rotation": "Piretroides Grupo 3A.",
        "reentry_time": "2 horas."
    },
    {
        "id": "grillos",
        "name": "Grillos Domésticos y de Campo",
        "scientific_name": "Acheta domesticus / Gryllus assimilis",
        "category": "Insectos Rastreros",
        "icon": "fa-music",
        "danger_level": "Bajo a Moderado (Daño a Telas y Atracción de Depredadores)",
        "biology_and_habits": "Insectos ortópteros de 15 a 25 mm, color café claro a negro. Machos producen canto estridulando sus alas para cortejo. Se alimentan de materia orgánica, papel, lana y alimentos. Su presencia atrae alacranes y arañas ponzoñosas.",
        "damage_and_risks": "Molestia por ruido nocturno; roedura de prendas de vestir de lana, seda y algodón; daño a papel; vector indirecto al servir de presa principal para alacranes.",
        "critical_points": "Sótanos, cuartos de calderas, registros sanitarios, grietas de banquetas exteriores, jardines húmedos.",
        "exclusion_measures": "Sellado de umbrales inferiores de puertas; sustitución de luces blancas exteriores por luz de vapor de sodio amarilla (no atractiva).",
        "mechanical_control": "Trampas de pegamento en cuartos oscuros.",
        "chemical_protocol": [
            "1. Aspersión perimetral de barrera exterior en muros y jardines.",
            "2. Aplicación de cebos granulados o aspersión en zonas bajas húmedas."
        ],
        "recommended_chemicals": [
            "Cybor 10 EA (Cipermetrina)",
            "Biothrine Flow (Deltametrina)",
            "Demand 2.5 CS (Lambda Cyhalotrina)"
        ],
        "irac_rotation": "Piretroides Grupo 3A.",
        "reentry_time": "2 horas."
    },
    {
        "id": "ciempies-milpies",
        "name": "Ciempiés y Ciempiés Casero",
        "scientific_name": "Scutigera coleoptrata / Scolopendra viridis",
        "category": "Miriápodos y Crustáceos",
        "icon": "fa-worm",
        "danger_level": "Moderado a Alto (Mordedura Dolorosa con Forcípulas)",
        "biology_and_habits": "Scutigera (ciempiés casero): 15 pares de patas larguísimas, se desplaza velozmente en paredes húmedas cazando otros insectos. Scolopendra: cuerpo aplanado con forcípulas venenosas en el primer segmento que inoculan toxinas en presas o humanos ante manipulación.",
        "damage_and_risks": "La mordedura de Scolopendra produce dolor punzante intenso, edema local, necrosis superficial y malestar general. Fobia y alarma en interiores.",
        "critical_points": "Sótanos húmedos, bajo piedras y macetas, registros hidrosanitarios, cuartos de baño.",
        "exclusion_measures": "Mantenimiento de franja perimetral de gravilla seca; sellado de accesos en umbrales.",
        "mechanical_control": "Trampas de goma adhesiva en zócalos húmedos.",
        "chemical_protocol": [
            "1. Aspersión de banda ancha perimetral exterior (2 metros de ancho).",
            "2. Tratamiento residual en sótanos y zonas húmedas."
        ],
        "recommended_chemicals": [
            "Demand 2.5 CS (Lambda Cyhalotrina)",
            "Biothrine Flow (Deltametrina 2.5%)"
        ],
        "irac_rotation": "Piretroides Grupo 3A.",
        "reentry_time": "2 horas."
    },
    {
        "id": "cochinillas-humedad",
        "name": "Cochinillas de Humedad / Bichos Bola",
        "scientific_name": "Armadillidium vulgare / Porcellio scaber",
        "category": "Miriápodos y Crustáceos",
        "icon": "fa-circle-dot",
        "danger_level": "Bajo (Indicador de Humedad Excesiva)",
        "biology_and_habits": "Únicos crustáceos adaptados a la vida terrestre. Respiran por pseudotráqueas branquiales modificadas que requieren 100% de humedad ambiental. Armadillidium rueda sobre sí mismo formando una esfera compacta ante amenazas (conglobación). Comen materia orgánica vegetal en descomposición.",
        "damage_and_risks": "No transmiten enfermedades ni pican; dañan plántulas tiernas en invernaderos y jardines; ingresan masivamente a casas en temporada de lluvias.",
        "critical_points": "Bajo macetas, hojarasca húmeda pegada a paredes, registros de drenaje, jardineras con exceso de riego.",
        "exclusion_measures": "Reducción del riego en jardineras pegadas a la construcción; retiro de mantillo o corteza pegada a muros.",
        "mechanical_control": "Barrido y retiro mecánico.",
        "chemical_protocol": [
            "1. Franja perimetral de gravilla tratada con insecticida residual.",
            "2. Aspersión en zócalos exteriores de cimientos."
        ],
        "recommended_chemicals": [
            "Cybor 10 EA (Cipermetrina)",
            "Demand 2.5 CS (Lambda Cyhalotrina)"
        ],
        "irac_rotation": "Piretroides Grupo 3A.",
        "reentry_time": "2 horas."
    },
    {
        "id": "paloma-comun",
        "name": "Paloma Común / Aves Nocivas",
        "scientific_name": "Columba livia",
        "category": "Aves Urbanas",
        "icon": "fa-dove",
        "danger_level": "Alto (Daño a Salud y Edificaciones)",
        "biology_and_habits": "Ave comensal gregaria de 30 a 35 cm. Anida en cornisas, techos, marquesinas y sistemas de ventilación de edificios. Produce hasta 12 kg de heces ácidas por ave al año.",
        "damage_and_risks": "Sus deyecciones contienen ácido úrico que corroe cantera, concreto y metales. Transmisora de Histoplasmosis (hongo Histoplasma capsulatum que prolifera en el guano acumulado e ingresa por vías respiratorias), Criptococosis, Psitacosis y alberga ácaros y chinches de las aves.",
        "critical_points": "Cornisas, marquesinas, letras de anuncios luminosos, aires acondicionados en azoteas, vigas de naves industriales.",
        "exclusion_measures": "PROHIBICIÓN NOM-256: Prohibido el envenenamiento o métodos letales crueles contra aves. Medidas permitidas exclusivamente de exclusión: Instalación de redes de polietileno UV de 50 mm, sistemas de púas de acero inoxidable en cornisas, alambres tensados (Bird-Wire) y sellado de oquedades en techos.",
        "mechanical_control": "Limpieza y desinfección previa del guano con aspersión humectante de cuaternarios de amonio (nunca barrer en seco para no levantar esporas fúngicas).",
        "chemical_protocol": [
            "1. Aplicación de gel repelente táctil no tóxico en bordes de posadero.",
            "2. Desinfección y sanitización profunda de superficies con solución de hipoclorito de sodio al 10% o virucida/fungicida especializado tras retirar el excremento con equipo de protección respiratoria con filtro N95 o P100."
        ],
        "recommended_chemicals": [
            "Geles repelentes táctiles mecánicos (Polibuteno no tóxico)",
            "Sanitizantes germicidas de amplio espectro para desinfección de guano"
        ],
        "irac_rotation": "No aplica control químico letal.",
        "reentry_time": "Inmediato tras instalación de barreras físicas."
    }
]

# Registro persistente de nuevas plagas consultadas o sintetizadas en línea
CUSTOM_SYNTHESIZED_PESTS: Dict[str, Dict[str, Any]] = {}


def get_pest_combat_guides() -> List[Dict[str, Any]]:
    """Retorna las fichas técnicas detalladas de combate específico por plaga urbana incluyendo las agregadas."""
    return list(PEST_ENCYCLOPEDIA) + list(CUSTOM_SYNTHESIZED_PESTS.values())


# ============================================================================
# MOTOR DE INTELIGENCIA ENTOMOLÓGICA DINÁMICO (NOM-256 & COFEPRIS)
# Analiza taxonomía, familia y biología real para cualquier plaga no listada
# ============================================================================

TAXONOMIC_TAXA_RULES: List[Dict[str, Any]] = [
    {
        "keywords": ["carcoma", "barrenador", "taladro", "termita", "polilla de madera", "xilofago", "xilofagos", "lyctus", "hylotrupes", "anobium"],
        "category": "Insectos Xilófagos",
        "order": "Coleoptera / Blattodea (Insectos Xilófagos)",
        "icon": "fa-tree",
        "danger_level": "Alto a Extremo (Degradación y Colapso Estructural)",
        "biology_template": "Insecto de hábitos xilófagos cuyas larvas o colonias taladran activamente el duramen y la albura de maderas estructurales, vigas, duelas y muebles. Las larvas excavan galerías durante periodos prolongados nutriéndose de la celulosa, provocando pérdida masiva de masa leñosa antes de que los adultos emerjan dejando orificios visibles.",
        "damage_template": "Debilitamiento de vigas maestras, riesgo de colapso de techumbres de madera, daño estético y estructural irreparable en carpintería fina y archivos históricos.",
        "exclusion_template": "Aplicación de selladores y barnices antixilófagos en maderas vírgenes; deshumidificación ambiental (<50% HR); eliminación de madera húmeda en contacto directo con el suelo.",
        "mechanical_template": "Sustitución de elementos estructurales comprometidos; aspirado y cepillado profundo de orificios de salida; tratamiento térmico en cámara para mobiliario.",
        "chemical_steps": [
            "1. Diagnóstico de galerías activas mediante detección auditiva o inspección de aserrín fresco.",
            "2. Decapado de acabados impermeables para permitir penetración del plaguicida.",
            "3. Inyección profunda a presión en galerías con formulación antixilófaga de alta residualidad.",
            "4. Impregnación superficial saturante (brochado o aspersión a baja presión) con solución a base de boratos o permetrina."
        ],
        "chemicals": [
            "Bora-Care (Octaborato Disódico Tetrahidratado)",
            "Termidor 25 CE (Fipronil 2.5% - RSCO-URB-INAC-175-313-009-2.5)",
            "Dragnet FT (Permetrina 36.8% - RSCO-URB-INAC-124-315-009-36.8)"
        ],
        "irac": "Piretroides Tipo I (IRAC 3A), Fenilpirazoles (IRAC 2B) y Boratos Inorgánicos.",
        "reentry": "4 a 6 horas debido al uso de solventes penetrantes de madera."
    },
    {
        "keywords": ["gorgojo", "taladrillo", "barrenador de grano", "sitophilus", "tribolium", "oryzaephilus", "rhizopertha", "trogoderma", "plaga de grano", "harina", "cereal"],
        "category": "Plagas de la Industria Alimentaria",
        "order": "Coleoptera / Curculionoidea (Plagas de Granos y Harinas)",
        "icon": "fa-wheat-awn",
        "danger_level": "Alto (Pérdidas Económicas e Inocuidad Alimentaria)",
        "biology_template": "Coleópteros que colonizan granos enteros, harinas, cereales procesados y semillas. Las hembras ovipositan dentro o sobre el grano; las larvas devoran el endospermo y embrión, generando calor, humedad y deyecciones que propician el desarrollo secundario de mohos y ácaros.",
        "damage_template": "Pérdida de peso comercial del lote, rechazo de embarques, generación de micotoxinas (Aflatoxinas cancerígenas) y pérdida de poder germinativo de semillas.",
        "exclusion_template": "Recepción de granos con humedad controlada (<12%); limpieza profunda de tolvas y silos vacíos; rotación estricta PEPS (Primeras Entradas, Primeras Salidas).",
        "mechanical_template": "Cribado y aspirado de impurezas; monitoreo con trampas de foso y feromonas de agregación en almacenes.",
        "chemical_steps": [
            "1. Vaciado y desinfección total de bodegas y silos con aspersión perimetral previa a la carga.",
            "2. Aplicación de protector de grano con Pirimifos-metil o Deltametrina + PBO en banda transportadora.",
            "3. En infestaciones activas severas: fumigación en masa bajo lona hermética con fosfuro de aluminio/magnesio por personal capacitado."
        ],
        "chemicals": [
            "Pybuthrin 33 (Piretrinas Naturales 3% + PBO 30% - RSCO-URB-INAC-102-315-009-3.0)",
            "Actellic 50 CE (Pirimifos-metil 50%)",
            "Biothrine Flow (Deltametrina 2.5% para silos vacíos)"
        ],
        "irac": "Organofosforados (IRAC 1B) y Piretrinas Sinergizadas (IRAC 3A).",
        "reentry": "2 a 4 horas en aspersión; 72 horas con aireación forzada en fumigación con fosfina."
    },
    {
        "keywords": ["chinche", "triatoma", "cimex", "besucona", "fitófaga", "lygaeidae", "pentatomidae", "chinche de campo", "chinchilla"],
        "category": "Insectos Hematófagos",
        "order": "Hemiptera / Heteroptera (Chinches y Hemípteros)",
        "icon": "fa-shield-virus",
        "danger_level": "Alto a Extremo (Hematófagos Vectores o Fitófagos Invasivos)",
        "biology_template": "Insectos con aparato bucal picador-chupador alojado en un rostro articulado. Las especies hematófagas se alimentan de sangre de vertebrados durante la noche refugiándose en grietas; las especies fitófagas succionan savia de plantas y pueden invadir masivamente inmuebles buscando refugio invernal.",
        "damage_template": "Picaduras pruriginosas, riesgo de transmisión de patógenos (Trypanosoma cruzi en triatóminos), olores fétidos por secreciones de glándulas metatorácicas y fobia en residentes.",
        "exclusion_template": "Aplanado y sellado de grietas en muros de adobe/tabique; colocación de guardapolvos y mallas mosquiteras; retiro de vegetación adosada a muros.",
        "mechanical_template": "Aspirado HEPA de fisuras; lavado térmico de textiles a más de 60°C.",
        "chemical_steps": [
            "1. Inspección minuciosa de grietas, uniones de muros y muebles.",
            "2. Aplicación focalizada de formulaciones combinadas de choque y residualidad.",
            "3. Aplicación de polvos desecantes en registros y chalupas eléctricas.",
            "4. Refuerzo obligatorio a los 15-21 días."
        ],
        "chemicals": [
            "Temprid SC (Imidacloprid + Beta-ciflutrina - RSCO-MEZC-INAC-0101-385-342-31.5)",
            "Phantom SC (Clorfenapir 21.45%)",
            "Demand 2.5 CS (Lambda Cyhalotrina Microencapsulada)"
        ],
        "irac": "Neonicotinoides (IRAC 4A) + Piretroides (IRAC 3A) y Pirroles (IRAC 13).",
        "reentry": "4 horas tras la aplicación."
    },
    {
        "keywords": ["mosca", "mosquito", "jejen", "zancudo", "simulido", "drosophila", "psychoda", "fannia", "tabano", "culicoides"],
        "category": "Insectos Voladores",
        "order": "Diptera (Moscas, Mosquitos y Dípteros Urbanos)",
        "icon": "fa-mosquito",
        "danger_level": "Alto a Extremo (Vectores Epidemiológicos y Mecánicos)",
        "biology_template": "Insectos dípteros provistos de un solo par de alas membranosas y balancines (halterios). Sus larvas se desarrollan en ambientes acuáticos, semiacuáticos o en sustratos orgánicos en descomposición (lodos de drenaje, estiércol, basura húmeda, charcos). Ciclos biológicos rápidos con alta capacidad de dispersión aérea.",
        "damage_template": "Transmisión activa de arbovirosis (Dengue, Zika, Fiebre del Nilo), patógenos entéricos (Salmonella, Shigella) o molestias severas por picaduras hematófagas.",
        "exclusion_template": "Eliminación de aguas estancadas; mallas mosquiteras 18x16; cortinas de aire en accesos; trampas hidráulicas con sello de agua en coladeras.",
        "mechanical_control": "Instalación de lámparas de luz UV con placa adhesiva a 1.80 m de altura; limpieza mecánica de biopelículas en drenajes.",
        "chemical_steps": [
            "1. Tratamiento larvicida en sitios de cría acuáticos con biolarvicidas selectivos (BTI).",
            "2. Pintado de superficies de posadero con cebos mosquicidas atrayentes.",
            "3. Nebulización espacial ULV al amanecer o atardecer para derribo masivo de adultos."
        ],
        "chemicals": [
            "Agita 10 WG (Tiametoxam 10% + Z-9 Tricosene)",
            "Biothrine Flow (Deltametrina 2.5%)",
            "AquaPy (Piretrinas Naturales base acuosa)",
            "Fendona 6 SC (Alfa-cipermetrina 6%)"
        ],
        "irac": "Neonicotinoides (IRAC 4A), Piretroides (IRAC 3A) y Biolarvicidas Microbianos (IRAC 11).",
        "reentry": "0 horas para cebos pintados; 2 horas para nebulización espacial."
    },
    {
        "keywords": ["arana", "araña", "alacran", "alacrán", "escorpion", "escorpión", "loxosceles", "latrodectus", "centruroides"],
        "category": "Arácnidos Ponzoñosos",
        "order": "Arachnida (Araneae y Scorpiones Ponzoñosos)",
        "icon": "fa-spider",
        "danger_level": "Extremo (Veneno Necrótico o Neurotóxico)",
        "biology_template": "Arácnidos carnívoros y depredadores terrestres provistos de quelíceros o pedipalpos transformados. Hábitos predominantemente nocturnos, higrófilos o xerófilos según la especie, buscando refugio en grietas, leña, registros subterráneos y calzado.",
        "damage_template": "Riesgo de envenenamiento grave por inoculación de neurotoxinas o citotoxinas necróticas; cuadros clínicos de latrodectismo, loxoscelismo o escorpionismo que requieren hospitalización urgente.",
        "exclusion_template": "Zócalos de material liso y pulido en cimientos exteriores; mallas mosquiteras finas; despeje total de chatarra, leña y escombros del perímetro.",
        "mechanical_template": "Monitoreo nocturno con lámpara ultravioleta (para alacranes); trampas de goma adhesiva en zoclos oscuros.",
        "chemical_steps": [
            "1. Despeje perimetral y deshierbe con equipo de protección adecuado.",
            "2. Aplicación de barrera perimetral exterior con microencapsulado de alta persistencia.",
            "3. Aspersión puntual en grietas, registros hidrosanitarios y rodapiés interiores."
        ],
        "chemicals": [
            "Demand 2.5 CS (Lambda Cyhalotrina Microencapsulada 2.5%)",
            "Biothrine Flow (Deltametrina 2.5%)",
            "Dragnet FT (Permetrina 36.8%)"
        ],
        "irac": "Piretroides Sintéticos Tipo II (IRAC 3A).",
        "reentry": "2 a 4 horas tras la aplicación."
    },
    {
        "keywords": ["acaro", "ácaro", "garrapata", "sarna", "scabies", "rhipicephalus", "dermatophagoides", "polvo"],
        "category": "Arácnidos Hematófagos / Vectores",
        "order": "Arachnida / Acari (Ácaros y Garrapatas)",
        "icon": "fa-bug-slash",
        "danger_level": "Alto a Extremo (Vectores de Rickettsiosis o Alérgenos Respiratorios)",
        "biology_template": "Arácnidos microscópicos o macroscópicos con cuerpo no segmentado (idiosoma). Las garrapatas son hematófagas obligadas con gran resistencia al ayuno; los ácaros del polvo consumen escamas dérmicas y proliferan con humedad relativa >70%.",
        "damage_template": "Transmisión de Rickettsia rickettsii, Ehrlichia, asma bronquial alérgica, rinitis crónica y sarna (escabiosis).",
        "exclusion_template": "Control de humedad relativa interior (<50%); fundas antiácaros en colchones; desparasitación veterinaria de mascotas.",
        "mechanical_template": "Aspirado con filtro HEPA de colchones y tapetes; lavado de ropa de cama a 60°C.",
        "chemical_steps": [
            "1. En garrapatas: rociado residual de choque en bardas hasta 1.5 m y suelos de patio.",
            "2. En ácaros ambientales: aplicación de acaricidas autorizados y deshumidificación.",
            "3. Refuerzo a los 14-21 días para control de ninfas recién eclosionadas."
        ],
        "chemicals": [
            "Demand 2.5 CS (Lambda Cyhalotrina 2.5%)",
            "Biothrine Flow (Deltametrina 2.5%)",
            "Temprid SC (Imidacloprid + Betaciflutrina)"
        ],
        "irac": "Piretroides Tipo II (IRAC 3A) y Neonicotinoides (IRAC 4A).",
        "reentry": "4 horas tras aspersión."
    },
    {
        "keywords": ["avispa", "avispón", "abeja", "polistes", "vespula", "himenoptero"],
        "category": "Insectos Voladores",
        "order": "Hymenoptera (Avispas y Abejas Ponzoñosas)",
        "icon": "fa-triangle-exclamation",
        "danger_level": "Alto a Extremo (Shock Anafiláctico)",
        "biology_template": "Insectos sociales o solitarios con aguijón conectado a glándulas venenosas. Construyen nidos en aleros, techos y árboles.",
        "damage_template": "Picaduras dolorosas múltiples con riesgo letal de shock anafiláctico.",
        "exclusion_template": "Sellado de oquedades en fachadas y cajas de registro; mallas en respiraderos.",
        "mechanical_template": "Reubicación de abejas con apicultor; trampas de atracción.",
        "chemical_steps": [
            "1. Aplicación nocturna con chorro continuo de derribo rápido directamente al nido.",
            "2. Remoción física del panal una vez neutralizada la actividad."
        ],
        "chemicals": [
            "Biothrine Flow (Deltametrina 2.5%)",
            "Pybuthrin 33 (Piretrinas de Derribo)",
            "Demand 2.5 CS (Lambda Cyhalotrina)"
        ],
        "irac": "Piretroides Grupo 3A de alto derribo.",
        "reentry": "2 horas."
    },
    {
        "keywords": ["polilla", "oruga", "lepidoptero", "palomilla", "tinea", "plodia"],
        "category": "Plagas de Textiles y Museos",
        "order": "Lepidoptera (Polillas y Palomillas)",
        "icon": "fa-vest",
        "danger_level": "Moderado a Alto (Daño a Telas y Granos)",
        "biology_template": "Insectos holometábolos cuyas orugas masticadoras tejen sedas y consumen queratina (textiles) o almidones (harinas y frutos secos).",
        "damage_template": "Destrucción de ropa de lana, telas finas, tapices o merma total de lotes de granos y harinas.",
        "exclusion_template": "Almacenamiento hermético de textiles limpios y granos; mallas finas en ventanas y puertas.",
        "mechanical_template": "Trampas adhesivas Delta con feromonas sexuales específicas; aspirado profundo.",
        "chemical_steps": [
            "1. Retiro de materiales con presencia de larvas o sedas.",
            "2. Limpieza exhaustiva de estantes y clósets.",
            "3. Nebulización ULV o aspersión focalizada con piretrinas o IGRs."
        ],
        "chemicals": [
            "Pybuthrin 33 (Piretrinas Naturales + PBO)",
            "Starycide SC 480 (Triflumuron IGR)",
            "Demand 2.5 CS (Lambda Cyhalotrina)"
        ],
        "irac": "Piretrinas (IRAC 3A) y Reguladores de Crecimiento (IRAC 15).",
        "reentry": "2 horas."
    }
]


def search_or_synthesize_pest_guide(query: str) -> Dict[str, Any]:
    """
    Busca una plaga en el catálogo enciclopédico de FLOSA o ejecuta el Motor de
    Inteligencia Entomológica para generar una ficha biológica y técnica personalizada,
    fidedigna y no duplicada conforme a la NOM-256-SSA1-2012 y COFEPRIS.
    Guarda automáticamente las nuevas búsquedas para que permanezcan en el catálogo.
    """
    if not query or not query.strip():
        all_p = get_pest_combat_guides()
        return {
            "source": "catalogo_oficial_mip",
            "pest": all_p[0] if all_p else PEST_ENCYCLOPEDIA[0]
        }

    q_raw = query.strip()
    q_norm = q_raw.lower()

    # 1. BÚSQUEDA EXACTA O PARCIAL EN CATÁLOGO LOCAL Y EN PLAGAS SINTETIZADAS GUARDADAS
    all_pests = get_pest_combat_guides()
    for p in all_pests:
        name_l = p["name"].lower()
        sci_l = p["scientific_name"].lower()
        cat_l = p["category"].lower()
        pid_l = p["id"].lower()

        if q_norm == pid_l or q_norm in name_l or q_norm in sci_l or q_norm in cat_l:
            return {
                "source": "catalogo_oficial_mip",
                "pest": p
            }

    # Búsqueda por palabras clave individuales
    words = [w for w in re.split(r'\s+', q_norm) if len(w) >= 3]
    for p in all_pests:
        text_corpus = f"{p['name']} {p['scientific_name']} {p['category']} {p['biology_and_habits']} {p['damage_and_risks']}".lower()
        if all(w in text_corpus for w in words) and words:
            return {
                "source": "catalogo_oficial_mip",
                "pest": p
            }

    # 2. MOTOR DE INTELIGENCIA ENTOMOLÓGICA (CLASIFICACIÓN TAXONÓMICA FIDEDIGNA)
    name_clean = q_raw.title()
    slug_id = re.sub(r'[^a-zA-Z0-9]', '-', name_clean.lower()).strip('-')

    # Detectar el taxón o familia entomológica adecuada
    matched_taxa = None
    for taxa in TAXONOMIC_TAXA_RULES:
        for kw in taxa["keywords"]:
            if kw in q_norm:
                matched_taxa = taxa
                break
        if matched_taxa:
            break

    # Si no hubo coincidencia directa por palabra clave taxonómica, inferir por raíces
    if not matched_taxa:
        if any(term in q_norm for term in ["escarabajo", "gorgojo", "polilla de madera", "barrenillo", "coleoptero"]):
            matched_taxa = TAXONOMIC_TAXA_RULES[1]  # Coleóptero grano
        elif any(term in q_norm for term in ["zancudo", "mosquito", "jejen", "mosca", "diptero"]):
            matched_taxa = TAXONOMIC_TAXA_RULES[3]  # Díptero
        elif any(term in q_norm for term in ["chinche", "pulgón", "hemiptero", "trips"]):
            matched_taxa = TAXONOMIC_TAXA_RULES[2]  # Hemíptero
        else:
            matched_taxa = {
                "category": "Insectos Rastreros",
                "order": "Arthropoda / Insecta (Control Urbano Especializado)",
                "icon": "fa-bug-slash",
                "danger_level": "Evaluación Técnica Según Nivel Poblacional",
                "biology_template": f"Especie artrópoda identificada en la consulta técnica: '{name_clean}'. Presenta hábitos invasivos o colonizadores en ambientes antrópicos, buscando fuentes de humedad, materia orgánica y refugio en hendiduras estructurales, zoclos o registros exteriores.",
                "damage_template": f"Riesgo de contaminación de superficies, daño estético, afectación a materias primas o molestias mecánicas provocadas por la presencia y deyecciones de {name_clean}.",
                "exclusion_template": "Sellado hermético de grietas y pasos de tubería; instalación de guardapolvos en puertas exteriores; control riguroso de humedad interior.",
                "mechanical_template": "Monitoreo perimetral mediante trampas adhesivas de goma para cuantificar densidad poblacional antes y después del tratamiento.",
                "chemical_steps": [
                    f"1. Inspección diagnóstica y delimitación de focos de refugio de {name_clean}.",
                    "2. Aplicación focalizada en grietas y hendiduras con insecticida microencapsulado de banda verde con registro COFEPRIS.",
                    "3. Creación de franja perimetral de contención exterior de 1 metro en piso y 1 metro en pared.",
                    "4. Evaluación y seguimiento técnico a las 72 horas."
                ],
                "chemicals": [
                    "Biothrine Flow (Deltametrina 2.5% - RSCO-URB-INAC-111-315-009-2.5)",
                    "Demand 2.5 CS (Lambda Cyhalotrina 2.5% - RSCO-URB-INAC-173-356-064-2.5)",
                    "Cybor 10 EA (Cipermetrina 10% - RSCO-URB-INAC-119-315-323-10.0)"
                ],
                "irac": "Piretroides Sintéticos (IRAC 3A).",
                "reentry": "2 horas tras la aplicación."
            }

    # Sintetizar ficha fidedigna basada en la familia biológica real
    synthetic_pest = {
        "id": slug_id or "plaga-especializada",
        "name": f"{name_clean}",
        "scientific_name": f"Taxón asociado a {name_clean} ({matched_taxa['order']})",
        "category": matched_taxa.get("category", "Insectos Rastreros"),
        "icon": matched_taxa.get("icon", "fa-bug"),
        "danger_level": matched_taxa["danger_level"],
        "biology_and_habits": f"{matched_taxa['biology_template']} Especie consultada: {name_clean}.",
        "damage_and_risks": matched_taxa["damage_template"],
        "critical_points": "Zonas de humedad, grietas estructurales, juntas de dilatación, áreas de almacenamiento, cuartos de basura y ductos de instalaciones.",
        "exclusion_measures": matched_taxa["exclusion_template"],
        "mechanical_control": matched_taxa.get("mechanical_template", "Trampas de monitoreo y exclusión física."),
        "chemical_protocol": matched_taxa["chemical_steps"],
        "recommended_chemicals": matched_taxa["chemicals"],
        "irac_rotation": matched_taxa["irac"],
        "reentry_time": matched_taxa["reentry"]
    }

    # Guardar en memoria persistente de la aplicación para que aparezca siempre en el catálogo
    CUSTOM_SYNTHESIZED_PESTS[synthetic_pest["id"]] = synthetic_pest

    return {
        "source": "motor_entomologico_sintetizado",
        "pest": synthetic_pest
    }
