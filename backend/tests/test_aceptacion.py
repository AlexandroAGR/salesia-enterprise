"""Fase 14 – Pruebas de aceptación.

Flujo empresarial completo de extremo a extremo: el usuario recorre
todo el sistema por la API tal como lo haría en producción.
"""

from __future__ import annotations


def test_flujo_completo_venta_y_analisis(client, admin_headers, db):
    """Cliente → producto → inventario → venta → pago → analytics →
    dataset → análisis estadístico → insights → reporte → auditoría."""

    # 1) El administrador abre sesión y confirma su identidad.
    me = client.get("/api/auth/me", headers=admin_headers).json()
    assert me["role"] == "Administrador"

    # 2) Registra un cliente nuevo.
    customer = client.post(
        "/api/customers",
        headers=admin_headers,
        json={
            "full_name": "Empresa Andina S.A.",
            "document_type": "RUC",
            "document_number": "20555444333",
            "email": "compras@andina.pe",
        },
    ).json()
    assert customer["id"] > 0

    # 3) Registra un producto nuevo.
    product = client.post(
        "/api/products",
        headers=admin_headers,
        json={
            "sku": "FLUJO-1",
            "name": "Licencia Enterprise",
            "unit_price": "250.00",
            "category_id": 1,
        },
    ).json()

    # 4) Carga stock inicial mediante un movimiento de entrada.
    movement = client.post(
        "/api/inventory/movements",
        headers=admin_headers,
        json={
            "company_id": 1,
            "product_id": product["id"],
            "movement_type": "entrada",
            "quantity": "20",
            "reason": "Carga inicial",
        },
    )
    assert movement.status_code == 201

    # 5) Registra la venta con pago (queda 'completed').
    sale = client.post(
        "/api/sales",
        headers=admin_headers,
        json={
            "customer_id": customer["id"],
            "items": [{"product_id": product["id"], "quantity": 4}],
            "tax_rate": "0.18",
            "payment": {"payment_method_id": 1},
            "notes": "Pedido del trimestre",
        },
    ).json()
    assert sale["status"] == "completed"
    assert sale["customer_name"] == "Empresa Andina S.A."
    # 4 × 250.00 = 1000.00 ; 18% = 180.00 ; total = 1180.00
    assert sale["total_amount"] == "1180.00"

    # 6) El inventario refleja la salida y el stock restante.
    inventory = client.get(
        "/api/inventory", headers=admin_headers
    ).json()
    row = next(
        item
        for item in inventory["items"]
        if item["product_id"] == product["id"]
    )
    assert float(row["quantity_on_hand"]) == 16.0

    # 7) Analytics refleja la venta del periodo.
    summary = client.get(
        "/api/analytics/summary",
        headers=admin_headers,
        params={"date_from": "2026-01-01", "date_to": "2026-12-31"},
    ).json()
    assert summary["kpis"]["sales_count"] >= 1
    assert summary["kpis"]["revenue"] >= 1180.0

    # 8) El analista crea un dataset, una variable y observaciones.
    dataset = client.post(
        "/api/datasets",
        headers=admin_headers,
        json={
            "name": "Ventas Q4",
            "source_type": "ventas",
            "description": "Muestras para el motor estadístico",
        },
    ).json()

    variable = client.post(
        f"/api/datasets/{dataset['id']}/variables",
        headers=admin_headers,
        json={
            "name": "ticket",
            "data_type": "numeric",
            "variable_type": "continua",
        },
    ).json()

    observations = client.post(
        f"/api/datasets/{dataset['id']}/observations",
        headers=admin_headers,
        json={
            "items": [
                {"variable_id": variable["id"], "numeric_value": value}
                for value in (100.0, 120.0, 140.0, 900.0)
            ]
        },
    )
    assert observations.status_code == 201

    # 9) Ejecuta media/mediana: la media debe superar a la mediana
    #    por el valor atípico de 900 (media 315, mediana 130).
    analysis = client.post(
        "/api/analyses/mean-median",
        headers=admin_headers,
        json={"variable_id": variable["id"]},
    ).json()
    metrics = {
        item["metric_name"]: item["numeric_result"]
        for item in analysis["results"]
    }
    assert metrics["mean"] == 315.0
    assert metrics["median"] == 130.0
    comparison = next(
        item
        for item in analysis["results"]
        if item["metric_name"] == "comparison"
    )
    assert (
        comparison["result_payload"]["relation"]
        == "media_mayor_mediana"
    )

    # 10) Ejecuta una variable aleatoria (normal).
    rv = client.post(
        "/api/analyses/random-variable",
        headers=admin_headers,
        json={
            "variable_id": variable["id"],
            "distribution": "normal",
            "parameters": {"mu": 315.0, "sigma": 100.0},
        },
    ).json()
    rv_metrics = {
        item["metric_name"]: item["numeric_result"]
        for item in rv["results"]
    }
    assert rv_metrics["expected_value"] == 315.0
    assert rv_metrics["variance"] == 10000.0

    # 11) Ejecuta el teorema de Bayes.
    bayes = client.post(
        "/api/analyses/bayes",
        headers=admin_headers,
        json={
            "probability_a": 0.01,
            "probability_b_given_a": 0.9,
            "probability_b": 0.1,
        },
    ).json()
    assert bayes["bayes"]["posterior_probability"] == 0.09

    # 12) Genera insights y verifica que quedaron guardados.
    generated = client.post(
        "/api/insights/generate",
        headers=admin_headers,
        json={"period": "all"},
    ).json()
    assert isinstance(generated["created"], list)

    listed = client.get("/api/insights", headers=admin_headers).json()
    assert listed["total"] >= len(generated["created"])

    # 13) Genera un reporte estadístico con instantánea.
    report = client.post(
        "/api/reports/generate",
        headers=admin_headers,
        json={"report_type": "estadistico", "period": "all"},
    ).json()
    assert report["report_type"] == "estadistico"
    assert isinstance(report["content"], dict)

    stored = client.get(
        f"/api/reports/{report['id']}", headers=admin_headers
    ).json()
    assert stored["content"] == report["content"]

    # 14) La auditoría recoge todo el rastro de acciones críticas.
    audit = client.get("/api/audit", headers=admin_headers).json()
    actions = {row["action"] for row in audit["items"]}
    assert {
        "customer.create",
        "product.create",
        "inventory.movement",
        "sale.create",
    } <= actions


