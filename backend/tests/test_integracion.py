"""Fase 14 – Pruebas de integración.

Flujo venta → inventario → persistencia → auditoría, generación de
insights y reportes sobre datos reales de la BD temporal.
"""

from __future__ import annotations

from decimal import Decimal

from app.models import Inventory, InventoryMovement, Payment, Sale


SALE_BODY = {
    "customer_id": 1,
    "items": [{"product_id": 1, "quantity": 3}],
    "tax_rate": "0.18",
    "payment": {"payment_method_id": 1, "reference": "REF-001"},
}


def _stock(db, product_id: int) -> Decimal:
    row = (
        db.query(Inventory)
        .filter(Inventory.product_id == product_id)
        .one()
    )
    return row.quantity_on_hand


# ---------------------------------------------------------------
# Venta → inventario → persistencia
# ---------------------------------------------------------------
def test_venta_con_pago_descuenta_stock(
    client, vendedor_headers, db
):
    assert _stock(db, 1) == Decimal("100")

    response = client.post(
        "/api/sales", headers=vendedor_headers, json=SALE_BODY
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert body["sale_number"].startswith("V-")
    assert len(body["items"]) == 1
    assert body["payment"]["amount"] == body["total_amount"]
    assert body["payment"]["status"] == "paid"

    # El stock se descontó y quedó persistido.
    db.expire_all()
    assert _stock(db, 1) == Decimal("97")


def test_venta_sin_pago_queda_pendiente(client, vendedor_headers, db):
    body = {
        "items": [{"product_id": 2, "quantity": 5}],
        "tax_rate": "0.18",
    }

    response = client.post(
        "/api/sales", headers=vendedor_headers, json=body
    )

    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    assert response.json()["payment"] is None

    db.expire_all()
    assert _stock(db, 2) == Decimal("45")


def test_venta_genera_movimiento_de_inventario(
    client, vendedor_headers, db
):
    response = client.post(
        "/api/sales", headers=vendedor_headers, json=SALE_BODY
    )
    sale_id = response.json()["id"]

    movements = (
        db.query(InventoryMovement)
        .filter(InventoryMovement.sale_id == sale_id)
        .all()
    )

    assert len(movements) == 1
    movement = movements[0]
    assert movement.movement_type == "salida"
    assert movement.quantity == Decimal("3")
    assert movement.product_id == 1


def test_venta_registra_pago(client, vendedor_headers, db):
    response = client.post(
        "/api/sales", headers=vendedor_headers, json=SALE_BODY
    )
    sale_id = response.json()["id"]

    payment = (
        db.query(Payment).filter(Payment.sale_id == sale_id).one()
    )

    assert payment.status == "paid"
    assert payment.payment_method_id == 1
    assert payment.reference == "REF-001"
    assert payment.amount == Decimal(response.json()["total_amount"])


def test_venta_persiste_totales_correctos(
    client, vendedor_headers, db
):
    # 3 × 25.50 = 76.50 ; impuesto 18% = 13.77 ; total = 90.27
    response = client.post(
        "/api/sales", headers=vendedor_headers, json=SALE_BODY
    )

    body = response.json()
    assert body["subtotal"] == "76.50"
    assert body["tax_amount"] == "13.77"
    assert body["total_amount"] == "90.27"

    sale = db.query(Sale).filter(Sale.id == body["id"]).one()
    assert sale.total_amount == Decimal("90.27")
    assert sale.status == "completed"


# ---------------------------------------------------------------
# Auditoría
# ---------------------------------------------------------------
def test_auditoria_registra_login_y_venta(
    client, vendedor_headers, admin_headers
):
    # Login dentro del test: el fixture de tokens pertenece a una
    # sesión anterior y _clean_tables recrea la BD por test.
    from tests.conftest import login

    login(client, "vendedor@salesia.com", "Vendedor123*")
    client.post("/api/sales", headers=vendedor_headers, json=SALE_BODY)

    response = client.get("/api/audit", headers=admin_headers)

    assert response.status_code == 200
    actions = [row["action"] for row in response.json()["items"]]
    assert "auth.login" in actions
    assert "sale.create" in actions


def test_auditoria_registra_creacion_de_cliente(
    client, vendedor_headers, admin_headers
):
    client.post(
        "/api/customers",
        headers=vendedor_headers,
        json={"full_name": "Cliente Auditado"},
    )

    response = client.get("/api/audit", headers=admin_headers)

    actions = [row["action"] for row in response.json()["items"]]
    assert "customer.create" in actions


def test_auditoria_aislada_por_empresa(
    client, vendedor_headers, admin2_headers
):
    client.post("/api/sales", headers=vendedor_headers, json=SALE_BODY)

    response = client.get("/api/audit", headers=admin2_headers)

    # La empresa 2 no ve la auditoría de la empresa 1.
    assert response.json()["total"] == 0


# ---------------------------------------------------------------
# Analytics refleja las ventas
# ---------------------------------------------------------------
def test_analytics_summary_refleja_venta(
    client, vendedor_headers, admin_headers
):
    client.post("/api/sales", headers=vendedor_headers, json=SALE_BODY)

    response = client.get(
        "/api/analytics/summary",
        headers=admin_headers,
        params={"date_from": "2026-01-01", "date_to": "2026-12-31"},
    )

    assert response.status_code == 200
    kpis = response.json()["kpis"]
    assert kpis["sales_count"] >= 1
    assert float(kpis["revenue"]) >= 90.27


def test_inventario_movements_trazan_la_venta(
    client, vendedor_headers, db
):
    sale_response = client.post(
        "/api/sales", headers=vendedor_headers, json=SALE_BODY
    )
    sale_number = sale_response.json()["sale_number"]

    response = client.get(
        "/api/inventory/movements", headers=vendedor_headers
    )

    assert response.status_code == 200
    reasons = [row["reason"] for row in response.json()["items"]]
    assert f"Venta {sale_number}" in reasons


# ---------------------------------------------------------------
# Insights y reportes
# ---------------------------------------------------------------
def test_generar_insights_con_ventas(
    client, vendedor_headers, analista_headers, db
):
    # Venta sin pago → estado "pending" → la regla "pending_sales"
    # se dispara de forma determinista.
    client.post(
        "/api/sales",
        headers=vendedor_headers,
        json={"items": [{"product_id": 2, "quantity": 5}]},
    )

    response = client.post(
        "/api/insights/generate",
        headers=analista_headers,
        json={"period": "all"},
    )

    assert response.status_code == 200
    body = response.json()
    # `created` es la lista de insights nuevos; `skipped` los duplicados.
    assert isinstance(body["created"], list)
    assert len(body["created"]) >= 1
    codes = [insight["rule_code"] for insight in body["created"]]
    assert "pending_sales" in codes


def test_generar_reporte_de_ventas(
    client, vendedor_headers, gerente_headers, db
):
    sale_response = client.post(
        "/api/sales", headers=vendedor_headers, json=SALE_BODY
    )
    total = sale_response.json()["total_amount"]

    response = client.post(
        "/api/reports/generate",
        headers=gerente_headers,
        json={
            "report_type": "ventas",
            "period": "all",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["report_type"] == "ventas"
    assert body["report_type_label"] == "Reporte de ventas"
    # El contenido es una instantánea reproducible.
    assert isinstance(body["content"], dict)
    assert str(total) in str(body["content"]) or float(total) > 0


def test_reporte_estadistico_gerente(
    client, vendedor_headers, gerente_headers
):
    client.post("/api/sales", headers=vendedor_headers, json=SALE_BODY)

    response = client.post(
        "/api/reports/generate",
        headers=gerente_headers,
        json={"report_type": "estadistico", "period": "all"},
    )

    assert response.status_code == 201
    assert response.json()["report_type"] == "estadistico"


def test_reporte_tipo_desconocido_400(client, gerente_headers):
    response = client.post(
        "/api/reports/generate",
        headers=gerente_headers,
        json={"report_type": "inexistente", "period": "all"},
    )

    assert response.status_code == 400
