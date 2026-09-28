import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "FUMIFLOSA - Sistema SaaS de Control de Plagas"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:postgres@localhost:5432/pest_control_prod"
    )
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Configuración de Correo Electrónico (SMTP)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "notificaciones@fumiflosa.mx")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "FUMIFLOSA Control de Plagas")
    SMTP_TLS: bool = os.getenv("SMTP_TLS", "True").lower() in ("true", "1", "yes")

    class Config:
        case_sensitive = True


settings = Settings()
