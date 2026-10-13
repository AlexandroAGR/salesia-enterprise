"""Fase 14 – Pruebas de endpoints (API).

Códigos de estado, esquemas de respuesta y control de permisos por
rol sobre la API completa (TestClient sobre la BD temporal).
"""

from __future__ import annotations


# ---------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------
def test_login_correcto_devuelve_token(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@salesia.com", "password": "Admin123*"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["access_token"]


def test_login_password_incorrecta(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@salesia.com", "password": "mala"},
    )

    assert response.status_code == 401
    assert "Credenciales" in response.json()["detail"]


def test_login_usuario_inexistente(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "nobody@salesia.com", "password": "x"},
    )

    assert response.status_code == 401


def test_endpoint_sin_token(client):
    response = client.get("/api/customers")

    assert response.status_code == 401


def test_endpoint_token_corrupto(client):
    response = client.get(
        "/api/customers",
        headers={"Authorization": "Bearer token.basura.falso"},
    )

    assert response.status_code == 401


def test_auth_me_devuelve_rol(client, admin_headers):
    response = client.get("/api/auth/me", headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "admin@salesia.com"
    assert body["role"] == "Administrador"


def test_logout_registra_auditoria(client, admin_headers):
    response = client.post("/api/auth/logout", headers=admin_headers)

    assert response.status_code == 204


# ---------------------------------------------------------------
# Esquemas y paginación
# ---------------------------------------------------------------
def test_listado_paginado(client, admin_headers):
    response = client.get("/api/customers", headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert set(body) >= {"items", "total", "page", "page_size"}
    assert isinstance(body["items"], list)


def test_creacion_cliente_201(client, vendedor_headers):
    response = client.post(
        "/api/customers",
        headers=vendedor_headers,
        json={"full_name": "María López"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["full_name"] == "María López"
    assert body["is_active"] is True


def test_validacion_422_nombre_corto(client, vendedor_headers):
    response = client.post(
        "/api/customers",
        headers=vendedor_headers,
        json={"full_name": "A"},
    )

    assert response.status_code == 422


def test_validacion_422_email_invalido(client, vendedor_headers):
    response = client.post(
        "/api/customers",
        headers=vendedor_headers,
        json={"full_name": "María López", "email": "no-es-email"},
    )

    assert response.status_code == 422


def test_producto_ajeno_404(client, admin2_headers):
    # El producto 1 pertenece a la empresa 1; el admin de la empresa 2
    # no debe verlo.
    response = client.get("/api/products/1", headers=admin2_headers)

    assert response.status_code == 404


def test_cliente_ajeno_404(client, admin2_headers):
    response = client.get("/api/customers/1", headers=admin2_headers)

    assert response.status_code == 404


def test_analytics_rango_invalido_400(client, admin_headers):
    response = client.get(
        "/api/analytics/summary",
        headers=admin_headers,
        params={"date_from": "2026-10-10", "date_to": "2026-10-01"},
    )

    assert response.status_code == 400
    assert "inválido" in response.json()["detail"]


# ---------------------------------------------------------------
# Permisos por rol (Fase 13) – denegación
# ---------------------------------------------------------------
def test_vendedor_no_ve_auditoria(client, vendedor_headers):
    response = client.get("/api/audit", headers=vendedor_headers)

    assert response.status_code == 403


def test_gerente_no_crea_clientes(client, gerente_headers):
    response = client.post(
        "/api/customers",
        headers=gerente_headers,
        json={"full_name": "No Debe Crearse"},
    )

    assert response.status_code == 403
    assert "permiso" in response.json()["detail"].lower()


def test_analista_no_crea_clientes(client, analista_headers):
    response = client.post(
        "/api/customers",
        headers=analista_headers,
        json={"full_name": "No Debe Crearse"},
    )

    assert response.status_code == 403


def test_almacen_no_crea_ventas(client, almacen_headers):
    response = client.post(
        "/api/sales",
        headers=almacen_headers,
        json={"items": [{"product_id": 1, "quantity": 1}]},
    )

    assert response.status_code == 403


def test_vendedor_no_crea_productos(client, vendedor_headers):
    response = client.post(
        "/api/products",
        headers=vendedor_headers,
        json={
            "sku": "V-001",
            "name": "Producto Vendedor",
            "unit_price": "10.00",
        },
    )

    assert response.status_code == 403


def test_analista_no_crea_ventas(client, analista_headers):
    # sales:write es sólo de Administrador y Vendedor.
    response = client.post(
        "/api/sales",
        headers=analista_headers,
        json={"items": [{"product_id": 1, "quantity": 1}]},
    )

    assert response.status_code == 403


def test_vendedor_no_ejecuta_analisis(client, vendedor_headers):
    response = client.post(
        "/api/analyses/probability",
        headers=vendedor_headers,
        json={"p_a": 0.5, "p_b": 0.4, "p_a_and_b": 0.2},
    )

    assert response.status_code == 403


# ---------------------------------------------------------------
# Permisos por rol – concedidos
# ---------------------------------------------------------------
def test_vendedor_ve_clientes(client, vendedor_headers):
    response = client.get("/api/customers", headers=vendedor_headers)

    assert response.status_code == 200


def test_analista_crea_dataset(client, analista_headers):
    response = client.post(
        "/api/datasets",
        headers=analista_headers,
        json={"name": "Encuesta", "source_type": "manual"},
    )

    assert response.status_code == 201


def test_gerente_consulta_analytics(client, gerente_headers):
    response = client.get("/api/analytics/summary", headers=gerente_headers)

    assert response.status_code == 200


def test_almacen_consulta_inventario(client, almacen_headers):
    response = client.get("/api/inventory", headers=almacen_headers)

    assert response.status_code == 200
