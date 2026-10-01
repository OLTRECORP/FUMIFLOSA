import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text
from app.config import settings
from app.database import engine
from app.models import Base
from app.api.routes import router as api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Sistema SaaS Multinivel de Gestión de Control de Plagas conforme a la NOM-256-SSA1-2012 / COFEPRIS / STPS",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.on_event("startup")
def startup_db_sync():
    """Garantiza la creación y migración automática de columnas y tablas en PostgreSQL / SQLite."""
    try:
        Base.metadata.create_all(bind=engine)
        if engine.dialect.name == "postgresql":
            with engine.begin() as conn:
                for stmt in [
                    "ALTER TABLE IF EXISTS alembic_version ALTER COLUMN version_num TYPE VARCHAR(128);",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(100);",
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username);",
                    "ALTER TABLE clients ADD COLUMN IF NOT EXISTS portal_slug VARCHAR(100);",
                    "ALTER TABLE clients ADD COLUMN IF NOT EXISTS portal_password VARCHAR(255);",
                    "ALTER TABLE clients ADD COLUMN IF NOT EXISTS portal_is_enabled BOOLEAN DEFAULT TRUE;",
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_clients_portal_slug ON clients (portal_slug);",
                    "ALTER TABLE chemicals ADD COLUMN IF NOT EXISTS toxicological_category VARCHAR(50);",
                    "ALTER TABLE chemicals ADD COLUMN IF NOT EXISTS compatible_methods VARCHAR(255);",
                    "ALTER TABLE chemicals ADD COLUMN IF NOT EXISTS technical_sheet_url VARCHAR(500);",
                    "ALTER TABLE chemicals ADD COLUMN IF NOT EXISTS safety_sheet_url VARCHAR(500);",
                    "ALTER TABLE rsco_items ADD COLUMN IF NOT EXISTS technical_sheet_url VARCHAR(500);",
                    "ALTER TABLE rsco_items ADD COLUMN IF NOT EXISTS safety_sheet_url VARCHAR(500);",
                    "ALTER TABLE certificates ADD COLUMN IF NOT EXISTS is_cancelled BOOLEAN DEFAULT FALSE;",
                    "ALTER TABLE certificates ADD COLUMN IF NOT EXISTS cancellation_reason VARCHAR(500);",
                    "ALTER TABLE certificates ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;",
                    "ALTER TABLE service_orders ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'completed';",
                    "ALTER TABLE service_orders ADD COLUMN IF NOT EXISTS scheduled_for TIMESTAMPTZ;"
                ]:
                    try:
                        conn.execute(text(stmt))
                    except Exception:
                        pass
        
        # Sincronizar catálogo inicial RSCO, Químicos, Usuarios, Clientes, Certificados y Bitácoras
        from app.database import SessionLocal
        from app.services.seed_service import seed_all_database_defaults
        with SessionLocal() as db_session:
            seed_results = seed_all_database_defaults(db_session)
            print(f"[STARTUP DB SEED COMPLETE]: {seed_results}")
    except Exception as e:
        print(f"[STARTUP DB SYNC WARNING]: {e}")

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir Rutas Principales de la API
app.include_router(api_router)

# Rutas de los archivos HTML y Assets
TEMPLATES_DIR = Path(__file__).parent / "templates"
ASSETS_DIR = Path(__file__).parent / "assets"
DASHBOARD_HTML_PATH = TEMPLATES_DIR / "dashboard.html"
CLIENT_PORTAL_HTML_PATH = TEMPLATES_DIR / "client_portal.html"

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

if ASSETS_DIR.exists():
    app.mount("/static-assets", StaticFiles(directory=str(ASSETS_DIR)), name="static_assets")


@app.get("/assets/logo.png", tags=["Assets"])
@app.get("/assets/logo_flosa.png", tags=["Assets"])
def get_logo_image():
    """Devuelve el logo oficial de FLOSA Control de Plagas."""
    logo_path = ASSETS_DIR / "certificates" / "logo_flosa.png"
    if not logo_path.exists():
        logo_path = ASSETS_DIR / "logo_flosa.png"
    if logo_path.exists():
        return FileResponse(str(logo_path), media_type="image/png")
    return HTMLResponse("", status_code=404)


@app.get("/", response_class=HTMLResponse, tags=["Dashboard"])
@app.head("/", tags=["Dashboard"])
@app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
def get_dashboard():
    """Sirve la interfaz web visual del Panel de Control de FUMIFLOSA."""
    if DASHBOARD_HTML_PATH.exists():
        with open(DASHBOARD_HTML_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>FUMIFLOSA SaaS - Panel no disponible</h1>"


@app.get("/portal/c/{portal_slug}", response_class=HTMLResponse, tags=["Client Portal"])
def get_client_portal_page(portal_slug: str):
    """Sirve el portal público/privado con enlace permanente para un cliente institucional."""
    if CLIENT_PORTAL_HTML_PATH.exists():
        with open(CLIENT_PORTAL_HTML_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Portal de Cliente no disponible</h1>"


@app.get("/health", tags=["Health"])
@app.head("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT
    }