def test_flujo_multiempresa_aislamiento(client, admin_headers, db):
    """Los datos de una empresa no contaminan a la otra."""
    from tests.conftest import login

    # La empresa 1 crea cliente y venta.
    client.post(
        "/api/customers",
        headers=admin_headers,
        json={"full_name": "Cliente Empresa 1"},
    )
    client.post(
        "/api/sales",
        headers=admin_headers,
        json={"items": [{"product_id": 1, "quantity": 1}]},
    )

    headers2 = login(client, "admin2@otraempresa.com", "Admin123*")

    # La empresa 2 no ve ninguno de esos datos.
    customers2 = client.get(
        "/api/customers", headers=headers2
    ).json()
    assert all(
        item["full_name"] != "Cliente Empresa 1"
        for item in customers2["items"]
    )

    sales2 = client.get("/api/sales", headers=headers2).json()
    assert sales2["total"] == 0

    summary2 = client.get(
        "/api/analytics/summary", headers=headers2
    ).json()
    assert summary2["kpis"]["sales_count"] == 0


def test_flujo_sesion_y_permisos(client, admin_headers):
    """Cierre de sesión y denegación coherente tras el flujo."""
    from tests.conftest import login

    # El vendedor no puede acceder al módulo de auditoría.
    vendedor = login(client, "vendedor@salesia.com", "Vendedor123*")
    assert (
        client.get("/api/audit", headers=vendedor).status_code == 403
    )

    # Cierra sesión (queda registrado) y con un token antiguo sigue
    # siendo válido hasta expirar (JWT stateless).
    assert (
        client.post("/api/auth/logout", headers=vendedor).status_code
        == 204
    )
    assert (
        client.get("/api/customers", headers=vendedor).status_code
        == 200
    )
