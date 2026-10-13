"""Fase 14 – Pruebas de datos.

Constraints de la base de datos, reglas de duplicados y manejo de
valores nulos en la API.
"""

from __future__ import annotations


# ---------------------------------------------------------------
# Valores nulos y opcionales
# ---------------------------------------------------------------
def test_cliente_solo_requiere_nombre(client, vendedor_headers):
    response = client.post(
        "/api/customers",
        headers=vendedor_headers,
        json={"full_name": "Cliente Mínimo"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["full_name"] == "Cliente Mínimo"
    assert body["document_number"] is None
    assert body["email"] is None
    assert body["phone"] is None
    assert body["address"] is None


def test_cliente_conoce_su_id(client, vendedor_headers):
    created = client.post(
        "/api/customers",
        headers=vendedor_headers,
        json={"full_name": "Con Identidad"},
    ).json()

    fetched = client.get(
        f"/api/customers/{created['id']}", headers=vendedor_headers
    )

    assert fetched.status_code == 200
    assert fetched.json()["id"] == created["id"]


def test_venta_sin_cliente_y_sin_notas(client, vendedor_headers):
    response = client.post(
        "/api/sales",
        headers=vendedor_headers,
        json={"items": [{"product_id": 1, "quantity": 1}]},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["customer_id"] is None
    assert body["customer_name"] is None
    assert body["notes"] is None


def test_producto_sin_categoria(client, almacen_headers):
    response = client.post(
        "/api/products",
        headers=almacen_headers,
        json={
            "sku": "SIN-CAT-1",
            "name": "Producto Sin Categoría",
            "unit_price": "9.90",
        },
    )

    assert response.status_code == 201
    assert response.json()["category_id"] is None


# ---------------------------------------------------------------
# Constraints de longitud y formato (422)
# ---------------------------------------------------------------
def test_cliente_nombre_demasiado_largo(client, vendedor_headers):
    response = client.post(
        "/api/customers",
        headers=vendedor_headers,
        json={"full_name": "X" * 200},
    )

    assert response.status_code == 422


def test_producto_sku_demasiado_largo(client, almacen_headers):
    response = client.post(
        "/api/products",
        headers=almacen_headers,
        json={
            "sku": "S" * 100,
            "name": "Producto Largo",
            "unit_price": "1.00",
        },
    )

    assert response.status_code == 422


def test_producto_precio_negativo(client, almacen_headers):
    response = client.post(
        "/api/products",
        headers=almacen_headers,
        json={
            "sku": "NEG-1",
            "name": "Producto Negativo",
            "unit_price": "-5.00",
        },
    )

    assert response.status_code == 422


def test_producto_precio_con_mas_decimales(client, almacen_headers):
    response = client.post(
        "/api/products",
        headers=almacen_headers,
        json={
            "sku": "DEC-1",
            "name": "Producto Decimal",
            "unit_price": "10.999",
        },
    )

    assert response.status_code == 422


# ---------------------------------------------------------------
# Duplicados
# ---------------------------------------------------------------
def test_variable_duplicada_409(client, analista_headers):
    dataset = client.post(
        "/api/datasets",
        headers=analista_headers,
        json={"name": "Duplicados", "source_type": "manual"},
    ).json()
    dataset_id = dataset["id"]

    first = client.post(
        f"/api/datasets/{dataset_id}/variables",
        headers=analista_headers,
        json={
            "name": "Ingresos",
            "data_type": "numeric",
            "variable_type": "continua",
        },
    )
    assert first.status_code == 201

    # El mismo nombre (ignorando mayúsculas) debe rechazarse.
    second = client.post(
        f"/api/datasets/{dataset_id}/variables",
        headers=analista_headers,
        json={
            "name": "INGRESOS",
            "data_type": "numeric",
            "variable_type": "continua",
        },
    )

    assert second.status_code == 409
    assert "Ya existe" in second.json()["detail"]


def test_variable_duplicada_en_otros_datasets_ok(
    client, analista_headers
):
    # El mismo nombre en datasets distintos sí está permitido.
    d1 = client.post(
        "/api/datasets",
        headers=analista_headers,
        json={"name": "Dataset Uno", "source_type": "manual"},
    ).json()
    d2 = client.post(
        "/api/datasets",
        headers=analista_headers,
        json={"name": "Dataset Dos", "source_type": "manual"},
    ).json()

    body = {
        "name": "Monto",
        "data_type": "numeric",
        "variable_type": "continua",
    }
    r1 = client.post(
        f"/api/datasets/{d1['id']}/variables",
        headers=analista_headers,
        json=body,
    )
    r2 = client.post(
        f"/api/datasets/{d2['id']}/variables",
        headers=analista_headers,
        json=body,
    )

    assert r1.status_code == 201
    assert r2.status_code == 201


def test_numero_de_venta_unico(client, vendedor_headers):
    r1 = client.post(
        "/api/sales",
        headers=vendedor_headers,
        json={"items": [{"product_id": 1, "quantity": 1}]},
    )
    r2 = client.post(
        "/api/sales",
        headers=vendedor_headers,
        json={"items": [{"product_id": 1, "quantity": 1}]},
    )

    assert r1.json()["sale_number"] != r2.json()["sale_number"]


# ---------------------------------------------------------------
# Coherencia de tipos de datos (dataset)
# ---------------------------------------------------------------
def test_variable_cualitativa_rechaza_valor_numerico(
    client, analista_headers
):
    dataset = client.post(
        "/api/datasets",
        headers=analista_headers,
        json={"name": "Coherencia", "source_type": "manual"},
    ).json()
    variable = client.post(
        f"/api/datasets/{dataset['id']}/variables",
        headers=analista_headers,
        json={
            "name": "zona",
            "data_type": "text",
            "variable_type": "cualitativa",
        },
    ).json()

    response = client.post(
        f"/api/datasets/{dataset['id']}/observations",
        headers=analista_headers,
        json={
            "items": [
                {
                    "variable_id": variable["id"],
                    "numeric_value": 42.0,
                }
            ]
        },
    )

    assert response.status_code == 400
    assert "text_value" in response.json()["detail"]


def test_variable_numerica_rechaza_valor_texto(
    client, analista_headers
):
    dataset = client.post(
        "/api/datasets",
        headers=analista_headers,
        json={"name": "Coherencia 2", "source_type": "manual"},
    ).json()
    variable = client.post(
        f"/api/datasets/{dataset['id']}/variables",
        headers=analista_headers,
        json={
            "name": "monto",
            "data_type": "numeric",
            "variable_type": "continua",
        },
    ).json()

    response = client.post(
        f"/api/datasets/{dataset['id']}/observations",
        headers=analista_headers,
        json={
            "items": [
                {"variable_id": variable["id"], "text_value": "algo"}
            ]
        },
    )

    assert response.status_code == 400
    assert "numeric_value" in response.json()["detail"]


def test_variable_numerica_rechaza_valor_no_finito(
    client, analista_headers
):
    dataset = client.post(
        "/api/datasets",
        headers=analista_headers,
        json={"name": "Finito", "source_type": "manual"},
    ).json()
    variable = client.post(
        f"/api/datasets/{dataset['id']}/variables",
        headers=analista_headers,
        json={
            "name": "monto",
            "data_type": "numeric",
            "variable_type": "continua",
        },
    ).json()

    # Cuerpo crudo: 1e400 llega como Infinity al parser del servidor
    # (json= de httpx no puede serializar inf desde Python).
    payload = (
        '{"items": [{"variable_id": %d, "numeric_value": 1e400}]}'
        % variable["id"]
    )
    response = client.post(
        f"/api/datasets/{dataset['id']}/observations",
        headers={
            **analista_headers,
            "Content-Type": "application/json",
        },
        content=payload,
    )

    assert response.status_code == 400


def test_clasificacion_incoherente_400(client, analista_headers):
    dataset = client.post(
        "/api/datasets",
        headers=analista_headers,
        json={"name": "Incoherente", "source_type": "manual"},
    ).json()

    response = client.post(
        f"/api/datasets/{dataset['id']}/variables",
        headers=analista_headers,
        json={
            "name": "letra",
            "data_type": "text",
            "variable_type": "continua",  # incoherente con text
        },
    )

    assert response.status_code == 400
    assert "numérico" in response.json()["detail"]


# ---------------------------------------------------------------
# Borrado lógico y referencias
# ---------------------------------------------------------------
def test_producto_desactivado_no_se_puede_vender(
    client, almacen_headers, vendedor_headers
):
    product = client.post(
        "/api/products",
        headers=almacen_headers,
        json={
            "sku": "BAJA-1",
            "name": "Producto Baja",
            "unit_price": "5.00",
        },
    ).json()

    deleted = client.delete(
        f"/api/products/{product['id']}", headers=almacen_headers
    )
    assert deleted.status_code in (200, 204)

    response = client.post(
        "/api/sales",
        headers=vendedor_headers,
        json={"items": [{"product_id": product["id"], "quantity": 1}]},
    )

    assert response.status_code == 409
    assert "inactivo" in response.json()["detail"]


def test_cliente_desactivado_no_aparece_por_defecto(
    client, vendedor_headers
):
    customer = client.post(
        "/api/customers",
        headers=vendedor_headers,
        json={"full_name": "Cliente Desactivable"},
    ).json()

    client.delete(
        f"/api/customers/{customer['id']}", headers=vendedor_headers
    )

    default_list = client.get(
        "/api/customers", headers=vendedor_headers
    ).json()
    ids = [item["id"] for item in default_list["items"]]
    assert customer["id"] not in ids

    with_inactive = client.get(
        "/api/customers",
        headers=vendedor_headers,
        params={"include_inactive": "true"},
    ).json()
    ids_all = [item["id"] for item in with_inactive["items"]]
    assert customer["id"] in ids_all


def test_producto_borrado_no_visible(client, almacen_headers):
    product = client.post(
        "/api/products",
        headers=almacen_headers,
        json={
            "sku": "BORRA-1",
            "name": "Producto Borrable",
            "unit_price": "5.00",
        },
    ).json()

    client.delete(
        f"/api/products/{product['id']}", headers=almacen_headers
    )

    fetched = client.get(
        f"/api/products/{product['id']}", headers=almacen_headers
    )

    # El endpoint individual sigue devolviéndolo marcado inactivo.
    assert fetched.status_code == 200
    assert fetched.json()["is_active"] is False
