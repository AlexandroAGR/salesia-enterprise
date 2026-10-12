"""Verificación end-to-end de la Fase 10 (Dashboard Analytics).

Comprueba KPIs, media/mediana, serie temporal con huecos a cero,
desgloses por producto/categoría/vendedor, distribución de frecuencias,
filtros (periodo, vendedor, categoría), validaciones y aislamiento
multiempresa.

Estrategia: los valores absolutos se verifican con un ámbito propio
(categorías con sufijo uuid creadas por el propio script) para que la
corrida sea independiente de los datos demo o de otras verificaciones;
los checks sin filtros son invariantes (suma de desgloses == ingreso,
ticket == ingresos/ventas, frecuencias == nº de ventas).

Requisitos:
  - Backend corriendo en :8000 con seeds (runner SQLite o PostgreSQL).

Uso:
  PYTHONPATH=$PWD .venv/bin/python verify_fase10.py
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone

import httpx

BASE_URL = "http://localhost:8000"
EMAIL = "admin@salesia.com"
PASSWORD = "Admin123*"
OTHER_EMAIL = "gerente@otraempresa.com"
OTHER_PASSWORD = "Gerente123*"

# Categorías demo del seed SQLite (para comprobar exclusión de estados
# con ventas históricas de estados variados).
TECH_DEMO = "Tecnología Demo"
OFFICE_DEMO = "Oficina Demo"

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


def close(a: float, b: float, tol: float = 1e-4) -> bool:
    return abs(a - b) <= tol


def get(client: httpx.Client, url: str, headers: dict, **params) -> httpx.Response:
    return client.get(url, headers=headers, params=params or None)


def main() -> int:
    client = httpx.Client(base_url=BASE_URL, timeout=15.0)
    today = datetime.now(timezone.utc).date()

    # ---------------------------------------------------------------
    step("1. Servidor y autenticación")
    # ---------------------------------------------------------------
    try:
        root = client.get("/")
        check("API responde en /", root.status_code == 200, str(root.status_code))
    except httpx.ConnectError:
        print("  ❌ No se pudo conectar. ¿Está uvicorn corriendo en :8000?")
        return 1

    no_token = client.get("/api/analytics/summary")
    check("Analytics sin token → 401", no_token.status_code == 401,
          str(no_token.status_code))

    login = client.post(
        "/api/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    check("Login admin → 200", login.status_code == 200, str(login.status_code))
    if login.status_code != 200:
        return 1
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    me = client.get("/api/auth/me", headers=headers)
    check("/api/auth/me → 200", me.status_code == 200)

    # ---------------------------------------------------------------
    step("2. Catálogo propio (ámbito uuid para esta corrida)")
    # ---------------------------------------------------------------
    suffix = uuid.uuid4().hex[:6].upper()

    category_a_resp = client.post(
        "/api/categories", headers=headers,
        json={"name": f"Analitica A {suffix}", "description": "Fase 10"},
    )
    check("POST /api/categories (A) → 201",
          category_a_resp.status_code == 201, category_a_resp.text[:200])
    if category_a_resp.status_code != 201:
        return 1
    cat_a = category_a_resp.json()["id"]

    category_b_resp = client.post(
        "/api/categories", headers=headers,
        json={"name": f"Analitica B {suffix}", "description": "Fase 10"},
    )
    check("POST /api/categories (B) → 201",
          category_b_resp.status_code == 201, category_b_resp.text[:200])
    cat_b = category_b_resp.json()["id"]

    product_a_resp = client.post(
        "/api/products", headers=headers,
        json={
            "sku": f"ANA-{suffix}-A",
            "name": f"Producto Analitica A {suffix}",
            "category_id": cat_a,
            "unit_price": "100.00",
            "cost_price": "50.00",
        },
    )
    check("POST /api/products (PA 100.00) → 201",
          product_a_resp.status_code == 201, product_a_resp.text[:200])
    if product_a_resp.status_code != 201:
        return 1
    product_a = product_a_resp.json()["id"]

    product_b_resp = client.post(
        "/api/products", headers=headers,
        json={
            "sku": f"ANA-{suffix}-B",
            "name": f"Producto Analitica B {suffix}",
            "category_id": cat_b,
            "unit_price": "50.00",
            "cost_price": "25.00",
        },
    )
    check("POST /api/products (PB 50.00) → 201",
          product_b_resp.status_code == 201, product_b_resp.text[:200])
    product_b = product_b_resp.json()["id"]

    for product_id in (product_a, product_b):
        movement = client.post(
            "/api/inventory/movements", headers=headers,
            json={
                "product_id": product_id,
                "movement_type": "entrada",
                "quantity": "10",
                "reason": "Stock fase 10",
            },
        )
        if movement.status_code != 201:
            check(f"Entrada de stock producto {product_id} → 201",
                  False, movement.text[:200])
            return 1
    check("Stock inicial registrado (10 + 10)", True)

    customer_resp = client.post(
        "/api/customers", headers=headers,
        json={
            "document_type": "DNI",
            "document_number": f"7{uuid.uuid4().int % 10**8:08d}",
            "full_name": f"Cliente Analitica {suffix}",
            "email": f"ana{suffix.lower()}@demo.com",
        },
    )
    check("POST /api/customers → 201",
          customer_resp.status_code == 201, customer_resp.text[:200])
    if customer_resp.status_code != 201:
        return 1
    customer_id = customer_resp.json()["id"]

    methods = client.get("/api/payment-methods", headers=headers)
    check("GET /api/payment-methods → 200 y con datos",
          methods.status_code == 200 and len(methods.json()) > 0)
    if methods.status_code != 200 or not methods.json():
        return 1
    method_id = methods.json()[0]["id"]

    # ---------------------------------------------------------------
    step("3. Ventas de prueba (totales exactos con IGV 18%)")
    # ---------------------------------------------------------------
    # A: 1×PA = 100 → total 118.00  (completada)
    # B: 2×PA + 1×PB = 250 → total 295.00  (completada)
    # C: 1×PB = 50 → total 59.00  (pendiente, sin pago)
    sale_a = client.post(
        "/api/sales", headers=headers,
        json={
            "customer_id": customer_id,
            "items": [{"product_id": product_a, "quantity": 1}],
            "tax_rate": 0.18,
            "payment": {"payment_method_id": method_id, "reference": "ANA-A"},
        },
    )
    check("Venta A → 201", sale_a.status_code == 201, sale_a.text[:300])
    check("Venta A total = 118.00 y completed",
          sale_a.status_code == 201
          and close(float(sale_a.json()["total_amount"]), 118.0)
          and sale_a.json()["status"] == "completed",
          sale_a.text[:200])

    sale_b = client.post(
        "/api/sales", headers=headers,
        json={
            "customer_id": customer_id,
            "items": [
                {"product_id": product_a, "quantity": 2},
                {"product_id": product_b, "quantity": 1},
            ],
            "tax_rate": 0.18,
            "payment": {"payment_method_id": method_id, "reference": "ANA-B"},
        },
    )
    check("Venta B → 201 total = 295.00",
          sale_b.status_code == 201
          and close(float(sale_b.json()["total_amount"]), 295.0),
          sale_b.text[:300])

    sale_c = client.post(
        "/api/sales", headers=headers,
        json={
            "customer_id": customer_id,
            "items": [{"product_id": product_b, "quantity": 1}],
            "tax_rate": 0.18,
        },
    )
    check("Venta C → 201 total = 59.00 y pending",
          sale_c.status_code == 201
          and close(float(sale_c.json()["total_amount"]), 59.0)
          and sale_c.json()["status"] == "pending",
          sale_c.text[:300])

    # ---------------------------------------------------------------
    step("4. Resumen / KPIs (ámbito categoría A, periodo = hoy)")
    # ---------------------------------------------------------------
    base = {"date_from": str(today), "date_to": str(today), "category_id": cat_a}
    summary = get(client, "/api/analytics/summary", headers, **base)
    check("GET /api/analytics/summary → 200", summary.status_code == 200,
          summary.text[:200])
    data = summary.json()
    kpis = data.get("kpis", {})
    stats = data.get("statistics", {})

    check("KPI ingresos = 413.00 (A + B)",
          close(float(kpis.get("revenue", -1)), 413.0), str(kpis))
    check("KPI nº de ventas = 2 (C fuera de la categoría A)",
          kpis.get("sales_count") == 2, str(kpis))
    check("KPI ticket promedio = 206.50",
          close(float(kpis.get("avg_ticket", -1)), 206.5), str(kpis))
    check("KPI clientes = 1 (mismo cliente en A y B)",
          kpis.get("customers_count") == 1, str(kpis))
    check("KPI unidades vendidas = 4 (1 + 2 + 1)",
          close(float(kpis.get("items_sold", -1)), 4.0), str(kpis))

    check("Media = 206.50", close(float(stats.get("mean", -1)), 206.5), str(stats))
    check("Mediana = 206.50",
          close(float(stats.get("median", -1)), 206.5), str(stats))
    check("Mín / Máx = 118 / 295",
          close(float(stats.get("min", -1)), 118.0)
          and close(float(stats.get("max", -1)), 295.0), str(stats))
    check("Desviación típica = 88.5",
          close(float(stats.get("stddev", -1)), 88.5), str(stats))

    previous = data.get("previous_period")
    check("Periodo anterior (ayer) sin ventas de esta categoría",
          previous is not None
          and close(float(previous.get("revenue", -1)), 0.0)
          and previous.get("sales_count") == 0
          and previous.get("revenue_change_pct") is None,
          str(previous))

    check("Eco de filtros en la respuesta",
          data.get("filters", {}).get("category_id") == cat_a
          and data.get("filters", {}).get("date_from") == str(today),
          str(data.get("filters")))

    # ---------------------------------------------------------------
    step("5. Resumen categoría B")
    # ---------------------------------------------------------------
    summary_b = get(
        client, "/api/analytics/summary", headers,
        date_from=str(today), date_to=str(today), category_id=cat_b,
    )
    data_b = summary_b.json()
    kpis_b = data_b.get("kpis", {})
    stats_b = data_b.get("statistics", {})
    check("Cat B: ingresos = 354.00 (B + C)",
          close(float(kpis_b.get("revenue", -1)), 354.0), str(kpis_b))
    check("Cat B: 2 ventas, ticket = 177.00",
          kpis_b.get("sales_count") == 2
          and close(float(kpis_b.get("avg_ticket", -1)), 177.0), str(kpis_b))
    check("Cat B: mediana = 177.00",
          close(float(stats_b.get("median", -1)), 177.0), str(stats_b))

    # ---------------------------------------------------------------
    step("6. Invariantes del resumen (sin filtros)")
    # ---------------------------------------------------------------
    full = client.get("/api/analytics/summary", headers=headers).json()
    full_kpis = full.get("kpis", {})
    full_stats = full.get("statistics", {})
    revenue = float(full_kpis.get("revenue", 0))
    count = int(full_kpis.get("sales_count", 0))

    check("Invariante: ticket = ingresos / nº de ventas",
          count > 0 and close(float(full_kpis.get("avg_ticket", -1)),
                              revenue / count, 0.01),
          f"{full_kpis}")
    check("Invariante: estadística.n == kpis.sales_count",
          full_stats.get("count") == count, str(full_stats))
    check("Invariante: min <= mediana <= max",
          count == 0
          or (float(full_stats.get("min", 0))
              <= float(full_stats.get("median", 0))
              <= float(full_stats.get("max", 0))),
          str(full_stats))

    # ---------------------------------------------------------------
    step("7. Serie temporal (día, semana, mes y huecos a cero)")
    # ---------------------------------------------------------------
    series_day = get(
        client, "/api/analytics/series", headers,
        granularity="day", **base,
    ).json()
    items = series_day.get("items", [])
    check("Serie día (hoy): 1 bucket con 413.00 y 2 ventas",
          series_day.get("granularity") == "day"
          and len(items) == 1
          and items[0]["bucket"] == str(today)
          and close(float(items[0]["revenue"]), 413.0)
          and items[0]["sales_count"] == 2,
          str(series_day))

    horizon = today + timedelta(days=2)
    series_fill = get(
        client, "/api/analytics/series", headers,
        granularity="day", date_from=str(today), date_to=str(horizon),
        category_id=cat_a,
    ).json()
    fill_items = series_fill.get("items", [])
    check("Serie 3 días: 3 buckets con huecos a cero",
          len(fill_items) == 3
          and close(float(fill_items[0]["revenue"]), 413.0)
          and close(float(fill_items[1]["revenue"]), 0.0)
          and close(float(fill_items[2]["revenue"]), 0.0)
          and fill_items[1]["sales_count"] == 0,
          str(fill_items))
    check("Suma de la serie = ingresos del periodo",
          close(sum(float(p["revenue"]) for p in fill_items), 413.0),
          str(fill_items))

    series_week = get(
        client, "/api/analytics/series", headers,
        granularity="week", date_from=str(today), date_to=str(today),
        category_id=cat_a,
    ).json()
    week_items = series_week.get("items", [])
    monday = today - timedelta(days=today.isoweekday() - 1)
    check("Serie semana: 1 bucket (lunes) con 413.00",
          len(week_items) == 1
          and week_items[0]["bucket"] == str(monday)
          and close(float(week_items[0]["revenue"]), 413.0),
          str(series_week))

    month_start = today.replace(day=1)
    series_month = get(
        client, "/api/analytics/series", headers,
        granularity="month", date_from=str(month_start), date_to=str(today),
        category_id=cat_a,
    ).json()
    month_items = series_month.get("items", [])
    month_key = f"{today.year:04d}-{today.month:02d}"
    check("Serie mes: 1 bucket del mes actual con 413.00",
          len(month_items) == 1
          and month_items[0]["bucket"] == month_key
          and close(float(month_items[0]["revenue"]), 413.0),
          str(series_month))

    tomorrow = today + timedelta(days=1)
    series_empty = get(
        client, "/api/analytics/series", headers,
        granularity="day", date_from=str(tomorrow), date_to=str(tomorrow),
        category_id=cat_a,
    ).json()
    empty_items = series_empty.get("items", [])
    check("Periodo futuro: 1 bucket en cero",
          len(empty_items) == 1
          and empty_items[0]["bucket"] == str(tomorrow)
          and close(float(empty_items[0]["revenue"]), 0.0)
          and empty_items[0]["sales_count"] == 0,
          str(series_empty))

    # ---------------------------------------------------------------
    step("8. Resumen de un periodo sin ventas")
    # ---------------------------------------------------------------
    summary_empty = get(
        client, "/api/analytics/summary", headers,
        date_from=str(tomorrow), date_to=str(tomorrow), category_id=cat_a,
    ).json()
    empty_kpis = summary_empty.get("kpis", {})
    empty_stats = summary_empty.get("statistics", {})
    check("Periodo vacío: ingresos 0, ticket 0, 0 ventas",
          close(float(empty_kpis.get("revenue", -1)), 0.0)
          and close(float(empty_kpis.get("avg_ticket", -1)), 0.0)
          and empty_kpis.get("sales_count") == 0,
          str(empty_kpis))
    check("Periodo vacío: estadística con count 0 y media nula",
          empty_stats.get("count") == 0 and empty_stats.get("mean") is None,
          str(empty_stats))

    # ---------------------------------------------------------------
    step("9. Desgloses: producto, categoría y vendedor")
    # ---------------------------------------------------------------
    by_product_a = get(
        client, "/api/analytics/breakdown", headers,
        group_by="product", **base,
    ).json()
    products = {item["label"]: item for item in by_product_a.get("items", [])}
    pa = products.get(f"Producto Analitica A {suffix}", {})
    pb = products.get(f"Producto Analitica B {suffix}", {})
    check("Producto A (cat A) = 354.00",
          close(float(pa.get("revenue", -1)), 354.0), str(pa))
    check("Producto B (cat A) = 59.00",
          close(float(pb.get("revenue", -1)), 59.0), str(pb))
    check("Suma de productos = ingresos (413.00)",
          close(sum(float(i["revenue"]) for i in by_product_a["items"]), 413.0),
          str(by_product_a))
    check("Producto A: 3 unidades en 2 ventas",
          close(float(pa.get("quantity", -1)), 3.0)
          and pa.get("sales_count") == 2, str(pa))

    by_product_b = get(
        client, "/api/analytics/breakdown", headers,
        group_by="product",
        date_from=str(today), date_to=str(today), category_id=cat_b,
    ).json()
    products_b = {item["label"]: item for item in by_product_b.get("items", [])}
    check("Cat B: producto A = 236.00 (reparto proporcional)",
          close(float(products_b.get(
              f"Producto Analitica A {suffix}", {}).get("revenue", -1)), 236.0),
          str(products_b))
    check("Cat B: producto B = 118.00 y suma == 354.00",
          close(float(products_b.get(
              f"Producto Analitica B {suffix}", {}).get("revenue", -1)), 118.0)
          and close(sum(float(i["revenue"]) for i in by_product_b["items"]),
                    354.0),
          str(products_b))

    by_seller_a = get(
        client, "/api/analytics/breakdown", headers,
        group_by="seller", **base,
    ).json()
    seller_items = by_seller_a.get("items", [])
    admin_id = me.json().get("id")
    check("Vendedor (cat A): única fila del admin con 413.00",
          len(seller_items) == 1
          and seller_items[0]["id"] == admin_id
          and seller_items[0]["label"] == "Admin SalesIA"
          and close(float(seller_items[0]["revenue"]), 413.0)
          and seller_items[0]["sales_count"] == 2,
          str(seller_items))

    by_category_full = get(
        client, "/api/analytics/breakdown", headers,
        group_by="category",
    ).json()
    check("Categorías (sin filtros): suma == ingresos totales",
          close(sum(float(i["revenue"]) for i in by_category_full["items"]),
                revenue, 0.05),
          f"{by_category_full['items']} vs {revenue}")

    by_seller_full = get(
        client, "/api/analytics/breakdown", headers,
        group_by="seller",
    ).json()
    check("Vendedores (sin filtros): suma == ingresos totales",
          close(sum(float(i["revenue"]) for i in by_seller_full["items"]),
                revenue, 0.05),
          str(by_seller_full["items"]))

    limited = get(
        client, "/api/analytics/breakdown", headers,
        group_by="product", limit=1,
    ).json()
    check("limit=1 devuelve 1 elemento", len(limited.get("items", [])) == 1,
          str(limited))

    # ---------------------------------------------------------------
    step("10. Distribución de frecuencias")
    # ---------------------------------------------------------------
    freq_a = get(client, "/api/analytics/frequencies", headers, **base).json()
    bins_a = freq_a.get("bins", [])
    check("Frecuencias (cat A): count = 2, mín 118, máx 295",
          freq_a.get("count") == 2
          and close(float(freq_a.get("min", -1)), 118.0)
          and close(float(freq_a.get("max", -1)), 295.0)
          and close(float(freq_a.get("mean", -1)), 206.5),
          str(freq_a))
    check("Sturges para n=2 → 2 intervalos con frecuencia 1 y 1",
          len(bins_a) == 2
          and bins_a[0]["frequency"] == 1
          and bins_a[1]["frequency"] == 1
          and close(float(bins_a[0]["relative"]), 0.5)
          and close(float(bins_a[1]["relative"]), 0.5),
          str(bins_a))
    check("Suma de frecuencias = nº de ventas",
          sum(b["frequency"] for b in bins_a) == freq_a.get("count"),
          str(bins_a))

    freq_empty = get(
        client, "/api/analytics/frequencies", headers,
        date_from=str(tomorrow), date_to=str(tomorrow), category_id=cat_a,
    ).json()
    check("Frecuencias de periodo vacío → count 0 y sin intervalos",
          freq_empty.get("count") == 0 and freq_empty.get("bins") == [],
          str(freq_empty))

    # ---------------------------------------------------------------
    step("11. Filtros: vendedor, categoría e histórico demo")
    # ---------------------------------------------------------------
    options = client.get("/api/analytics/filters", headers=headers).json()
    sellers = {item["name"]: item["id"] for item in options.get("sellers", [])}
    categories = {item["name"]: item["id"]
                  for item in options.get("categories", [])}
    check("Filtros: admin y vendedor entre los vendedores",
          "Admin SalesIA" in sellers and "Vendedor Demo" in sellers,
          str(sellers))
    check("Filtros: categorías demo presentes",
          TECH_DEMO in categories and OFFICE_DEMO in categories,
          str(categories))
    check("Filtros: categorías propias de esta corrida presentes",
          f"Analitica A {suffix}" in categories
          and f"Analitica B {suffix}" in categories,
          str(categories))
    if not categories:
        return 1

    window_start = today - timedelta(days=7)

    def scoped(**extra):
        params = {
            "date_from": str(window_start),
            "date_to": str(today),
            **extra,
        }
        return client.get(
            "/api/analytics/summary", headers=headers, params=params
        ).json()

    tech_id = categories[TECH_DEMO]
    office_id = categories[OFFICE_DEMO]
    admin_id = sellers["Admin SalesIA"]
    vendedor_id = sellers["Vendedor Demo"]

    tech = scoped(category_id=tech_id).get("kpis", {})
    check("Ventas de tecnología (7 días): 1 venta = 1060.82",
          tech.get("sales_count") == 1
          and close(float(tech.get("revenue", -1)), 1060.82),
          str(tech))
    check("La venta cancelada NO suma (habría sido 2 ventas)",
          tech.get("sales_count") != 2, str(tech))

    office = scoped(category_id=office_id).get("kpis", {})
    check("Ventas de oficina (7 días): 3 ventas = 1490.34",
          office.get("sales_count") == 3
          and close(float(office.get("revenue", -1)), 1490.34),
          str(office))
    check("La venta reembolsada NO suma (habría sido 4 ventas)",
          office.get("sales_count") != 4, str(office))

    office_admin = scoped(category_id=office_id, seller_id=admin_id).get(
        "kpis", {}
    )
    check("Oficina + admin: 2 ventas = 902.70",
          office_admin.get("sales_count") == 2
          and close(float(office_admin.get("revenue", -1)), 902.70),
          str(office_admin))

    office_seller = scoped(category_id=office_id, seller_id=vendedor_id).get(
        "kpis", {}
    )
    check("Oficina + vendedor: 1 venta = 587.64",
          office_seller.get("sales_count") == 1
          and close(float(office_seller.get("revenue", -1)), 587.64),
          str(office_seller))

    no_match = scoped(category_id=cat_a, seller_id=vendedor_id).get("kpis", {})
    check("Combinación sin resultados → todo en cero",
          no_match.get("sales_count") == 0
          and close(float(no_match.get("revenue", -1)), 0.0),
          str(no_match))

    # ---------------------------------------------------------------
    step("12. Validaciones de entrada")
    # ---------------------------------------------------------------
    bad_range = get(
        client, "/api/analytics/summary", headers,
        date_from=str(tomorrow), date_to=str(window_start),
    )
    check("date_from > date_to → 400", bad_range.status_code == 400,
          str(bad_range.status_code))

    bad_granularity = get(
        client, "/api/analytics/series", headers, granularity="hora"
    )
    check("granularity inválida → 422", bad_granularity.status_code == 422,
          str(bad_granularity.status_code))

    bad_group = get(
        client, "/api/analytics/breakdown", headers, group_by="inventado"
    )
    check("group_by inválido → 422", bad_group.status_code == 422,
          str(bad_group.status_code))

    bad_seller = get(
        client, "/api/analytics/summary", headers, seller_id=0
    )
    check("seller_id=0 → 422", bad_seller.status_code == 422,
          str(bad_seller.status_code))

    bad_limit = get(
        client, "/api/analytics/breakdown", headers, limit=0
    )
    check("limit=0 → 422", bad_limit.status_code == 422,
          str(bad_limit.status_code))

    # ---------------------------------------------------------------
    step("13. Aislamiento multiempresa")
    # ---------------------------------------------------------------
    other_login = client.post(
        "/api/auth/login",
        json={"email": OTHER_EMAIL, "password": OTHER_PASSWORD},
    )
    check("Login de la otra empresa → 200",
          other_login.status_code == 200, str(other_login.status_code))
    if other_login.status_code != 200:
        return 1
    other_headers = {
        "Authorization": f"Bearer {other_login.json()['access_token']}"
    }

    other_summary = client.get(
        "/api/analytics/summary", headers=other_headers
    ).json()
    other_kpis = other_summary.get("kpis", {})
    check("Otra empresa: ingresos 0 (no ve nuestras ventas)",
          other_kpis.get("sales_count") == 0
          and close(float(other_kpis.get("revenue", -1)), 0.0),
          str(other_kpis))

    other_scoped = client.get(
        "/api/analytics/summary", headers=other_headers,
        params={"category_id": cat_a},
    ).json()
    check("Otra empresa filtrando por nuestra categoría → 0",
          other_scoped.get("kpis", {}).get("sales_count") == 0,
          str(other_scoped.get("kpis")))

    other_breakdown = client.get(
        "/api/analytics/breakdown", headers=other_headers
    ).json()
    check("Otra empresa: desgloses vacíos",
          other_breakdown.get("items") == [], str(other_breakdown))

    other_freq = client.get(
        "/api/analytics/frequencies", headers=other_headers
    ).json()
    check("Otra empresa: frecuencias vacías",
          other_freq.get("count") == 0 and other_freq.get("bins") == [],
          str(other_freq))

    other_options = client.get(
        "/api/analytics/filters", headers=other_headers
    ).json()
    check("Otra empresa: filtros sin nuestras categorías/vendedores",
          other_options.get("sellers") == []
          and all(
              item["id"] not in (cat_a, cat_b)
              for item in other_options.get("categories", [])
          ),
          str(other_options))

    # ---------------------------------------------------------------
    print("\n" + "=" * 60)
    print(f"RESULTADO: {passed} correctas · {failed} incorrectas")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
