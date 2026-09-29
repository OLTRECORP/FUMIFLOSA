import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import router as api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Sistema SaaS Multinivel de Gestión de Control de Plagas conforme a la NOM-256-SSA1-2012 / COFEPRIS / STPS",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

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
