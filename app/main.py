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
    """Garantiza la creación y migración automática de columnas y tablas en PostgreSQL."""
    try:
        Base.metadata.create_all(bind=engine)
        with engine.begin() as conn:
            # Soporte para revisiones alembic largas
            conn.execute(text("ALTER TABLE IF EXISTS alembic_version ALTER COLUMN version_num TYPE VARCHAR(128);"))

            # Columnas para users
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(100);"))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username);"))
            
            # Columnas para clients (Portal Permanente)
            conn.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS portal_slug VARCHAR(100);"))
            conn.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS portal_password VARCHAR(255);"))
            conn.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS portal_is_enabled BOOLEAN DEFAULT TRUE;"))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_clients_portal_slug ON clients (portal_slug);"))
            
            # Columnas para chemicals
            conn.execute(text("ALTER TABLE chemicals ADD COLUMN IF NOT EXISTS toxicological_category VARCHAR(50);"))
            conn.execute(text("ALTER TABLE chemicals ADD COLUMN IF NOT EXISTS compatible_methods VARCHAR(255);"))
            
            # Columnas para certificates (Cancelación)
            conn.execute(text("ALTER TABLE certificates ADD COLUMN IF NOT EXISTS is_cancelled BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE certificates ADD COLUMN IF NOT EXISTS cancellation_reason VARCHAR(500);"))
            conn.execute(text("ALTER TABLE certificates ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;"))

            # Columnas para service_orders (Estado y Agendamiento)
            conn.execute(text("ALTER TABLE service_orders ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'completed';"))
            conn.execute(text("ALTER TABLE service_orders ADD COLUMN IF NOT EXISTS scheduled_for TIMESTAMPTZ;"))
        
        # Sincronizar catálogo inicial RSCO en línea
        from app.database import SessionLocal
        from app.services.mip_service import seed_default_rsco_items
        with SessionLocal() as db_session:
            seed_default_rsco_items(db_session)
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

# Rutas de los archivos HTML
TEMPLATES_DIR = Path(__file__).parent / "templates"
DASHBOARD_HTML_PATH = TEMPLATES_DIR / "dashboard.html"
CLIENT_PORTAL_HTML_PATH = TEMPLATES_DIR / "client_portal.html"


@app.get("/", response_class=HTMLResponse, tags=["Dashboard"])
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
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT
    }
