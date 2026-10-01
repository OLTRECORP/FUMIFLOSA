# FUMIFLOSA - Sistema SaaS Multinivel de Gestión de Control de Plagas

Sistema SaaS de alto rendimiento diseñado para la gestión integral de control de plagas corporativo e institucional (ej. IMSS con 100+ unidades, cadenas comerciales, hospitales e industrias), cumpliendo estrictamente con la **NOM-256-SSA1-2012** y normativas de **COFEPRIS** y **STPS** en México.

---

## 🚀 Características Principales

- **Arquitectura Multinivel B2B:**
  - Soporte jerárquico para Clientes Matriz y cientos de Sucursales/Unidades Operativas asociadas.
  - Clasificación de unidades por giro: Hospitalaria, Comercial, Industrial, Oficinas y Habitacional.

- **Generación Masiva Mensual B2B (Contratos Recurrentes):**
  - Módulo para emitir en un solo lote órdenes de servicio y certificados NOM-256 para todas las sucursales de un cliente matriz.
  - Modos de generación: clonación de la última configuración registrada por sucursal o aplicación de plantilla base.
  - Generación de folios consecutivos únicos sin colisiones.
  - Envío automatizado por correo electrónico a los encargados de cada unidad.

- **Duplicación y Renovación de Servicios en 1 Clic:**
  - Duplicación de órdenes de servicio individuales junto con su certificado NOM-256 y catálogo de químicos aplicados.
  - Cálculo automático de vigencia a 30 días naturales a partir de la nueva fecha de aplicación.

- **Cumplimiento Normativo NOM-256-SSA1-2012 / COFEPRIS:**
  - Emisión de Certificados Oficiales con vigencia legal calculada a 30 días.
  - Catálogo de químicos regulados con número **CICOPLAFEST**, dosis autorizada, tiempo de reentrada en horas y categoría toxicológica.
  - Registro de Licencia Sanitaria empresarial y Cédula Profesional del Responsable Sanitario.
  - Generación de PDF milimétrico con **ReportLab**, avisos de emergencia **SINTOX (01-800-0092800 / 800-009-2800)** y espacios oficiales para sellos y firmas.

- **Envío de Certificados por Correo Electrónico (SMTP / Sandbox):**
  - Envío automático de certificados oficiales en formato PDF adjunto con plantilla HTML corporativa y alertas normativas.
  - Soporte para SMTP seguro (STARTTLS/SSL) y modo simulación/sandbox para desarrollo.

- **Trazabilidad, Auditoría y Seguridad:**
  - Llaves primarias universales en `UUIDv4`.
  - Eliminación lógica (*Soft Delete*) en todas las entidades críticas (`is_deleted`, `deleted_at`).
  - Transacciones atómicas de base de datos (`commit` / `rollback`) para evitar inconsistencias.
  - Control de técnicos de campo con registro y constancias de capacitación **STPS DC-3**.

- **Portal B2B, Dashboards y Descarga Masiva ZIP:**
  - Semáforo y calendario de monitoreo de vigencias sanitarias próximas a vencer (ventanas de 7, 15 y 30 días).
  - Descarga consolidada en memoria de todos los certificados PDF de un cliente matriz en un único archivo ZIP.
  - Ingesta masiva desde archivos CSV con normalización automática mediante Pandas.

---

## 🛠️ Stack Tecnológico

| Capa | Tecnologías |
| :--- | :--- |
| **Backend** | Python 3.11+ / FastAPI / Pydantic v2 / Pydantic-Settings |
| **ORM & Migraciones** | SQLAlchemy 2.0 / Alembic |
| **Base de Datos** | PostgreSQL / SQLite (soporte de pruebas) |
| **Generación de Reportes** | ReportLab 4.x / 5.x (Maquetación milimétrica NOM-256) |
| **Procesamiento de Datos** | Pandas 2.x / 3.x |
| **Frontend** | Single Page Application (SPA) responsiva con Tailwind CSS y FontAwesome |
| **Pruebas Automatizadas** | Pytest / FastAPI TestClient |
| **Infraestructura** | Render.com (`render.yaml`) / Uvicorn |

---

## 📂 Estructura del Proyecto

