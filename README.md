# FUMIFLOSA - Sistema SaaS Multinivel de Gestión de Control de Plagas

Sistema SaaS de alto rendimiento diseñado para la gestión integral de control de plagas corporativo e institucional (ej. IMSS con 100+ unidades), cumpliendo estrictamente con la **NOM-256-SSA1-2012** y normativas de **COFEPRIS** y **STPS** en México.

---

## 🚀 Características Principales

- **Arquitectura Multinivel B2B:** Soporte jerárquico para Clientes Matriz y cientos de Sucursales/Unidades Operativas.
- **Cumplimiento Normativo NOM-256-SSA1-2012:**
  - Emisión de Certificados Oficiales con vigencia automática a 30 días.
  - Registro y dosificación por químico con número CICOPLAFEST.
  - Datos de Licencia Sanitaria empresarial y Cédula de Responsable Sanitario.
  - Formato PDF estructurado con avisos legales de emergencia **SINTOX (01-800-0092800)** y espacio para sellos institucionales.
- **Trazabilidad y Auditoría:**
  - Llaves primarias universales en UUIDv4.
  - Eliminación lógica (*Soft Delete*) en todas las entidades sensibles.
  - Transacciones atómicas de base de datos para enlazar Órdenes y Certificados.
- **Ingesta Masiva de Datos:** Script optimizado con `pandas` para migración de históricos desde CSV.
- **Portal B2B & Dashboards:**
  - Monitoreo en tiempo real de certificados próximos a vencer (7, 15 y 30 días).
  - Exportación consolidada en ZIP de todos los certificados de un cliente matriz.

---

## 🛠️ Stack Tecnológico

- **Backend:** Python 3.11+ / FastAPI
- **ORM & Migraciones:** SQLAlchemy 2.0 / Alembic
- **Base de Datos:** PostgreSQL
- **Generación de Reportes:** ReportLab (posicionamiento milimétrico)
- **Procesamiento de Datos:** Pandas
- **Despliegue e Infraestructura:** Render.com (`render.yaml`)

---

## 📦 Despliegue en Render.com

1. Haz un fork o conecta este repositorio (`https://github.com/OLTRECORP/FUMIFLOSA`) a tu cuenta de **Render.com**.
2. Selecciona **Blueprints** y vincula el archivo `render.yaml`.
3. Render aprovisionará automáticamente:
   - Base de Datos PostgreSQL (`fumiflosa-db`).
   - Web Service en FastAPI con migraciones automáticas (`alembic upgrade head`).
4. Accede a `/docs` para ver la documentación interactiva Swagger.
