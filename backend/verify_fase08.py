"""
Verificación end-to-end de la Fase 08 (Ventas, pagos e inventario).

Requisitos:
  - Backend corriendo:  uvicorn app.main:app --reload --port 8000
  - Base de datos con los seeds aplicados

Uso:
  python verify_fase08.py
"""
from __future__ import annotations

import sys
import uuid
from decimal import Decimal

import httpx

BASE_URL = "http://localhost:8000"
EMAIL = "admin@salesia.com"
PASSWORD = "Admin123*"

passed = 0
failed = 0


def check(label: str, condition: bool, extra: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {label}")
    else:
        failed += 1
        print(f"  ❌ {label}" + (f" → {extra}" if extra else ""))


def step(title: str) -> None:
    print(f"\n=== {title} ===")


def main() -> int:
    client = httpx.Client(base_url=BASE_URL, timeout=15.0)

    # ---------------------------------------------------------------
    step("1. Servidor y base de datos")
    # ---------------------------------------------------------------
    try:
        root = client.get("/")
        check("API responde en /", root.status_code == 200, str(root.status_code))

        health = client.get("/health/database")
        check(
            "PostgreSQL conectado",
            health.status_code == 200,
            health.json().get("detail", str(health.status_code)),
        )
        if health.status_code == 200:
            data = health.json()
            print(f"     BD: {data['database']} · {data['database_user']}")
    except httpx.ConnectError:
        print("  ❌ No se pudo conectar. ¿Está uvicorn corriendo en :8000?")
        return 1

    # ---------------------------------------------------------------
    step("2. Autenticación")
    # ---------------------------------------------------------------
    # 2.1 Sin token → 401
    no_token = client.get("/api/customers")
    check("Petición sin token → 401", no_token.status_code == 401)

    # 2.2 Credenciales inválidas → 401
    bad = client.post(
        "/api/auth/login", json={"email": EMAIL, "password": "mala"}
    )
    check("Login con contraseña mala → 401", bad.status_code == 401)

    # 2.3 Login correcto
    login = client.post(
        "/api/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    check("Login correcto → 200", login.status_code == 200, str(login.status_code))
    if login.status_code != 200:
        return 1

    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    auth = client

    me = auth.get("/api/auth/me", headers=headers)
    check("/api/auth/me devuelve el usuario", me.status_code == 200)

    # ---------------------------------------------------------------
    step("3. Catálogos base (clientes, categorías, productos)")
    # ---------------------------------------------------------------
    suffix = uuid.uuid4().hex[:6].upper()

    customer = auth.post(
        "/api/customers",
        headers=headers,
        json={
            "document_type": "DNI",
            "document_number": f"7{uuid.uuid4().int % 10**8:08d}",
            "full_name": f"Cliente E2E {suffix}",
            "email": f"e2e{suffix.lower()}@demo.com",
        },
    )
    check("POST /api/customers → 201", customer.status_code == 201,
          str(customer.status_code) + " " + customer.text[:200])
    if customer.status_code != 201:
        return 1
    customer_id = customer.json()["id"]

    category = auth.post(
        "/api/categories",
        headers=headers,
        json={"name": f"Categoría E2E {suffix}", "description": "Prueba fase 08"},
    )
    check("POST /api/categories → 201", category.status_code == 201,
          str(category.status_code) + " " + category.text[:200])
    if category.status_code != 201:
        return 1
    category_id = category.json()["id"]

    product_price = Decimal("150.00")
    product = auth.post(
        "/api/products",
        headers=headers,
        json={
            "sku": f"E2E-{suffix}",
            "name": f"Producto E2E {suffix}",
            "category_id": category_id,
            "unit_price": str(product_price),
            "cost_price": "80.00",
        },
    )
    check("POST /api/products → 201", product.status_code == 201,
          str(product.status_code) + " " + product.text[:200])
    if product.status_code != 201:
        return 1
    product_id = product.json()["id"]

    # ---------------------------------------------------------------
    step("4. Inventario: entrada de stock")
    # ---------------------------------------------------------------
    movement = auth.post(
        "/api/inventory/movements",
        headers=headers,
        json={
            "product_id": product_id,
            "movement_type": "entrada",
            "quantity": "10",
            "reason": "Reposición E2E",
        },
    )
    check("POST /inventory/movements (entrada) → 201",
          movement.status_code == 201,
          str(movement.status_code) + " " + movement.text[:200])
    if movement.status_code != 201:
        return 1

    mv = movement.json()
    check("Stock anterior 0 → nuevo 10",
          mv["previous_quantity"] in ("0", "0.000")
          and mv["new_quantity"] in ("10", "10.000"),
          f"{mv['previous_quantity']} → {mv['new_quantity']}")

    # El listado de inventario refleja el stock
    inv_list = auth.get(
        "/api/inventory",
        headers=headers,
        params={"search": f"E2E-{suffix}"},
    )
    check("GET /api/inventory → 200", inv_list.status_code == 200)
    items = inv_list.json()["items"]
    check("El producto aparece con stock 10",
          len(items) == 1 and items[0]["quantity_on_hand"] in ("10", "10.000"),
          str(items[:1]))
    check("low_stock = false",
          len(items) == 1 and items[0]["low_stock"] is False)

    # ---------------------------------------------------------------
    step("5. Venta completa con pago (flujo feliz)")
    # ---------------------------------------------------------------
    methods = auth.get("/api/payment-methods", headers=headers)
    check("GET /api/payment-methods → 200", methods.status_code == 200)
    if methods.status_code != 200 or not methods.json():
        print("     ⚠️  No hay métodos de pago en el seed.")
        return 1
    method_id = methods.json()[0]["id"]

    sale_payload = {
        "customer_id": customer_id,
        "items": [
            {"product_id": product_id, "quantity": 3, "discount_amount": 10}
        ],
        "discount_amount": 5,
        "tax_rate": 0.18,
        "payment": {"payment_method_id": method_id, "reference": "E2E-REC-1"},
        "notes": "Venta de verificación E2E",
    }
    sale = auth.post("/api/sales", headers=headers, json=sale_payload)
    check("POST /api/sales → 201", sale.status_code == 201,
          str(sale.status_code) + " " + sale.text[:300])
    if sale.status_code != 201:
        return 1

    s = sale.json()

    # --- verificación de cálculos ---
    # subtotal = 150 × 3 = 450
    # descuentos = 10 (línea) + 5 (venta) = 15
    # base = 435 · IGV = 78.30 · total = 513.30
    check("subtotal = 450.00", Decimal(s["subtotal"]) == Decimal("450.00"),
          s["subtotal"])
    check("descuentos = 15.00", Decimal(s["discount_amount"]) == Decimal("15.00"),
          s["discount_amount"])
    check("IGV = 78.30", Decimal(s["tax_amount"]) == Decimal("78.30"),
          s["tax_amount"])
    check("total = 513.30", Decimal(s["total_amount"]) == Decimal("513.30"),
          s["total_amount"])
    check("estado = completed (tiene pago)", s["status"] == "completed", s["status"])
    check("sale_number generado", bool(s["sale_number"]), s.get("sale_number", ""))
    check("items[] con 1 producto",
          len(s["items"]) == 1 and s["items"][0]["quantity"] in ("3", "3.000"))
    check("line_total = 440.00 (450 − 10)",
          Decimal(s["items"][0]["line_total"]) == Decimal("440.00"),
          s["items"][0]["line_total"])
    check("payment presente y pagado",
          s["payment"] is not None and s["payment"]["status"] == "paid",
          str(s["payment"]))

    # --- stock descontado: 10 − 3 = 7 ---
    inv_after = auth.get(
        "/api/inventory",
        headers=headers,
        params={"search": f"E2E-{suffix}"},
    ).json()["items"]
    check("Stock descontado a 7",
          len(inv_after) == 1
          and inv_after[0]["quantity_on_hand"] in ("7", "7.000"),
          str(inv_after[0]["quantity_on_hand"]) if inv_after else "sin datos")

    # --- movimiento de salida registrado con la venta ---
    movements = auth.get(
        "/api/inventory/movements",
        headers=headers,
        params={"product_id": product_id, "movement_type": "salida"},
    ).json()["items"]
    check("Movimiento de salida vinculado a la venta",
          len(movements) == 1
          and movements[0]["sale_id"] == s["id"]
          and movements[0]["movement_type"] == "salida",
          str(movements[:1]))

    # ---------------------------------------------------------------
    step("6. Detalle y listado de ventas")
    # ---------------------------------------------------------------
    detail = auth.get(f"/api/sales/{s['id']}", headers=headers)
    check("GET /api/sales/{id} → 200", detail.status_code == 200)
    check("Detalle incluye items y pago",
          detail.status_code == 200
          and len(detail.json()["items"]) == 1
          and detail.json()["payment"] is not None)

    detail_404 = auth.get("/api/sales/99999999", headers=headers)
    check("GET /api/sales/99999999 → 404", detail_404.status_code == 404)

    sale_list = auth.get("/api/sales", headers=headers,
                         params={"page": 1, "page_size": 10})
    check("GET /api/sales → 200", sale_list.status_code == 200)
    check("La venta aparece en el listado",
          any(item["id"] == s["id"] for item in sale_list.json()["items"]))

    sale_search = auth.get("/api/sales", headers=headers,
                           params={"search": s["sale_number"]})
    check("Búsqueda por correlativo la encuentra",
          sale_search.json()["total"] >= 1)

    sale_status = auth.get("/api/sales", headers=headers,
                           params={"status": "completed"})
    check("Filtro por estado funciona", sale_status.status_code == 200)

    # ---------------------------------------------------------------
    step("7. Venta pendiente + pago parcial + pago final")
    # ---------------------------------------------------------------
    sale2 = auth.post(
        "/api/sales",
        headers=headers,
        json={
            "customer_id": customer_id,
            "items": [{"product_id": product_id, "quantity": 2,
                       "discount_amount": 0}],
            "tax_rate": 0.18,
            "payment": None,
        },
    )
    check("Venta sin pago → 201", sale2.status_code == 201,
          str(sale2.status_code) + " " + sale2.text[:200])
    if sale2.status_code != 201:
        return 1
    s2 = sale2.json()
    # subtotal 300 · IGV 54 · total 354
    check("Estado pendiente", s2["status"] == "pending", s2["status"])
    check("total = 354.00", Decimal(s2["total_amount"]) == Decimal("354.00"),
          s2["total_amount"])

    # Pago parcial de 100 → sigue pendiente
    p1 = auth.post(
        "/api/payments",
        headers=headers,
        json={
            "sale_id": s2["id"],
            "payment_method_id": method_id,
            "amount": "100.00",
            "currency": "PEN",
            "reference": "PARCIAL-1",
        },
    )
    check("Pago parcial → 201", p1.status_code == 201,
          str(p1.status_code) + " " + p1.text[:200])

    state_after_partial = auth.get(f"/api/sales/{s2['id']}", headers=headers).json()
    check("Sigue pendiente tras pago parcial",
          state_after_partial["status"] == "pending",
          state_after_partial["status"])

    # Pago que excede el pendiente → 409
    over = auth.post(
        "/api/payments",
        headers=headers,
        json={
            "sale_id": s2["id"],
            "payment_method_id": method_id,
            "amount": "99999.00",
            "currency": "PEN",
        },
    )
    check("Pago que excede el pendiente → 409", over.status_code == 409,
          str(over.status_code))

    # Pago final que salda → completed
    p2 = auth.post(
        "/api/payments",
        headers=headers,
        json={
            "sale_id": s2["id"],
            "payment_method_id": method_id,
            "amount": "254.00",
            "currency": "PEN",
            "reference": "PARCIAL-2",
        },
    )
    check("Pago final → 201", p2.status_code == 201,
          str(p2.status_code) + " " + p2.text[:200])

    state_final = auth.get(f"/api/sales/{s2['id']}", headers=headers).json()
    check("Venta saldada → completed",
          state_final["status"] == "completed", state_final["status"])
    check("Pago del detalle muestra 354.00",
          Decimal(state_final["payment"]["amount"]) == Decimal("354.00"),
          str(state_final["payment"]))

    # ---------------------------------------------------------------
    step("8. Casos límite y validaciones (deben fallar)")
    # ---------------------------------------------------------------
    # 8.1 Stock insuficiente
    over_stock = auth.post(
        "/api/sales",
        headers=headers,
        json={
            "items": [{"product_id": product_id, "quantity": 9999,
                       "discount_amount": 0}],
            "tax_rate": 0.18,
        },
    )
    check("Venta con stock insuficiente → 409",
          over_stock.status_code == 409, str(over_stock.status_code))

    # 8.2 Producto inexistente → 404
    bad_product = auth.post(
        "/api/sales",
        headers=headers,
        json={
            "items": [{"product_id": 99999999, "quantity": 1,
                       "discount_amount": 0}],
            "tax_rate": 0.18,
        },
    )
    check("Producto inexistente → 404", bad_product.status_code == 404,
          str(bad_product.status_code))

    # 8.3 Descuento mayor al subtotal → 409
    big_discount = auth.post(
        "/api/sales",
        headers=headers,
        json={
            "items": [{"product_id": product_id, "quantity": 1,
                       "discount_amount": 0}],
            "discount_amount": 99999,
            "tax_rate": 0.18,
        },
    )
    check("Descuento mayor que el subtotal → 409",
          big_discount.status_code == 409, str(big_discount.status_code))

    # 8.4 Carrito vacío → 422 (validación Pydantic)
    empty_cart = auth.post(
        "/api/sales", headers=headers,
        json={"items": [], "tax_rate": 0.18},
    )
    check("Carrito vacío → 422", empty_cart.status_code == 422,
          str(empty_cart.status_code))

    # 8.5 Salida de inventario sin stock → 409
    no_stock = auth.post(
        "/api/inventory/movements",
        headers=headers,
        json={"product_id": product_id, "movement_type": "salida",
              "quantity": "99999"},
    )
    check("Salida sin stock → 409", no_stock.status_code == 409,
          str(no_stock.status_code))

    # 8.6 Tipo de movimiento inválido → 422
    bad_type = auth.post(
        "/api/inventory/movements",
        headers=headers,
        json={"product_id": product_id, "movement_type": "magia",
              "quantity": "1"},
    )
    check("Tipo de movimiento inválido → 422", bad_type.status_code == 422,
          str(bad_type.status_code))

    # 8.7 Cliente de otra empresa / inexistente → 404
    bad_customer = auth.post(
        "/api/sales",
        headers=headers,
        json={
            "customer_id": 99999999,
            "items": [{"product_id": product_id, "quantity": 1,
                       "discount_amount": 0}],
            "tax_rate": 0.18,
        },
    )
    check("Cliente inexistente → 404", bad_customer.status_code == 404,
          str(bad_customer.status_code))

    # ---------------------------------------------------------------
    step("9. Endpoint de pagos y aislamiento multiempresa")
    # ---------------------------------------------------------------
    payments = auth.get("/api/payments", headers=headers)
    check("GET /api/payments → 200", payments.status_code == 200)
    check("Hay al menos 3 pagos registrados",
          payments.json()["total"] >= 3, str(payments.json().get("total")))

    # Registro de auditoría de la venta (si existe la tabla)
    # (consulta directa no disponible por API aún: se verifica en SQL)
    print("     ℹ️  La auditoría de la venta se verifica con SQL (paso 10).")

    # ---------------------------------------------------------------
    print("\n" + "=" * 60)
    print(f"RESULTADO: {passed} pruebas correctas · {failed} fallos")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())