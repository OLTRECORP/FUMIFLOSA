import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.models import Base, User, UserRole

# Configuración de base de datos SQLite en memoria para pruebas
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_master_login_official_credentials(client):
    """Prueba de login con credenciales oficiales maestras: FOSM630329EA5 / FLOSA6303."""
    res = client.post("/api/v1/auth/login", json={
        "username": "FOSM630329EA5",
        "password": "FLOSA6303"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["role"] == "SuperAdmin"


def test_master_login_email_credential(client):
    """Prueba de login con correo admin@fumiflosa.mx / FLOSA6303."""
    res = client.post("/api/v1/auth/login", json={
        "username": "admin@fumiflosa.mx",
        "password": "FLOSA6303"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["role"] == "SuperAdmin"


def test_master_login_rfc_typo_resilience(client):
    """Prueba de login con RFC FOMS630329EA5."""
    res = client.post("/api/v1/auth/login", json={
        "username": "FOMS630329EA5",
        "password": "FLOSA6303"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data


def test_master_login_aliases(client):
    """Prueba de login con alias comunes como admin, superadmin, flosa."""
    res1 = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin"
    })
    assert res1.status_code == 200

    res2 = client.post("/api/v1/auth/login", json={
        "username": "flosa",
        "password": "flosa6303"
    })
    assert res2.status_code == 200


def test_invalid_login(client):
    """Prueba de login con credenciales incorrectas."""
    res = client.post("/api/v1/auth/login", json={
        "username": "usuario_falso_que_no_existe",
        "password": "password_invalido_123"
    })
    assert res.status_code == 401
