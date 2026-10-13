"""Infraestructura de pruebas – Fase 14.

Ejecuta la API completa sobre SQLite (una BD temporal por sesión de
pytest) con los mismos shims que el runner temporal de desarrollo:

  · ``sa.BigInteger``  → ``Integer``        (SQLite no tiene bigint)
  · ``postgresql.JSONB`` → ``JSON``
  · ``postgresql.INET``  → ``String(45)``

Los shims se aplican ANTES de importar los modelos (los modelos hacen
``from sqlalchemy import BigInteger`` en el momento del import).
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path

# La BD debe apuntar a un archivo temporal ANTES de importar la
# configuración (pydantic-settings prioriza variables de entorno
# sobre el .env del proyecto).
_TMP_DIR = tempfile.mkdtemp(prefix="salesia_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DIR}/test.db"

# Shims SQLite aplicados antes de cualquier import de modelos.
import sqlalchemy as _sa  # noqa: E402
from sqlalchemy.dialects import postgresql as _pg  # noqa: E402

_sa.BigInteger = _sa.Integer
_pg.JSONB = _sa.JSON
_pg.INET = _sa.String(45)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    Category,
    Company,
    Customer,
    Dataset,
    DatasetVariable,
    Inventory,
    Observation,
    PaymentMethod,
    Product,
    Role,
    User,
)
from app.models.base import Base  # noqa: E402


NOW = datetime(2026, 10, 6, 12, 0, 0)

# Datos semilla compartidos por todos los tests.
COMPANY_1 = 1
COMPANY_2 = 2
CATEGORY_ID = 1
PRODUCT_CAFE = 1
PRODUCT_TE = 2
PRODUCT_AJENO = 3  # pertenece a la empresa 2
CUSTOMER_ID = 1
PAYMENT_EFECTIVO = 1


def _seed(db: Session) -> None:
    """Semilla mínima: 2 empresas, 5 roles, usuarios y datos base."""
    roles = {
        name: Role(id=index, name=name, description=None)
        for index, name in enumerate(
            ["Administrador", "Gerente", "Vendedor", "Analista", "Almacén"],
            start=1,
        )
    }
    for role in roles.values():
        db.add(role)

    db.add(
        Company(
            id=COMPANY_1,
            name="Comercial SalesIA S.A.C.",
            tax_id="20123456789",
            email=None,
            phone=None,
            address=None,
            is_active=True,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    db.add(
        Company(
            id=COMPANY_2,
            name="Otra Empresa S.A.C.",
            tax_id="20987654321",
            email=None,
            phone=None,
            address=None,
            is_active=True,
            created_at=NOW,
            updated_at=NOW,
        )
    )

    users = [
        ("admin@salesia.com", "Admin123*", "Administrador", COMPANY_1),
        ("gerente@salesia.com", "Gerente123*", "Gerente", COMPANY_1),
        ("vendedor@salesia.com", "Vendedor123*", "Vendedor", COMPANY_1),
        ("analista@salesia.com", "Analista123*", "Analista", COMPANY_1),
        ("almacen@salesia.com", "Almacen123*", "Almacén", COMPANY_1),
        ("admin2@otraempresa.com", "Admin123*", "Administrador", COMPANY_2),
    ]
    for index, (email, password, role_name, company_id) in enumerate(
        users, start=1
    ):
        db.add(
            User(
                id=index,
                company_id=company_id,
                role_id=roles[role_name].id,
                full_name=email.split("@")[0].title(),
                email=email,
                password_hash=hash_password(password),
                is_active=True,
                last_login_at=None,
                created_at=NOW,
                updated_at=NOW,
            )
        )

    db.add(
        Category(
            id=CATEGORY_ID,
            company_id=COMPANY_1,
            name="Bebidas",
            description=None,
            is_active=True,
            created_at=NOW,
        )
    )

    products = [
        (PRODUCT_CAFE, COMPANY_1, "CAF-001", "Café Premium", "25.50", 100),
        (PRODUCT_TE, COMPANY_1, "TE-002", "Té Verde", "15.00", 50),
        (PRODUCT_AJENO, COMPANY_2, "AJE-009", "Producto Ajeno", "99.00", 10),
    ]
    for pid, company_id, sku, name, price, stock in products:
        db.add(
            Product(
                id=pid,
                company_id=company_id,
                category_id=CATEGORY_ID if company_id == COMPANY_1 else None,
                sku=sku,
                name=name,
                description=None,
                unit_price=Decimal(price),
                cost_price=Decimal("0"),
                is_active=True,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        db.add(
            Inventory(
                id=pid,
                company_id=company_id,
                product_id=pid,
                quantity_on_hand=Decimal(str(stock)),
                minimum_quantity=Decimal("0"),
                updated_at=NOW,
            )
        )

    db.add(
        Customer(
            id=CUSTOMER_ID,
            company_id=COMPANY_1,
            document_type="DNI",
            document_number="12345678",
            full_name="Juan Pérez",
            email="juan@correo.com",
            phone=None,
            address=None,
            is_active=True,
            created_at=NOW,
            updated_at=NOW,
        )
    )

    db.add(
        PaymentMethod(
            id=PAYMENT_EFECTIVO,
            company_id=COMPANY_1,
            name="Efectivo",
            code="EFEC",
            is_active=True,
            created_at=NOW,
        )
    )

    db.commit()


def reset_database() -> None:
    """Recrea el esquema y vuelve a sembrar los datos base."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        _seed(db)
    finally:
        db.close()


import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _database():
    reset_database()
    yield
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def _clean_tables(_database):
    """Aísla cada test: recrea el esquema y la semilla base."""
    reset_database()
    yield


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, email: str, password: str) -> dict:
    """Devuelve las cabeceras Authorization para un usuario."""
    response = client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(scope="session")
def tokens(client):
    """Tokens de cada rol (la sesión de BD no cambia entre tests)."""
    return {
        "Administrador": login(client, "admin@salesia.com", "Admin123*"),
        "Gerente": login(client, "gerente@salesia.com", "Gerente123*"),
        "Vendedor": login(client, "vendedor@salesia.com", "Vendedor123*"),
        "Analista": login(client, "analista@salesia.com", "Analista123*"),
        "Almacén": login(client, "almacen@salesia.com", "Almacen123*"),
        "Administrador2": login(
            client, "admin2@otraempresa.com", "Admin123*"
        ),
    }


@pytest.fixture()
def admin_headers(tokens):
    return tokens["Administrador"]


@pytest.fixture()
def vendedor_headers(tokens):
    return tokens["Vendedor"]


@pytest.fixture()
def gerente_headers(tokens):
    return tokens["Gerente"]


@pytest.fixture()
def analista_headers(tokens):
    return tokens["Analista"]


@pytest.fixture()
def almacen_headers(tokens):
    return tokens["Almacén"]


@pytest.fixture()
def admin2_headers(tokens):
    return tokens["Administrador2"]


@pytest.fixture()
def db():
    """Sesión de SQLAlchemy directa (para aserciones a nivel de datos)."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
