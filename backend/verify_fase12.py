"""Verificación end-to-end de la Fase 12 (Reportes).

Comprueba los cinco tipos de reporte del plan (ventas, estadístico,
productos, clientes y vendedores), la instantánea histórica en `content`,
el catálogo, la exportación de datos para CSV, las validaciones y el
aislamiento multiempresa. Los números de cada reporte se contrastan con
los endpoints vivos de analítica y de ventas, que comparten las mismas
reglas de negocio.

Requisitos:
  - Backend corriendo en :8000 con seeds (runner SQLite o PostgreSQL).
  - Ejecutarlo el PRIMERO sobre una BD fresca; después se lanzan como
    regresión verify_fase11, verify_fase10, verify_fase09 y
    verify_fase08.

Uso:
  PYTHONPATH=$PWD .venv/bin/python verify_fase12.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

import httpx

BASE_URL = "http://localhost:8000"
EMAIL = "admin@salesia.com"
PASSWORD = "Admin123*"
OTHER_EMAIL = "gerente@otraempresa.com"
OTHER_PASSWORD = "Gerente123*"

REPORT_CODES = [
    "ventas",
    "estadistico",
    "productos",
    "clientes",
    "vendedores",
]
EXCLUDED_STATUSES = {"cancelled", "refunded"}

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


def close(a, b, tol: float = 0.02) -> bool:
    if a is None or b is None:
        return False
    return abs(float(a) - float(b)) <= tol


def get_json(
    client: httpx.Client, path: str, headers: dict, **params
) -> dict | list | None:
    clean = {k: v for k, v in params.items() if v is not None}
    response = client.get(path, headers=headers, params=clean or None)
    if response.status_code == 200:
        return response.json()
    return None


def login(client: httpx.Client, email: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def fetch_all_sales(client: httpx.Client, headers: dict) -> list[dict]:
    """Todas las ventas de la empresa (cualquier estado)."""
    out: list[dict] = []
    page = 1
    while True:
        data = get_json(
            client, "/api/sales", headers, page=page, page_size=100
        )
        if not isinstance(data, dict):
            return out
        out.extend(data["items"])
        if len(out) >= data["total"] or not data["items"]:
            return out
        page += 1


def reportable(sales: list[dict], date_from: str, date_to: str) -> list[dict]:
    """Ventas no canceladas/reembolsadas dentro de la ventana (misma
    regla de negocio que la analítica de la Fase 10)."""
    return [
        sale
        for sale in sales
        if sale["status"] not in EXCLUDED_STATUSES
        and date_from <= str(sale["sold_at"])[:10] <= date_to
    ]


def main() -> int:
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        headers = login(client, EMAIL, PASSWORD)
        other_headers = login(client, OTHER_EMAIL, OTHER_PASSWORD)

        today = datetime.now(timezone.utc).date()
        date_from = today - timedelta(days=6)
        date_to = today

        # ------------------------------------------------------------
        step("Autenticación")
        # ------------------------------------------------------------
        check(
            "GET /api/reports sin token → 401",
            client.get("/api/reports").status_code == 401,
        )
        check(
            "GET /api/reports/types sin token → 401",
            client.get("/api/reports/types").status_code == 401,
        )
        check(
            "POST /api/reports/generate sin token → 401",
            client.post(
                "/api/reports/generate", json={"report_type": "ventas"}
            ).status_code
            == 401,
        )

        # ------------------------------------------------------------
        step("Catálogo de tipos de reporte")
        # ------------------------------------------------------------
        types = get_json(client, "/api/reports/types", headers)
        check("GET /api/reports/types → lista con 5 tipos",
              isinstance(types, list) and len(types) == 5,
              extra=str(types)[:120])
        codes = [item["code"] for item in types or []]
        check("El catálogo respeta el orden del plan", codes == REPORT_CODES,
              extra=str(codes))
        check(
            "Nombres y descripciones no vacíos",
            isinstance(types, list)
            and all(
                item["name"].strip() and item["description"].strip()
                for item in types
            ),
        )

        # ------------------------------------------------------------
        step("Validaciones de la API")
        # ------------------------------------------------------------
        response = client.post(
            "/api/reports/generate",
            headers=headers,
            json={"report_type": "inexistente"},
        )
        check("generate con tipo desconocido → 400",
              response.status_code == 400,
              extra=f"{response.status_code}")
        response = client.post(
            "/api/reports/generate",
            headers=headers,
            json={"report_type": "ventas", "period": "45"},
        )
        check("generate con período inválido → 422",
              response.status_code == 422,
              extra=f"{response.status_code}")
        response = client.post(
            "/api/reports/generate",
            headers=headers,
            json={
                "report_type": "ventas",
                "date_from": "2026-10-12",
                "date_to": "2026-10-01",
            },
        )
        check("generate con rango de fechas invertido → 400",
              response.status_code == 400,
              extra=f"{response.status_code}")
        response = client.post(
            "/api/reports/generate",
            headers=headers,
            json={"report_type": "ventas", "title": "T" * 181},
        )
        check("generate con título > 180 caracteres → 422",
              response.status_code == 422,
              extra=f"{response.status_code}")
        response = client.get(
            "/api/reports", headers=headers, params={"report_type": "raro"}
        )
        check("listado filtrado por tipo desconocido → 400",
              response.status_code == 400,
              extra=f"{response.status_code}")
        response = client.get(
            "/api/reports", headers=headers, params={"page": 0}
        )
        check("listado con page=0 → 422",
              response.status_code == 422,
              extra=f"{response.status_code}")

        # ------------------------------------------------------------
        step("Reporte de ventas")
        # ------------------------------------------------------------
        ventas = client.post(
            "/api/reports/generate",
            headers=headers,
            json={"report_type": "ventas", "period": "7"},
        )
        check("POST /api/reports/generate (ventas, 7 días) → 201",
              ventas.status_code == 201,
              extra=f"{ventas.status_code}: {ventas.text[:160]}")
        ventas_data = ventas.json()
        content = ventas_data["content"]
        scope = content["scope"]
        check("El ámbito cubre los últimos 7 días (hoy-6 … hoy)",
              scope["date_from"] == date_from.isoformat()
              and scope["date_to"] == date_to.isoformat(),
              extra=str(scope))
        check("El título por defecto incluye el tipo y el rango",
              ventas_data["title"].startswith("Reporte de ventas")
              and date_from.isoformat() in ventas_data["title"]
              and date_to.isoformat() in ventas_data["title"],
              extra=ventas_data["title"])
        check("report_type y etiqueta correctos",
              ventas_data["report_type"] == "ventas"
              and ventas_data["report_type_label"] == "Reporte de ventas")

        summary = get_json(
            client,
            "/api/analytics/summary",
            headers,
            date_from=date_from.isoformat(),
            date_to=date_to.isoformat(),
        )
        check("summary del reporte == GET /api/analytics/summary",
              isinstance(summary, dict)
              and content["summary"] == summary["kpis"],
              extra=f"{content['summary']} != {summary}")

        rows = content["rows"]
        kpis = content["summary"]
        check("Las filas coinciden con el nº de ventas del resumen",
              len(rows) == kpis["sales_count"],
              extra=f"{len(rows)} != {kpis['sales_count']}")
        check("La suma de las filas cuadra con los ingresos",
              close(sum(row["total_amount"] for row in rows),
                    kpis["revenue"]),
              extra=f"{sum(row['total_amount'] for row in rows)} != "
                    f"{kpis['revenue']}")
        check("Ninguna fila está cancelada ni reembolsada",
              all(row["status"] not in EXCLUDED_STATUSES for row in rows))

        all_sales = fetch_all_sales(client, headers)
        expected = reportable(
            all_sales, date_from.isoformat(), date_to.isoformat()
        )
        by_number = {sale["sale_number"]: sale for sale in all_sales}
        matched = True
        mismatch = ""
        for row in rows:
            sale = by_number.get(row["sale_number"])
            if sale is None:
                matched = False
                mismatch = f"venta {row['sale_number']} no existe"
                break
            expected_customer = sale["customer_name"] or "Sin cliente"
            if (
                row["customer"] != expected_customer
                or not close(row["total_amount"], float(sale["total_amount"]))
                or row["status"] != sale["status"]
                or row["sold_at"][:19] != str(sale["sold_at"])[:19]
            ):
                matched = False
                mismatch = f"{row['sale_number']} no coincide con /api/sales"
                break
        check("Cada fila coincide con su venta en /api/sales",
              matched, extra=mismatch)
        check(
            "Las filas son exactamente las ventas no excluidas del periodo",
            {row["sale_number"] for row in rows}
            == {sale["sale_number"] for sale in expected},
        )
        sold_dates = [row["sold_at"] for row in rows]
        check("Las filas se ordenan por fecha descendente",
              sold_dates == sorted(sold_dates, reverse=True))

        # ------------------------------------------------------------
        step("Reporte estadístico")
        # ------------------------------------------------------------
        response = client.post(
            "/api/reports/generate",
            headers=headers,
            json={"report_type": "estadistico", "period": "7"},
        )
        check("generate (estadístico, 7 días) → 201",
              response.status_code == 201,
              extra=f"{response.status_code}: {response.text[:160]}")
        est = response.json()["content"]
        check("kpis del reporte == kpis de analítica",
              isinstance(summary, dict) and est["kpis"] == summary["kpis"])
        check("estadística del reporte == estadística de analítica",
              isinstance(summary, dict)
              and est["statistics"] == summary["statistics"])
        check("periodo anterior == periodo anterior de analítica",
              isinstance(summary, dict)
              and est["previous_period"] == summary["previous_period"])
        interpretation = est["interpretation"]
        check("Interpretación: lista de frases no vacías",
              isinstance(interpretation, list)
              and len(interpretation) >= 3
              and all(isinstance(line, str) and line.strip()
                      for line in interpretation),
              extra=str(interpretation)[:160])
        check("Interpretación: menciona la media frente a la mediana",
              any("La media" in line and "mediana" in line
                  for line in interpretation))
        check("Interpretación: menciona el coeficiente de variación",
              any("coeficiente de variación" in line
                  for line in interpretation))
        check("Interpretación: menciona el rango de tickets",
              any("tickets van de" in line for line in interpretation))
        check("Interpretación: compara con el periodo anterior",
              any("periodo anterior" in line for line in interpretation))
        check("statistics.count == kpis.sales_count",
              est["statistics"]["count"] == est["kpis"]["sales_count"])

        # ------------------------------------------------------------
        step("Reporte de productos")
        # ------------------------------------------------------------
        response = client.post(
            "/api/reports/generate",
            headers=headers,
            json={"report_type": "productos", "period": "7"},
        )
        check("generate (productos, 7 días) → 201",
              response.status_code == 201,
              extra=f"{response.status_code}: {response.text[:160]}")
        prod = response.json()["content"]
        breakdown = get_json(
            client,
            "/api/analytics/breakdown",
            headers,
            group_by="product",
            limit=25,
            date_from=date_from.isoformat(),
            date_to=date_to.isoformat(),
        )
        items = (breakdown or {}).get("items", []) if isinstance(
            breakdown, dict
        ) else []
        rows_ok = len(prod["rows"]) == len(items) and all(
            row["product"] == item["label"]
            and close(row["revenue"], item["revenue"])
            and row["sales_count"] == item["sales_count"]
            and close(row["quantity"], item["quantity"])
            for row, item in zip(prod["rows"], items)
        )
        check("Las filas coinciden con GET /analytics/breakdown?product",
              rows_ok,
              extra=f"{len(prod['rows'])} filas vs {len(items)} ítems")
        check("Los totales cuadran con la facturación del periodo",
              close(prod["totals"]["revenue"],
                    (summary or {}).get("kpis", {}).get("revenue"))
              and close(
                  sum(row["revenue"] for row in prod["rows"]),
                  prod["totals"]["revenue"],
              ),
              extra=str(prod["totals"]))
        shares = [row["share_pct"] for row in prod["rows"]]
        check("Participación: cada valor ≤ 100 y el conjunto suma ~100",
              all(share <= 100 for share in shares)
              and (not shares or close(sum(shares), 100, tol=0.5)
                   or prod["totals"]["revenue"] == 0),
              extra=str(shares))
        check("Las unidades coinciden con items_sold de analítica",
              isinstance(summary, dict)
              and close(prod["totals"]["units"],
                        summary["kpis"]["items_sold"]),
              extra=f"{prod['totals']['units']} != "
                    f"{summary['kpis']['items_sold'] if summary else '?'}")
        check("products_count == nº de filas",
              prod["totals"]["products_count"] == len(prod["rows"]))

        # ------------------------------------------------------------
        step("Reporte de clientes")
        # ------------------------------------------------------------
        response = client.post(
            "/api/reports/generate",
            headers=headers,
            json={"report_type": "clientes", "period": "7"},
        )
        check("generate (clientes, 7 días) → 201",
              response.status_code == 201,
              extra=f"{response.status_code}: {response.text[:160]}")
        cli = response.json()["content"]
        check("customers_count == clientes distintos de analítica",
              isinstance(summary, dict)
              and cli["totals"]["customers_count"]
              == summary["kpis"]["customers_count"])
        check("La suma de ventas por cliente == nº de ventas",
              sum(row["sales_count"] for row in cli["rows"])
              == kpis["sales_count"],
              extra=f"{sum(row['sales_count'] for row in cli['rows'])} != "
                    f"{kpis['sales_count']}")
        check("La suma de ingresos por cliente == ingresos del periodo",
              close(sum(row["revenue"] for row in cli["rows"]),
                    kpis["revenue"]),
              extra=f"{sum(row['revenue'] for row in cli['rows'])} != "
                    f"{kpis['revenue']}")

        # Agregado independiente a partir de /api/sales
        agg: dict = {}
        for sale in expected:
            name = sale["customer_name"] or "Sin cliente"
            group = agg.setdefault(
                name, {"count": 0, "revenue": 0.0, "last": ""}
            )
            group["count"] += 1
            group["revenue"] += float(sale["total_amount"])
            group["last"] = max(group["last"], str(sale["sold_at"])[:19])
        rows_match = len(cli["rows"]) == len(agg)
        for row in cli["rows"]:
            other = agg.get(row["customer"])
            if other is None or not close(
                row["revenue"], other["revenue"], tol=0.05
            ):
                rows_match = False
                break
            if row["sales_count"] != other["count"]:
                rows_match = False
                break
            if row["last_purchase"][:19] != other["last"]:
                rows_match = False
                break
        check("Las filas coinciden con el agregado de /api/sales",
              rows_match, extra=f"{cli['rows']} vs {agg}")
        check("Ticket medio == ingresos / ventas en cada fila",
              all(
                  close(row["avg_ticket"],
                        row["revenue"] / row["sales_count"], tol=0.02)
                  for row in cli["rows"]
                  if row["sales_count"]
              ))
        revenues = [row["revenue"] for row in cli["rows"]]
        check("Los clientes se ordenan por ingresos descendente",
              revenues == sorted(revenues, reverse=True))

        # ------------------------------------------------------------
        step("Reporte de vendedores")
        # ------------------------------------------------------------
        response = client.post(
            "/api/reports/generate",
            headers=headers,
            json={"report_type": "vendedores", "period": "7"},
        )
        check("generate (vendedores, 7 días) → 201",
              response.status_code == 201,
              extra=f"{response.status_code}: {response.text[:160]}")
        ven = response.json()["content"]
        breakdown = get_json(
            client,
            "/api/analytics/breakdown",
            headers,
            group_by="seller",
            limit=25,
            date_from=date_from.isoformat(),
            date_to=date_to.isoformat(),
        )
        items = (breakdown or {}).get("items", []) if isinstance(
            breakdown, dict
        ) else []
        rows_ok = len(ven["rows"]) == len(items) and all(
            row["seller"] == item["label"]
            and close(row["revenue"], item["revenue"])
            and row["sales_count"] == item["sales_count"]
            for row, item in zip(ven["rows"], items)
        )
        check("Las filas coinciden con GET /analytics/breakdown?seller",
              rows_ok,
              extra=f"{len(ven['rows'])} filas vs {len(items)} ítems")
        check("La suma de ingresos por vendedor == ingresos del periodo",
              close(sum(row["revenue"] for row in ven["rows"]),
                    kpis["revenue"]))
        check("Participación == ingresos / total por vendedor",
              all(
                  close(
                      row["share_pct"],
                      row["revenue"] / kpis["revenue"] * 100
                      if kpis["revenue"] else 0.0,
                      tol=0.01,
                  )
                  for row in ven["rows"]
              ),
              extra=str([(r["seller"], r["share_pct"])
                         for r in ven["rows"]]))
        check("Ticket medio == ingresos / ventas por vendedor",
              all(
                  close(row["avg_ticket"],
                        row["revenue"] / row["sales_count"], tol=0.02)
                  for row in ven["rows"]
                  if row["sales_count"]
              ))
        check("sellers_count == nº de filas",
              ven["totals"]["sellers_count"] == len(ven["rows"]))

        # ------------------------------------------------------------
        step("Detalle e instantánea histórica")
        # ------------------------------------------------------------
        report_id = ventas_data["id"]
        detail = get_json(client, f"/api/reports/{report_id}", headers)
        check("GET /api/reports/{id} devuelve la instantánea completa",
              isinstance(detail, dict)
              and detail.get("content") == ventas_data["content"],
              extra=str(detail)[:120])
        check("El reporte registra a su autor (id y nombre)",
              isinstance(detail, dict)
              and detail.get("created_by") is not None
              and bool(detail.get("created_by_name")))
        check("filters guarda el snapshot del periodo y las fechas",
              isinstance(detail, dict)
              and detail["filters"] == {
                  "period": "7",
                  "date_from": date_from.isoformat(),
                  "date_to": date_to.isoformat(),
                  "seller_id": None,
                  "category_id": None,
              },
              extra=str((detail or {}).get("filters")))

        categories = get_json(client, "/api/categories", headers)
        if isinstance(categories, dict):
            categories = categories.get("items", [])
        category_id = categories[0]["id"] if categories else None
        response = client.post(
            "/api/reports/generate",
            headers=headers,
            json={
                "report_type": "productos",
                "title": "Cierre mensual de gerencia",
                "period": "all",
                "category_id": category_id,
            },
        )
        check("generate con título propio → 201",
              response.status_code == 201,
              extra=f"{response.status_code}: {response.text[:160]}")
        custom = response.json()
        check("Se respeta el título personalizado",
              custom["title"] == "Cierre mensual de gerencia",
              extra=custom["title"])
        check("filters y scope conservan la categoría elegida",
              custom["filters"]["category_id"] == category_id
              and custom["content"]["scope"]["category_id"] == category_id,
              extra=str(custom["filters"]))

        # ------------------------------------------------------------
        step("Histórico y listado")
        # ------------------------------------------------------------
        listing = get_json(client, "/api/reports", headers, page_size=100)
        check("El listado acumula los reportes generados (≥ 6)",
              isinstance(listing, dict) and listing["total"] >= 6,
              extra=str(listing)[:120])
        check("El listado NO incluye el contenido (solo metadatos)",
              isinstance(listing, dict)
              and all("content" not in item for item in listing["items"]))
        ids = [item["id"] for item in (listing or {}).get("items", [])]
        check("Los reportes se ordenan del más reciente al más antiguo",
              ids == sorted(ids, reverse=True), extra=str(ids))

        filtered = get_json(
            client, "/api/reports", headers, report_type="estadistico"
        )
        check("Filtro por tipo devuelve sólo ese tipo",
              isinstance(filtered, dict)
              and len(filtered["items"]) > 0
              and all(item["report_type"] == "estadistico"
                      for item in filtered["items"]),
              extra=str(filtered)[:160])
        page2 = get_json(client, "/api/reports", headers, page_size=2)
        check("page_size=2 devuelve 2 items con el total intacto",
              isinstance(page2, dict)
              and len(page2["items"]) == 2
              and page2["total"] == listing["total"],
              extra=str(page2)[:160])
        beyond = get_json(
            client, "/api/reports", headers, page=999, page_size=2
        )
        check("Una página fuera de rango devuelve la lista vacía",
              isinstance(beyond, dict) and beyond["items"] == []
              and beyond["total"] == listing["total"])

        # ------------------------------------------------------------
        step("Aislamiento multiempresa")
        # ------------------------------------------------------------
        base = get_json(client, "/api/reports", other_headers)
        base_total = base["total"] if isinstance(base, dict) else -1
        check("La otra empresa empieza sin reportes ajenos",
              base_total >= 0, extra=str(base))
        response = client.get(
            f"/api/reports/{report_id}", headers=other_headers
        )
        check("GET del reporte ajeno → 404",
              response.status_code == 404, extra=f"{response.status_code}")

        response = client.post(
            "/api/reports/generate",
            headers=other_headers,
            json={"report_type": "ventas", "period": "all"},
        )
        check("La otra empresa genera su reporte de ventas → 201",
              response.status_code == 201,
              extra=f"{response.status_code}: {response.text[:160]}")
        empty = response.json()["content"]
        check("Su empresa sin ventas reporta ceros y sin filas",
              empty["summary"]["sales_count"] == 0
              and empty["summary"]["revenue"] == 0
              and empty["rows"] == [],
              extra=str(empty["summary"]))

        response = client.post(
            "/api/reports/generate",
            headers=other_headers,
            json={"report_type": "estadistico", "period": "all"},
        )
        check("Su reporte estadístico explica la ausencia de datos",
              response.status_code == 201
              and response.json()["content"]["interpretation"]
              == ["Sin ventas en el periodo: no hay datos que "
                  "interpretar."]
              and response.json()["content"]["statistics"]["count"] == 0,
              extra=response.text[:200])

        after = get_json(client, "/api/reports", other_headers)
        check("Sólo suman sus propios reportes (base + 2)",
              isinstance(after, dict)
              and after["total"] == base_total + 2,
              extra=f"{after} vs base {base_total}")
        admin_again = get_json(client, "/api/reports", headers, page_size=1)
        check("El histórico de la empresa principal no cambió",
              isinstance(admin_again, dict)
              and admin_again["total"] == listing["total"])

    print(f"\n{'=' * 50}")
    print(f"RESULTADO FASE 12: {passed} ✅ / {failed} ❌")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