```text
fumiflosa/
├── alembic/                          # Migraciones de base de datos con Alembic
│   ├── versions/                     # Scripts de versión DDL
│   │   └── 0001_initial_schema.py
│   └── env.py
├── app/
│   ├── api/
│   │   └── routes.py                 # Endpoints RESTful de la API
│   ├── services/
│   │   ├── duplication_service.py    # Servicio de duplicación y lote mensual B2B
│   │   ├── email_service.py          # Servicio de correo con PDF adjunto
│   │   ├── pdf_service.py            # Generador ReportLab NOM-256
│   │   └── data_import.py            # Ingesta masiva con Pandas
│   ├── templates/
│   │   └── dashboard.html            # Panel de control web visual interactivo
│   ├── config.py                     # Configuración y variables de entorno
│   ├── database.py                   # Sesión SQLAlchemy y engine
│   ├── models.py                     # Modelos ORM relacionales
│   ├── schemas.py                    # Esquemas de validación Pydantic
│   └── main.py                       # Punto de entrada FastAPI
├── tests/
│   └── test_monthly_batch_and_duplication.py # Suite de pruebas automatizadas
├── alembic.ini                       # Configuración de Alembic
├── render.yaml                       # Definición de infraestructura para Render
├── requirements.txt                  # Dependencias de Python
└── sample_historical_import.csv      # Archivo CSV de ejemplo para migración
```

---

## ⚙️ Variables de Entorno

| Variable | Descripción | Valor por Defecto |
| :--- | :--- | :--- |
| `DATABASE_URL` | Cadena de conexión a PostgreSQL | `postgresql://postgres:postgres@localhost:5432/pest_control_prod` |
| `ENVIRONMENT` | Entorno de ejecución (`development` / `production`) | `development` |
| `SMTP_HOST` | Servidor SMTP para envío de correos | `smtp.gmail.com` |
| `SMTP_PORT` | Puerto SMTP (587 para TLS, 465 para SSL) | `587` |
| `SMTP_USER` | Usuario / Correo remitente SMTP | `""` *(modo sandbox si está vacío)* |
| `SMTP_PASSWORD` | Contraseña o token de aplicación SMTP | `""` |
| `SMTP_FROM_EMAIL` | Dirección de correo que aparecerá como remitente | `notificaciones@fumiflosa.mx` |
| `SMTP_FROM_NAME` | Nombre visible del remitente | `FUMIFLOSA Control de Plagas` |
| `SMTP_TLS` | Activar STARTTLS (`True` / `False`) | `True` |

---

## 🚀 Instalación y Ejecución Local

### 1. Clonar el repositorio
```bash
git clone https://github.com/marcoblunt/fumiflosa.git
cd fumiflosa
```

### 2. Crear y activar entorno virtual
```bash
python -m venv .venv
# En Windows:
.venv\Scripts\activate
# En Linux / macOS:
source .venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Ejecutar migraciones de base de datos
```bash
alembic upgrade head
```

### 5. Iniciar el servidor de desarrollo
```bash
uvicorn app.main:app --reload --port 8000
```

- **Panel de Control Web:** [http://localhost:8000/](http://localhost:8000/)
- **Documentación Swagger:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Documentación Redoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Ejecución de Pruebas

Para ejecutar la suite de pruebas unitarias e integrales:

```bash
pytest -v
```

---

## 📦 Despliegue en Render.com

1. Conecta este repositorio (`https://github.com/marcoblunt/fumiflosa`) a tu cuenta de **Render.com**.
2. Selecciona **Blueprints** y vincula el archivo `render.yaml`.
3. Render aprovisionará automáticamente:
   - Base de Datos PostgreSQL gestionada (`fumiflosa-db`).
   - Web Service en FastAPI con migraciones automáticas (`alembic upgrade head`).
4. Configura las variables opcionales de SMTP en el panel de Render para habilitar envíos de correo en producción.

---

## 📜 Licencia y Cumplimiento

Desarrollado para el cumplimiento estricto de la **NOM-256-SSA1-2012** (Secretaría de Salud / COFEPRIS) y normativas de capacitación técnica **STPS**. Todos los derechos reservados.
