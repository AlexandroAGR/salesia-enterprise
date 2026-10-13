"""Fase 14 – Pruebas de cálculos y casos límite.

Totales de venta (subtotal, descuento, impuesto, redondeo monetario),
reglas de negocio con datos extremos y consistencia de analytics.
"""

from __future__ import annotations

from decimal import Decimal


def _sale(client, headers, **overrides):
    body = {
        "items": [{"product_id": 1, "quantity": 1}],
        "tax_rate": "0.18",
    }
    body.update(overrides)
    return client.post("/api/sales", headers=headers, json=body)


# ---------------------------------------------------------------
# Cálculo de totales
# ---------------------------------------------------------------
def test_total_con_impuesto(client, vendedor_headers):
    # 25.50 × 4 = 102.00 ; 18% = 18.36 ; total = 120.36
    response = _sale(
        client,
        vendedor_headers,
        items=[{"product_id": 1, "quantity": 4}],
    )

    body = response.json()
    assert body["subtotal"] == "102.00"
    assert body["tax_amount"] == "18.36"
    assert body["total_amount"] == "120.36"


def test_total_sin_impuesto(client, vendedor_headers):
    response = _sale(
        client,
        vendedor_headers,
        items=[{"product_id": 1, "quantity": 2}],
        tax_rate="0",
    )

    body = response.json()
    assert body["subtotal"] == "51.00"
    assert body["tax_amount"] == "0.00"
    assert body["total_amount"] == "51.00"


def test_descuento_por_linea(client, vendedor_headers):
    # 25.50 × 2 = 51.00 − 1.00 = 50.00 ; 18% = 9.00 ; total = 59.00
    response = _sale(
        client,
        vendedor_headers,
        items=[
            {
                "product_id": 1,
                "quantity": 2,
                "discount_amount": "1.00",
            }
        ],
    )

    body = response.json()
    assert body["subtotal"] == "51.00"
    assert body["discount_amount"] == "1.00"
    assert body["tax_amount"] == "9.00"
    assert body["total_amount"] == "59.00"


def test_descuento_global(client, vendedor_headers):
    # 25.50 − 5.50 = 20.00 ; 18% = 3.60 ; total = 23.60
    response = _sale(
        client, vendedor_headers, discount_amount="5.50"
    )

    body = response.json()
    assert body["discount_amount"] == "5.50"
    assert body["total_amount"] == "23.60"


def test_redondeo_monetario_half_up(client, vendedor_headers):
    # 25.50 × 7% = 1.785 → redondeo HALF_UP → 1.79 (no 1.78).
    response = _sale(
        client, vendedor_headers, tax_rate="0.07"
    )

    body = response.json()
    assert body["tax_amount"] == "1.79"
    assert body["total_amount"] == "27.29"


def test_items_multiples_suman(client, vendedor_headers):
    # Café 25.50 × 1 + Té 15.00 × 2 = 55.50 ; 18% = 9.99 ; total 65.49
    response = _sale(
        client,
        vendedor_headers,
        items=[
            {"product_id": 1, "quantity": 1},
            {"product_id": 2, "quantity": 2},
        ],
    )

    body = response.json()
    assert body["subtotal"] == "55.50"
    assert body["tax_amount"] == "9.99"
    assert body["total_amount"] == "65.49"
    assert len(body["items"]) == 2


# ---------------------------------------------------------------
# Casos límite de reglas de negocio
# ---------------------------------------------------------------
def test_cantidad_cero_422(client, vendedor_headers):
    response = _sale(
        client,
        vendedor_headers,
        items=[{"product_id": 1, "quantity": 0}],
    )

    assert response.status_code == 422


def test_cantidad_negativa_422(client, vendedor_headers):
    response = _sale(
        client,
        vendedor_headers,
        items=[{"product_id": 1, "quantity": -2}],
    )

    assert response.status_code == 422


def test_stock_insuficiente_409(client, vendedor_headers, db):
    # El producto 2 tiene 50 unidades.
    response = _sale(
        client,
        vendedor_headers,
        items=[{"product_id": 2, "quantity": 500}],
    )

    assert response.status_code == 409
    assert "Stock insuficiente" in response.json()["detail"]


def test_stock_insuficiente_no_descuenta(client, vendedor_headers, db):
    from app.models import Inventory

    _sale(
        client,
        vendedor_headers,
        items=[{"product_id": 2, "quantity": 500}],
    )

    db.expire_all()
    stock = (
        db.query(Inventory)
        .filter(Inventory.product_id == 2)
        .one()
        .quantity_on_hand
    )
    assert stock == Decimal("50")  # no se movió nada


