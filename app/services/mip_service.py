"""app/services/mip_service.py
Servicio de Contenidos del Manual Integral de Control de Plagas (MIP / IPM),
Guías de Combate Específico por Plaga y Sembrado Oficial de Registros RSCO.
Conforme a la NOM-256-SSA1-2012, COFEPRIS y NOM-017-STPS.
"""

from typing import List, Dict, Any
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
            # Actualizar datos si existen
            for k, v in data.items():
                setattr(existing, k, v)
    db.commit()
    return added


def get_mip_full_manual() -> Dict[str, Any]:
    """Retorna el contenido estructurado del Manual Integral de Control de Plagas Urbanas."""
    return {
        "title": "MANUAL INTEGRAL DE MANEJO DE PLAGAS URBANAS (MIP)",
        "subtitle": "Guía Técnica Operativa Conforme a la NOM-256-SSA1-2012, COFEPRIS y Normas STPS",
        "company": "FUMIFLOSA - Control de Plagas Urbanas",
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


def get_pest_combat_guides() -> List[Dict[str, Any]]:
    """Retorna las fichas técnicas detalladas de combate específico por plaga urbana."""
    return [
        {
            "id": "cucaracha-alemana",
            "name": "Cucaracha Germánica / Alemana",
            "scientific_name": "Blattella germanica",
            "category": "Insectos Rastreros",
            "icon": "fa-bug",
            "danger_level": "Alto (Vector Mecánico)",
            "biology_and_habits": "Mide de 10 a 15 mm, color café claro con dos franjas oscuras paralelas en el pronoto. Es la plaga urbana más frecuente en cocinas, restaurantes y hospitales. Hábitos estrictamente nocturnos y tigmotácticos (busca refugios estrechos donde su cuerpo haga contacto con dos superficies). Una hembra produce de 4 a 8 ootecas a lo largo de su vida, cada una con 30 a 48 embriones, con un ciclo de desarrollo de apenas 60 días a 28°C.",
            "damage_and_risks": "Transmisora de patógenos entéricos como Salmonella spp., Escherichia coli, Shigella, quistes de amebas y huevos de helmintos. Sus heces, mudas y restos corporales son potentes alérgenos causantes de asma y rinitis crónica en niños y personas vulnerables.",
            "critical_points": "Motores de refrigeradores y congeladores, compresores de cafeteras, grietas en azulejos, bisagras de alacenas, partes inferiores de mesas calientes, huecos en contactos eléctricos.",
            "exclusion_measures": "Sellado hermético de zoclos, azulejos y huecos en paredes con silicón antihongos; sustitución de tarimas de madera por plástico; eliminación inmediata de cartón ondulado (fuente principal de ingreso pasivo de ootecas).",
            "mechanical_control": "Colocación de trampas de goma con atrayente alimenticio/feromona agregativa en esquinas y bajo equipos para monitoreo y estimación del nivel de infestación (umbral de acción: >1 cucaracha/trampa/semana).",
            "chemical_protocol": [
                "1. Diagnóstico y aspirado previo de refugios masivos con filtro HEPA.",
                "2. Aplicación estratégica de cebo en gel (Fipronil o Indoxacarb) mediante micropuntos (0.25 a 0.5 g) en grietas, bisagras y motores donde los insectos forrajean.",
                "3. Aplicación de Regulador de Crecimiento de Insectos (IGR: Piriproxifeno o Triflumuron) para esterilizar a los adultos y deformar las ninfas.",
                "4. Aspersión perimetral focalizada en zócalos y tuberías con insecticida microencapsulado o no repelente (evitar aspersión generalizada que disperse la colonia)."
            ],
            "recommended_chemicals": [
                "Maxforce Forte (Fipronil 0.05% - RSCO-URB-INAC-175-359-392-0.05)",
                "Advion Cucaracha Gel (Indoxacarb 0.6% - RSCO-URB-INAC-102K-301-392-0.6)",
                "Temprid SC (Imidacloprid + Beta-ciflutrina - RSCO-MEZC-INAC-0101-385-342-31.5)",
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
            "id": "rata-alcantarilla",
            "name": "Rata Noruega / De Alcantarilla",
            "scientific_name": "Rattus norvegicus",
            "category": "Roedores Comensales",
            "icon": "fa-shield-cat",
            "danger_level": "Crítico (Daño Sanitario y Estructural)",
            "biology_and_habits": "Roedor robusto de 20 a 25 cm (sin cola), peso de 300 a 500 g. Hocico chato, orejas cortas y cola más corta que la longitud de la cabeza más el cuerpo. Excava madrigueras subterráneas con salidas de emergencia cerca de cimientos, basureros y márgenes de ríos/drenajes. Excelente nadadora y buceadora capaz de ingresar a través de tazas sanitarias.",
            "damage_and_risks": "Transmisora de Leptospirosis (*Leptospira interrogans* a través de orina), Hantavirus, Peste bubónica, Tifus murino y Mordedura de rata. Su hábito de roer continuo daña cables eléctricos (causante del 25% de incendios de origen desconocido), tuberías de PVC y empaques.",
            "critical_points": "Montículos de tierra cerca de cimientos (entradas de madrigueras), coladeras rotas, cuartos de basura exterior, andenes de carga, tarimas apiladas en el exterior.",
            "exclusion_measures": "Sellado con concreto reforzado con malla de acero en cimientos; placas de lámina galvanizada en la base de puertas exteriores; rejillas metálicas de alta resistencia en drenajes pluviales.",
            "mechanical_control": "En interiores: trampas de impacto de uso rudo (T-Rex) colocadas perpendiculares a los muros dentro de túneles de protección. Prohibido rodenticida químico en áreas de proceso de alimentos.",
            "chemical_protocol": [
                "1. Inspección perimetral y mapeo de madrigueras activas.",
                "2. Colocación de cebaderos de seguridad anclados en el perímetro exterior cada 10 a 15 metros.",
                "3. Sujeción de bloques parafinados extruidos de segunda generación (Flocumafen o Brodifacoum) en las varillas internas de cada cebadero para evitar que el roedor traslade el cebo.",
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
            "name": "Chinche de Cama",
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
            "id": "alacranes",
            "name": "Alacranes / Escorpiones Urbanos",
            "scientific_name": "Centruroides spp. (C. limpidus, C. sculpturatus)",
            "category": "Arácnidos Ponzoñosos",
            "icon": "fa-skull-crossbones",
            "danger_level": "Extremo (Veneno Neurotóxico Potencialmente Letal)",
            "biology_and_habits": "Arácnidos nocturnos provistos de pinzas (pedipalpos) y un metasoma (cola) terminado en un telson con aguijón conectado a glándulas venenosas. En México las especies peligrosas pertenecen al género *Centruroides* (color amarillo pajizo o pardo claro, pinzas delgadas y un pequeño dientecillo o tubérculo subaculear bajo el aguijón). Se refugian en escombros, madera, calzado, ropa colgada y grietas.",
            "damage_and_risks": "La picadura de especies tóxicas inyecta escorpaminas (neurotoxinas) que provocan dolor local quemante, parestesias, sensación de cuerpo extraño en la garganta, sialorrea (salivación excesiva), nistagmo, dificultad respiratoria, convulsiones y riesgo de paro respiratorio en niños y adultos mayores.",
            "critical_points": "Patios con escombros, leña apilada, registros de agua potable, grietas en muros de piedra, rodapiés, falsos plafones, clósets en planta baja.",
            "exclusion_measures": "Zócalos de azulejo liso en la base exterior de las paredes (los alacranes no pueden trepar superficies pulidas); colocación de mosquiteros y guardapolvos herméticos; revisión obligatoria de calzado antes de ponérselo.",
            "mechanical_control": "Búsqueda nocturna con lámpara de luz ultravioleta (la cutícula del alacrán presenta fluorescencia azul-verdosa brillante) y remoción mecánica segura con pinzas largas.",
            "chemical_protocol": [
                "1. Despeje previo de escombros y deshierbe perimetral con guantes de carnaza y calzado industrial.",
                "2. Aplicación de barrera perimetral exterior con insecticida microencapsulado de alto poder residual (Demand 2.5 CS o Biothrine Flow) en una franja de 1 metro en el piso y 1 metro en la pared.",
                "3. Aspersión en marcos de puertas, ventanas, zoclos y registros hidrosanitarios."
            ],
            "recommended_chemicals": [
                "Demand 2.5 CS (Lambda Cyhalotrina 2.5% - RSCO-URB-INAC-173-356-064-2.5)",
                "Biothrine Flow (Deltametrina 2.5% - RSCO-URB-INAC-111-315-009-2.5)",
                "Dragnet FT (Permetrina 36.8% - RSCO-URB-INAC-124-315-009-36.8)"
            ],
            "irac_rotation": "Piretroides Tipo II de prolongada estabilidad residual.",
            "reentry_time": "2 a 4 horas. En caso de picadura, aplicar faboterápico antialacrán en clínica médica y llamar a SINTOX 800-009-2800."
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
            "critical_points": "Contenedores de basura descubiertos, compac-tadores de residuos, andenes de recepción de materias primas perecederas, áreas de lavado de loza.",
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
            "id": "hormigas-urbanas",
            "name": "Hormigas Urbanas (Loca, Argentina, Fantasma)",
            "scientific_name": "Linepithema humile, Paratrechina longicornis",
            "category": "Insectos Rastreros",
            "icon": "fa-cubes-stacked",
            "danger_level": "Moderado a Alto (Hospitalario)",
            "biology_and_habits": "Insectos sociales que viven en colonias complejas con una o múltiples reinas (poliginia). En el medio urbano forman senderos persistentes de forrajeo siguiendo feromonas de pista hacia fuentes de azúcares, proteínas y grasas. Fenómeno de fragmentación (*budding*): si se aplica insecticida repelente de contacto, la colonia se fragmenta en múltiples nidos satélites multiplicando la infestación.",
            "damage_and_risks": "En hospitales y clínicas transportan bacterias nosocomiales (*Staphylococcus aureus*, *Pseudomonas*) directamente a quirófanos, áreas de neonatos y equipo estéril. En oficinas dañan equipos informáticos al anidar en fuentes de poder.",
            "critical_points": "Jardineras adyacentes a muros, hendiduras en banquetas, ductos eléctricos, tarjas de cocina, máquinas expendedoras de café.",
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
            "id": "termitas",
            "name": "Termita Subterránea",
            "scientific_name": "Reticulitermes spp., Coptotermes",
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
            "id": "granos-almacenados",
            "name": "Plagas de Granos Almacenados (Gorgojos y Polillas)",
            "scientific_name": "Sitophilus oryzae, Ephestia kuehniella, Plodia interpunctella",
            "category": "Plagas de la Industria Alimentaria",
            "icon": "fa-wheat-awn",
            "danger_level": "Alto (Pérdidas Económicas e Inocuidad)",
            "biology_and_habits": "Coleópteros y lepidópteros cuyas larvas se alimentan en el interior de granos de cereal, harinas, pastas, frutos secos y semillas. Las polillas adultas no se alimentan pero ovipositan sobre los envases; las larvas tejen telarañas densas contaminando el producto con excretas y mudas.",
            "damage_and_risks": "Merma total de lotes de producto terminado, calentamiento y desarrollo de hongos productores de micotoxinas (*Aspergillus flavus* - Aflatoxinas cancerígenas), rechazo de clientes y clausura sanitaria.",
            "critical_points": "Silos, tolvas de descarga, bodegas de materias primas secas, derrames de harina bajo racks de almacenamiento.",
            "exclusion_measures": "Revisión rigurosa de proveedores y materias primas entrantes; sistema estricto de rotación PEPS; almacenamiento hermético en silos limpios.",
            "mechanical_control": "Monitoreo permanente con trampas de feromonas específicas de agregación y sexuales (trampas delta con feromona para *Plodia* y *Ephestia*).",
            "chemical_protocol": [
                "1. Vaciado y limpieza profunda de silos y bodegas eliminando todo residuo harinoso.",
                "2. Tratamiento de superficies vacías con insecticida de bajo residuo autorizado para industria de alimentos (Piretrinas Naturales + PBO).",
                "3. En granos a granel: tratamiento con protector de grano autorizado (Pirimifos metil o Deltametrina formulación especial)."
            ],
            "recommended_chemicals": [
                "Pybuthrin 33 (Piretrinas Naturales 3% + PBO 30% - RSCO-URB-INAC-102-315-009-3.0)",
                "Biothrine Flow (Deltametrina 2.5% - RSCO-URB-INAC-111-315-009-2.5)"
            ],
            "irac_rotation": "Piretrinas naturales y organofosforados de rápida degradación.",
            "reentry_time": "2 a 4 horas. Respetar límites máximos de residuos (LMR) en alimentos."
        },
        {
            "id": "arana-violinista",
            "name": "Araña Violinista y Viuda Negra",
            "scientific_name": "Loxosceles reclusa / Latrodectus mactans",
            "category": "Arácnidos Ponzoñosos",
            "icon": "fa-spider",
            "danger_level": "Extremo (Veneno Necrótico / Neurotóxico)",
            "biology_and_habits": "*Loxosceles* (Violinista): 6 ojos en tres pares (díadas), marca en forma de violín en el cefalotórax, hábitos tímidos en clósets y detrás de cuadros. *Latrodectus* (Viuda Negra): abdomen globoso negro con mancha roja en forma de reloj de arena, teje telas irregulares desordenadas en lugares oscuros a nivel de suelo.",
            "damage_and_risks": "Loxoscelismo: necrosis cutánea severa con escara negra y riesgo de loxoscelismo visceral con insuficiencia renal aguda. Latrodectismo: dolor muscular abdominal severo ('abdomen en madera'), hipertensión, taquicardia y shock.",
            "critical_points": "Rincones oscuros de bodegas, detrás de cuadros, cajas de archivo muerto, interior de clósets no usados, registros de agua.",
            "exclusion_measures": "Aspirado semanal de rincones oscuros y parte trasera de muebles; uso obligatorio de guantes al mover cajas o leña; separación de camas a 20 cm de las paredes.",
            "mechanical_control": "Trampas de pegamento en zócalos oscuros.",
            "chemical_protocol": [
                "1. Aspersión dirigida y focalizada en grietas, rodapiés, esquinas altas y detrás de muebles con microencapsulados de alta persistencia.",
                "2. Aplicación de polvo humectable en cámaras de registro exterior."
            ],
            "recommended_chemicals": [
                "Demand 2.5 CS (Lambda Cyhalotrina 2.5% - RSCO-URB-INAC-173-356-064-2.5)",
                "Biothrine Flow (Deltametrina 2.5% - RSCO-URB-INAC-111-315-009-2.5)"
            ],
            "irac_rotation": "Piretroides de alta residualidad.",
            "reentry_time": "2 horas. En caso de mordedura acudir de inmediato a urgencias y solicitar faboterápico antiloxosceles o antilatrodectus."
        },
        {
            "id": "paloma-comun",
            "name": "Paloma Común / Aves Nocivas",
            "scientific_name": "Columba livia",
            "category": "Aves Urbanas",
            "icon": "fa-dove",
            "danger_level": "Alto (Daño a Salud y Edificaciones)",
            "biology_and_habits": "Ave comensal gregaria de 30 a 35 cm. Anida en cornisas, techos, marquesinas y sistemas de ventilación de edificios. Produce hasta 12 kg de heces ácidas por ave al año.",
            "damage_and_risks": "Sus deyecciones contienen ácido úrico que corroe cantera, concreto y metales. Transmisora de Histoplasmosis (hongo *Histoplasma capsulatum* que se multiplica en el guano acumulado e ingresa por vías respiratorias), Criptococosis, Psitacosis y albergan ácaros y chinches de las aves.",
            "critical_points": "Cornisas, marquesinas, letras de anuncios luminosos, aires acondicionados en azoteas, vigas de naves industriales.",
            "exclusion_measures": "PROHIBICIÓN NOM-256: Prohibido el envenenamiento o métodos letales crueles contra aves. Medidas permitidas exclusivamente de exclusión: Instalación de redes de polietileno UV de 50 mm, sistemas de púas de acero inoxidable en cornisas, alambres tensados (*Bird-Wire*) y sellado de oquedades en techos.",
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
