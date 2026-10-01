from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Ajustar compatibilidad de URL en caso de que Render use postgres:// en lugar de postgresql://
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

if "sqlite" in db_url:
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False}
    )
else:
    # Intentar conexión con PostgreSQL y auto-fallback a SQLite si la base de datos local no está disponible
    try:
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10
        )
        with engine.connect() as test_conn:
            pass
    except Exception as pg_err:
        print(f"[DATABASE ADAPTER]: PostgreSQL no disponible ({pg_err}). Activando SQLite de respaldo 'sqlite:///./fumiflosa.db'.")
        sqlite_url = "sqlite:///./fumiflosa.db"
        engine = create_engine(
            sqlite_url,
            connect_args={"check_same_thread": False}
        )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