def test_descuento_supera_importe_409(client, vendedor_headers):
    response = _sale(
        client,
        vendedor_headers,
        items=[
            {
                "product_id": 1,
                "quantity": 1,
                "discount_amount": "999.00",
            }
        ],
    )

    assert response.status_code == 409
    assert "descuento" in response.json()["detail"].lower()


def test_descuento_total_supera_subtotal_409(client, vendedor_headers):
    response = _sale(
        client, vendedor_headers, discount_amount="999.00"
    )

    assert response.status_code == 409


def test_producto_inactivo_409(client, vendedor_headers, db):
    from app.models import Product

    product = (
        db.query(Product).filter(Product.id == 2).one()
    )
    product.is_active = False
    db.commit()

    response = _sale(
        client,
        vendedor_headers,
        items=[{"product_id": 2, "quantity": 1}],
    )

    assert response.status_code == 409
    assert "inactivo" in response.json()["detail"]


def test_producto_no_existente_404(client, vendedor_headers):
    response = _sale(
        client,
        vendedor_headers,
        items=[{"product_id": 9999, "quantity": 1}],
    )

    assert response.status_code == 404


def test_producto_de_otra_empresa_404(client, vendedor_headers):
    # El producto 3 pertenece a la empresa 2.
    response = _sale(
        client,
        vendedor_headers,
        items=[{"product_id": 3, "quantity": 1}],
    )

    assert response.status_code == 404


def test_cliente_inactivo_409(client, vendedor_headers, db):
    from app.models import Customer

    customer = db.query(Customer).filter(Customer.id == 1).one()
    customer.is_active = False
    db.commit()

    response = _sale(client, vendedor_headers, customer_id=1)

    assert response.status_code == 409
    assert "inactivo" in response.json()["detail"]


def test_cliente_no_existente_404(client, vendedor_headers):
    response = _sale(client, vendedor_headers, customer_id=8888)

    assert response.status_code == 404


def test_metodo_pago_inexistente_404(client, vendedor_headers):
    response = _sale(
        client,
        vendedor_headers,
        payment={"payment_method_id": 777},
    )

    assert response.status_code == 404
    assert "no existe" in response.json()["detail"]


def test_metodo_pago_de_otra_empresa_404(client):
    # El método de pago 1 es de la empresa 1; el admin de la empresa 2
    # no puede usarlo aunque su producto sí sea válido.
    from tests.conftest import login

    headers = login(client, "admin2@otraempresa.com", "Admin123*")
    response = client.post(
        "/api/sales",
        headers=headers,
        json={
            "items": [{"product_id": 3, "quantity": 1}],
            "payment": {"payment_method_id": 1},
        },
    )

    assert response.status_code == 404
    assert "no existe" in response.json()["detail"]


# ---------------------------------------------------------------
# Consistencia de analytics
# ---------------------------------------------------------------
def test_summary_coincide_con_ventas(client, vendedor_headers):
    r1 = _sale(
        client, vendedor_headers, tax_rate="0"
    )  # 25.50
    r2 = _sale(
        client,
        vendedor_headers,
        items=[{"product_id": 2, "quantity": 2}],
        tax_rate="0",
    )  # 30.00

    esperado = (
        float(r1.json()["total_amount"])
        + float(r2.json()["total_amount"])
    )

    response = client.get(
        "/api/analytics/summary",
        headers=vendedor_headers,
        params={"date_from": "2026-01-01", "date_to": "2026-12-31"},
    )

    kpis = response.json()["kpis"]
    assert kpis["sales_count"] == 2
    assert float(kpis["revenue"]) == esperado
    assert float(kpis["avg_ticket"]) == round(esperado / 2, 2)


def test_summary_vacio_da_ceros(client, admin_headers):
    response = client.get(
        "/api/analytics/summary",
        headers=admin_headers,
        params={"date_from": "2019-01-01", "date_to": "2019-12-31"},
    )

    kpis = response.json()["kpis"]
    assert kpis["sales_count"] == 0
    assert float(kpis["revenue"]) == 0.0


def test_breakdown_agrupa_por_categoria(client, vendedor_headers):
    _sale(client, vendedor_headers, tax_rate="0")

    response = client.get(
        "/api/analytics/breakdown",
        headers=vendedor_headers,
        params={"group_by": "category"},
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert any(item["label"] == "Bebidas" for item in items)
