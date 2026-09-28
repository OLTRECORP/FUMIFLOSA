from fastapi import FastAPI
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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir Rutas Principales
app.include_router(api_router)


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT
    }


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Bienvenido a la API de FUMIFLOSA SaaS - Control de Plagas",
        "documentation": "/docs"
    }
