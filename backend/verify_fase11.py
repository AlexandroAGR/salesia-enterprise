"""Verificación end-to-end de la Fase 11 (Insights empresariales).

Comprueba el catálogo de reglas, la generación determinista con
deduplicación por huella, la trazabilidad de cada insight hasta los
datos o análisis que lo originaron (criterio de aceptación: "los
insights muestran el resultado que los origina"), los filtros, la
paginación, las validaciones y el aislamiento multiempresa.

Requisitos:
  - Backend corriendo en :8000 con seeds (runner SQLite o PostgreSQL).
  - Ejecutar tras verify_fase12 (el primero de la cadena sobre una BD
    fresca); después se lanzan como regresión verify_fase10,
    verify_fase09 y verify_fase08.

Uso:
  PYTHONPATH=$PWD .venv/bin/python verify_fase11.py
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

SEVERITIES = {"info", "positive", "warning"}
SALES_RULES = {
    "revenue_trend",
    "category_concentration",
    "product_concentration",
    "top_seller",
    "ticket_skew",
    "high_dispersion",
    "pending_sales",
    "cancellation_rate",
}
ANALYSIS_RULES = {
    "mean_median_skew",
    "random_variable_expected",
    "probability_independence",
    "bayes_posterior",
}
ALL_RULES = SALES_RULES | ANALYSIS_RULES

# Reglas que disparan el seed demo con ventana de 7 días (alta
# dispersión no dispara: el coeficiente de variación es < 1).
FRESH_RULES = ALL_RULES - {"high_dispersion"}

GROUP_OF = {
    "category_concentration": "category",
    "product_concentration": "product",
    "top_seller": "seller",
}

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


def close(a, b, tol: float = 1e-4) -> bool:
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


def post_json(
    client: httpx.Client, path: str, headers: dict, payload: dict | None = None
) -> httpx.Response:
    if payload is None:
        return client.post(path, headers=headers)
    return client.post(path, headers=headers, json=payload)


def login(client: httpx.Client, email: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def fetch_all(client: httpx.Client, headers: dict, **params) -> list[dict]:
    out: list[dict] = []
    page = 1
    while True:
        data = get_json(
            client,
            "/api/insights",
            headers,
            page=page,
            page_size=100,
            **params,
        )
        if not isinstance(data, dict):
            return out
        out.extend(data["items"])
        if len(out) >= data["total"] or not data["items"]:
            return out
        page += 1


def evidence_scope(ev: dict) -> dict:
    return {
        key: ev.get(key)
        for key in ("date_from", "date_to", "seller_id", "category_id")
        if key in ev
    }


def check_analysis(
    client: httpx.Client, headers: dict, insight: dict
) -> tuple[bool, str]:
    """La evidencia de una regla de análisis = resultados del análisis."""
    analysis = get_json(
        client, f"/api/analyses/{insight['analysis_id']}", headers
    )
    if not isinstance(analysis, dict):
        return False, f"análisis {insight['analysis_id']} no encontrado"

    ev = insight["evidence"]
    params = analysis.get("parameters") or {}
    results = {
        row["metric_name"]: row for row in analysis.get("results") or []
    }

    def num(metric: str):
        row = results.get(metric)
        return row.get("numeric_result") if row else None

    if insight["analysis_type"] != analysis.get("analysis_type"):
        return False, "el tipo de análisis no coincide"
    if insight["dataset_id"] != analysis.get("dataset_id"):
        return False, (
            f"dataset {insight['dataset_id']} != "
            f"{analysis.get('dataset_id')}"
        )

    code = insight["rule_code"]
    if code == "mean_median_skew":
        payload = (results.get("comparison") or {}).get("result_payload") or {}
        ok = (
            ev.get("variable") == params.get("variable_name")
            and close(ev.get("count"), num("count"))
            and close(ev.get("mean"), num("mean"))
            and close(ev.get("median"), num("median"))
            and ev.get("relation") == payload.get("relation")
            and ev.get("relation") != "media_igual_mediana"
        )
    elif code == "random_variable_expected":
        ok = (
            ev.get("variable") == params.get("variable_name")
            and ev.get("distribution") == params.get("distribution")
            and close(ev.get("expected_value"), num("expected_value"))
            and close(ev.get("variance"), num("variance"))
            and close(ev.get("std_dev"), num("std_dev"))
            and (
                "empirical_mean" not in ev
                or close(ev.get("empirical_mean"), num("empirical_mean"))
            )
        )
    elif code == "probability_independence":
        payload = (results.get("independence") or {}).get(
            "result_payload"
        ) or {}
        independent = payload.get("independent")
        ok = (
            close(ev.get("p_a"), params.get("p_a"))
            and close(ev.get("p_b"), params.get("p_b"))
            and close(ev.get("p_a_given_b"), num("p_a_given_b"))
            and close(ev.get("p_b_given_a"), num("p_b_given_a"))
            and ev.get("independent") is independent
            and close(ev.get("difference"), num("independence"))
            and insight["severity"]
            == ("info" if independent else "warning")
        )
    elif code == "bayes_posterior":
        ok = (
            close(ev.get("probability_a"), params.get("probability_a"))
            and close(
                ev.get("probability_b_given_a"),
                params.get("probability_b_given_a"),
            )
            and close(ev.get("probability_b"), num("marginal_probability"))
            and close(
                ev.get("posterior_probability"), num("posterior_probability")
            )
        )
    else:
        ok = False

    return ok, f"evidencia={ev}"


def crosscheck(
    client: httpx.Client, headers: dict, insight: dict, catalog: list[dict]
) -> tuple[bool, str]:
    """Comprueba que el insight coincide con los datos actuales."""
    code = insight["rule_code"]
    ev = insight["evidence"]
    names = {rule["code"]: rule["name"] for rule in catalog}

    if code not in ALL_RULES:
        return False, f"regla fuera del catálogo: {code}"
    if insight["severity"] not in SEVERITIES:
        return False, f"severidad inválida: {insight['severity']}"
    if not insight["title"] or len(insight["title"]) > 180:
        return False, f"título inválido: {insight['title']!r}"
    if not insight["description"]:
        return False, "descripción vacía"
    if insight["rule_name"] != names.get(code):
        return False, f"nombre de regla: {insight['rule_name']}"
    if not isinstance(ev, dict) or not ev:
        return False, "evidencia vacía"

    if code in ANALYSIS_RULES:
        if insight["analysis_id"] is None:
            return False, "regla de análisis sin analysis_id"
        return check_analysis(client, headers, insight)

    # Reglas de ventas: nunca vinculadas a un análisis
    if insight["analysis_id"] is not None:
        return False, "regla de ventas con analysis_id"

    scope = evidence_scope(ev)
    summary = get_json(client, "/api/analytics/summary", headers, **scope)

    if code == "revenue_trend":
        if not isinstance(summary, dict):
            return False, "sin /analytics/summary"
        previous = summary.get("previous_period")
        ok = (
            close(ev.get("revenue"), summary["kpis"]["revenue"])
            and isinstance(previous, dict)
            and close(ev.get("previous_revenue"), previous.get("revenue"))
            and close(
                ev.get("change_pct"), previous.get("revenue_change_pct")
            )
            and ev.get("date_from") == summary["filters"]["date_from"]
            and ev.get("date_to") == summary["filters"]["date_to"]
        )
        return ok, f"evidencia={ev} kpis={summary['kpis']} prev={previous}"

    if code in GROUP_OF:
        if not isinstance(summary, dict):
            return False, "sin /analytics/summary"
        group_by = GROUP_OF[code]
        breakdown = get_json(
            client,
            "/api/analytics/breakdown",
            headers,
            group_by=group_by,
            limit=25,
            **scope,
        )
        if not isinstance(breakdown, dict):
            return False, "sin /analytics/breakdown"
        items = breakdown["items"]
        total = summary["kpis"]["revenue"]
        top = items[0] if items else None
        expected_share = (
            round(top["revenue"] / total * 100, 2) if top and total else None
        )
        ok = (
            top is not None
            and ev.get(group_by) == top["label"]
            and close(ev.get("revenue"), top["revenue"])
            and close(ev.get("total_revenue"), total)
            and close(ev.get("share_pct"), expected_share)
            and ev.get("groups_count") == len(items)
        )
        return ok, f"evidencia={ev} items={items[:1]} total={total}"

    if code in {"ticket_skew", "high_dispersion"}:
        if not isinstance(summary, dict):
            return False, "sin /analytics/summary"
        stats = summary["statistics"]
        if code == "ticket_skew":
            ratio = (
                round(stats["mean"] / stats["median"], 2)
                if stats.get("median")
                else None
            )
            ok = (
                ev.get("count") == stats["count"]
                and close(ev.get("mean"), stats.get("mean"))
                and close(ev.get("median"), stats.get("median"))
                and close(ev.get("ratio"), ratio)
            )
        else:
            cv = (
                round(stats["stddev"] / stats["mean"], 2)
                if stats.get("mean")
                else None
            )
            ok = (
                ev.get("count") == stats["count"]
                and close(ev.get("mean"), stats.get("mean"))
                and close(ev.get("stddev"), stats.get("stddev"))
                and close(ev.get("cv"), cv)
            )
        return ok, f"evidencia={ev} stats={stats}"

    if code == "pending_sales":
        total = None
        amount = 0.0
        page = 1
        while True:
            data = get_json(
                client,
                "/api/sales",
                headers,
                status="pending",
                page=page,
                page_size=100,
            )
            if not isinstance(data, dict):
                return False, "sin ventas pendientes"
            total = data["total"]
            amount += sum(
                float(row["total_amount"]) for row in data["items"]
            )
            if page * 100 >= total:
                break
            page += 1
        ok = (
            ev.get("count") == total
            and close(ev.get("total_amount"), round(amount, 2))
        )
        return ok, f"evidencia={ev} api(count={total}, total={amount})"

    if code == "cancellation_rate":
        all_total = get_json(
            client, "/api/sales", headers, page=1, page_size=1
        )
        cancelled = get_json(
            client, "/api/sales", headers, status="cancelled",
            page=1, page_size=1,
        )
        refunded = get_json(
            client, "/api/sales", headers, status="refunded",
            page=1, page_size=1,
        )
        if not all_total:
            return False, "sin ventas"
        n = all_total["total"]
        c = cancelled["total"] if cancelled else 0
        r = refunded["total"] if refunded else 0
        expected = round((c + r) / n * 100, 2) if n else None
        ok = (
            ev.get("total") == n
            and ev.get("cancelled") == c
            and ev.get("refunded") == r
            and close(ev.get("rate_pct"), expected)
        )
        return ok, f"evidencia={ev} api(total={n}, c={c}, r={r})"

    return False, f"sin validación para la regla {code}"


def broken_items(
    client: httpx.Client,
    headers: dict,
    items: list[dict],
    catalog: list[dict],
) -> list[str]:
    """Detalle de los insights que no coinciden con sus datos."""
    broken = []
    for item in items:
        ok, detail = crosscheck(client, headers, item, catalog)
        if not ok:
            broken.append(f"{item['rule_code']}: {detail[:160]}")
    return broken


def main() -> int:
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)
    today = datetime.now(timezone.utc).date()

    # ---------------------------------------------------------------
    step("1. Servidor y autenticación")
    # ---------------------------------------------------------------
    try:
        root = client.get("/")
        check("API responde en /", root.status_code == 200,
              str(root.status_code))
    except httpx.ConnectError:
        print("  ❌ No se pudo conectar. ¿Está uvicorn corriendo en :8000?")
        return 1

    health = client.get("/health/database")
    if health.status_code == 200:
        check("PostgreSQL conectado", True, health.text[:120])
    else:
        print("  ⚠️  PostgreSQL no disponible: comprobación de BD omitida")

    for path, method in (
        ("/api/insights", "GET"),
        ("/api/insights/rules", "GET"),
        ("/api/insights/generate", "POST"),
    ):
        response = client.request(method, path)
        check(
            f"{method} {path} sin token → 401",
            response.status_code == 401,
            str(response.status_code),
        )

    headers = login(client, EMAIL, PASSWORD)
    other_headers = login(client, OTHER_EMAIL, OTHER_PASSWORD)
    me = get_json(client, "/api/auth/me", headers)
    check(
        "Login admin y consulta /auth/me",
        isinstance(me, dict)
        and me.get("email") == EMAIL
        and me.get("is_active") is True,
        str(me),
    )

    # ---------------------------------------------------------------
    step("2. Catálogo de reglas")
    # ---------------------------------------------------------------
    catalog = get_json(client, "/api/insights/rules", headers)
    check(
        "GET /api/insights/rules → 12 reglas",
        isinstance(catalog, list) and len(catalog) == 12,
        str(len(catalog) if isinstance(catalog, list) else catalog),
    )
    codes = {rule["code"] for rule in catalog or []}
    check("Códigos de reglas correctos", codes == ALL_RULES,
          str(sorted(codes ^ ALL_RULES)))
    check(
        "Cada regla tiene nombre, descripción y fuente",
        all(
            rule.get("name")
            and rule.get("description")
            and rule.get("source") in {"ventas", "analisis"}
            for rule in catalog or []
        ),
    )
    check(
        "Las 8 reglas de ventas y las 4 de análisis están declaradas",
        sum(1 for r in catalog if r["source"] == "ventas") == 8
        and sum(1 for r in catalog if r["source"] == "analisis") == 4,
    )

    # ---------------------------------------------------------------
    step("3. Historial inicial y primera generación")
    # ---------------------------------------------------------------
    initial = get_json(
        client, "/api/insights", headers, page=1, page_size=100
    )
    check(
        "GET /api/insights → página estándar",
        isinstance(initial, dict)
        and set(initial) == {"items", "total", "page", "page_size"},
        str(initial and sorted(initial)),
    )
    total0 = initial["total"] if isinstance(initial, dict) else 1

    gen1 = post_json(client, "/api/insights/generate", headers)
    check("POST /generate (sin body) → 200", gen1.status_code == 200,
          gen1.text[:200])
    body1 = gen1.json()
    check(
        "Respuesta con created (lista) y skipped (entero)",
        isinstance(body1.get("created"), list)
        and isinstance(body1.get("skipped"), int),
        str(body1)[:200],
    )
    created1 = body1["created"]
    codes1 = [item["rule_code"] for item in created1]

    after1 = get_json(client, "/api/insights", headers, page=1, page_size=1)
    check(
        "El total crece exactamente por los insights creados",
        isinstance(after1, dict)
        and after1["total"] == total0 + len(created1),
        f"{total0} + {len(created1)} != {after1 and after1['total']}",
    )

    if total0 == 0:
        check(
            "BD fresca: la generación crea ≥ 5 insights",
            len(created1) >= 5,
            str(codes1),
        )
        check(
            "BD fresca: crean las 7 reglas de ventas del seed",
            FRESH_RULES & SALES_RULES <= set(codes1),
            str(sorted((FRESH_RULES & SALES_RULES) - set(codes1))),
        )
        check("BD fresca: nada que omitir (skipped = 0)",
              body1["skipped"] == 0, str(body1["skipped"]))
    else:
        print(f"  ℹ️  BD no vacía ({total0} insights): se omiten los "
              "conteos absolutos de la primera generación")

    malformed = [
        item
        for item in created1
        if item["rule_code"] not in ALL_RULES
        or item["severity"] not in SEVERITIES
        or not item["title"]
        or len(item["title"]) > 180
        or not item["description"]
        or not item["evidence"]
        or item["rule_name"] != next(
            (r["name"] for r in catalog if r["code"] == item["rule_code"]),
            None,
        )
    ]
    check(
        "Todos los insights nuevos tienen campos válidos",
        not malformed,
        str(malformed[:1]),
    )

    # ---------------------------------------------------------------
    step("4. Deduplicación por huella")
    # ---------------------------------------------------------------
    gen2 = post_json(client, "/api/insights/generate", headers)
    body2 = gen2.json()
    check(
        "Repetir la generación sin cambios → 0 creados",
        gen2.status_code == 200 and body2["created"] == [],
        f"created={len(body2.get('created', []))}",
    )
    check(
        "Todos los candidatos se contaron como omitidos",
        body2["skipped"] >= 5,
        str(body2["skipped"]),
    )

    # ---------------------------------------------------------------
    step("5. Traza: evidencia → datos actuales (ventas)")
    # ---------------------------------------------------------------
    # Los insights son instantáneas con fecha: cuando los datos cambian,
    # las instantáneas antiguas dejan de reflejar el estado actual (un
    # barrido posterior solo valida los insights creados después del
    # cambio). Por eso el barrido completo exige BD fresca; en una
    # re-ejecución solo se validan los insights nuevos de esta corrida.
    insights_a = fetch_all(client, headers)
    if total0 == 0:
        broken_a = broken_items(client, headers, insights_a, catalog)
        check(
            f"Barrido inicial: {len(insights_a)} insights coinciden "
            "con sus datos",
            not broken_a,
            " | ".join(broken_a[:3]),
        )
    elif created1:
        broken_a = broken_items(client, headers, created1, catalog)
        check(
            f"Barrido inicial: {len(created1)} insights nuevos "
            "coinciden con sus datos",
            not broken_a,
            " | ".join(broken_a[:3]),
        )
    else:
        print(
            "  ℹ️  Sin insights nuevos en esta corrida: "
            "barrido inicial omitido"
        )
    ids_before_sale = {item["id"] for item in insights_a}
    sales_seen = {
        item["rule_code"] for item in insights_a if item["rule_code"]
        in SALES_RULES
    }
    if total0 == 0:
        check(
            "Se generaron las 7 reglas de ventas del seed",
            FRESH_RULES & SALES_RULES <= sales_seen,
            str(sorted((FRESH_RULES & SALES_RULES) - sales_seen)),
        )

    # ---------------------------------------------------------------
    step("6. Nueva venta → los insights se actualizan")
    # ---------------------------------------------------------------
    suffix = uuid.uuid4().hex[:6].upper()
    category = client.post(
        "/api/categories",
        headers=headers,
        json={"name": f"Insights {suffix}", "description": "Fase 11"},
    )
    check("Crear categoría de ámbito", category.status_code == 201,
          category.text[:160])
    product = client.post(
        "/api/products",
        headers=headers,
        json={
            "sku": f"INS-{suffix}",
            "name": f"Producto Insights {suffix}",
            "category_id": category.json()["id"],
            "unit_price": "99.99",
            "cost_price": "40.00",
        },
    )
    check("Crear producto de ámbito", product.status_code == 201,
          product.text[:160])
    if category.status_code != 201 or product.status_code != 201:
        return 1
    product_id = product.json()["id"]

    movement = client.post(
        "/api/inventory/movements",
        headers=headers,
        json={
            "product_id": product_id,
            "movement_type": "entrada",
            "quantity": "50",
            "reason": "Stock fase 11",
        },
    )
    check("Entrada de inventario", movement.status_code in (200, 201),
          movement.text[:160])

    methods = get_json(client, "/api/payment-methods", headers)
    sale_payload: dict = {
        "items": [{"product_id": product_id, "quantity": 2}],
    }
    if methods:
        sale_payload["payment"] = {"payment_method_id": methods[0]["id"]}
    sale = client.post("/api/sales", headers=headers, json=sale_payload)
    check("Crear venta (con pago si hay métodos)", sale.status_code == 201,
          sale.text[:200])

    before_sale = get_json(
        client, "/api/insights", headers, page=1, page_size=1
    )["total"]
    gen3 = post_json(client, "/api/insights/generate", headers)
    created3 = gen3.json()["created"]
    codes3 = [item["rule_code"] for item in created3]
    check(
        "Nueva venta → se crea al menos un insight",
        len(created3) >= 1,
        str(codes3),
    )
    check(
        "La tendencia de ingresos refleja la nueva venta",
        "revenue_trend" in codes3,
        str(codes3),
    )
    after_sale = get_json(
        client, "/api/insights", headers, page=1, page_size=1
    )["total"]
    check(
        "El total crece por los insights creados",
        after_sale == before_sale + len(created3),
        f"{before_sale} + {len(created3)} != {after_sale}",
    )
    broken3 = broken_items(client, headers, created3, catalog)
    check(
        "Los insights nuevos coinciden con /analytics y /sales",
        not broken3,
        " | ".join(broken3[:2]),
    )

    # ---------------------------------------------------------------
    step("7. Análisis estadísticos → insights vinculados")
    # ---------------------------------------------------------------
    dataset = client.post(
        "/api/datasets",
        headers=headers,
        json={
            "name": f"Insights {suffix}",
            "source_type": "manual",
            "description": "Datos para los insights de la Fase 11",
        },
    )
    check("Crear dataset", dataset.status_code == 201,
          dataset.text[:160])
    dataset_id = dataset.json()["id"]

    variable = client.post(
        f"/api/datasets/{dataset_id}/variables",
        headers=headers,
        json={
            "name": "monto",
            "data_type": "numeric",
            "variable_type": "continua",
            "description": "Monto de referencia",
        },
    )
    check("Crear variable numérica", variable.status_code == 201,
          variable.text[:160])
    variable_id = variable.json()["id"]

    observations = client.post(
        f"/api/datasets/{dataset_id}/observations",
        headers=headers,
        json={
            "items": [
                {"variable_id": variable_id, "numeric_value": value}
                for value in (10.0, 10.0, 10.0, 10.0, 100.0)
            ]
        },
    )
    check(
        "Observaciones sesgadas (media 28, mediana 10)",
        observations.status_code == 201,
        observations.text[:160],
    )

    analyses_expected: dict[str, int] = {}

    mean_median = client.post(
        "/api/analyses/mean-median",
        headers=headers,
        json={"variable_id": variable_id},
    )
    check("Análisis media/mediana → 201",
          mean_median.status_code == 201, mean_median.text[:160])
    analyses_expected["mean_median_skew"] = mean_median.json()["id"]

    for label, payload, expect_independent in (
        (
            "probabilidad independiente",
            {"p_a": 0.5, "p_b": 0.5, "p_a_and_b": 0.25},
            True,
        ),
        (
            "probabilidad dependiente",
            {"p_a": 0.5, "p_b": 0.4, "p_a_and_b": 0.3},
            False,
        ),
    ):
        response = client.post(
            "/api/analyses/probability", headers=headers, json=payload
        )
        independence = {}
        if response.status_code == 201:
            independence = next(
                (
                    row
                    for row in response.json().get("results") or []
                    if row["metric_name"] == "independence"
                ),
                {},
            )
        independent = (independence.get("result_payload") or {}).get(
            "independent"
        )
        check(
            f"Análisis de {label} → 201",
            response.status_code == 201,
            response.text[:160],
        )
        check(
            f"Independencia detectada = {expect_independent}",
            independent is expect_independent,
            str(independent),
        )

    bayes = client.post(
        "/api/analyses/bayes",
        headers=headers,
        json={
            "probability_a": 0.1,
            "probability_b_given_a": 0.9,
            "probability_b": 0.3,
        },
    )
    check("Análisis de Bayes → 201", bayes.status_code == 201,
          bayes.text[:160])
    analyses_expected["bayes_posterior"] = bayes.json()["id"]

    random_variable = client.post(
        "/api/analyses/random-variable",
        headers=headers,
        json={
            "variable_id": variable_id,
            "distribution": "binomial",
            "parameters": {"n": 10, "p": 0.5},
        },
    )
    check("Análisis de variable aleatoria → 201",
          random_variable.status_code == 201, random_variable.text[:160])
    analyses_expected["random_variable_expected"] = (
        random_variable.json()["id"]
    )

    gen4 = post_json(client, "/api/insights/generate", headers)
    created4 = gen4.json()["created"]
    codes4 = sorted(item["rule_code"] for item in created4)
    expected4 = sorted(
        [
            "mean_median_skew",
            "random_variable_expected",
            "probability_independence",
            "probability_independence",
            "bayes_posterior",
        ]
    )
    check(
        "Los 5 análisis nuevos generan 5 insights",
        codes4 == expected4,
        f"{codes4} != {expected4}",
    )
    check(
        "Ninguna regla de ventas duplicada en esta ejecución",
        not (set(codes4) & SALES_RULES),
        str(codes4),
    )

    linked = [
        item
        for item in created4
        if item["rule_code"] in {"mean_median_skew",
                                 "random_variable_expected"}
    ]
    check(
        "Insights de datos vinculados a su dataset",
        len(linked) == 2
        and all(item["dataset_id"] == dataset_id for item in linked)
        and all(item["dataset_name"] for item in linked),
        str([(i["rule_code"], i["dataset_id"]) for i in linked]),
    )
    bayes_insight = next(
        (i for i in created4 if i["rule_code"] == "bayes_posterior"), {}
    )
    check(
        "Insight de Bayes sin dataset (parámetros manuales)",
        bayes_insight.get("dataset_id") is None,
        str(bayes_insight.get("dataset_id")),
    )
    broken4 = broken_items(client, headers, created4, catalog)
    check(
        "La evidencia de análisis == resultados del análisis",
        not broken4,
        " | ".join(broken4[:2]),
    )

    # ---------------------------------------------------------------
    step("8. Filtros y paginación")
    # ---------------------------------------------------------------
    filtered = get_json(
        client, "/api/insights", headers, rule_code="revenue_trend",
        page_size=100,
    )
    check(
        "Filtro rule_code devuelve solo esa regla",
        isinstance(filtered, dict)
        and filtered["total"] >= 1
        and all(i["rule_code"] == "revenue_trend"
                for i in filtered["items"]),
        str(filtered and filtered["total"]),
    )
    warnings = get_json(
        client, "/api/insights", headers, severity="warning",
        page_size=100,
    )
    check(
        "Filtro severity=warning",
        isinstance(warnings, dict)
        and warnings["total"] >= 1
        and all(i["severity"] == "warning" for i in warnings["items"]),
        str(warnings and warnings["total"]),
    )
    positives = get_json(
        client, "/api/insights", headers, severity="positive",
        page_size=100,
    )
    check(
        "Filtro severity=positive (solo si hay tendencias al alza)",
        positives is None
        or all(i["severity"] == "positive" for i in positives["items"]),
    )
    by_analysis = get_json(
        client,
        "/api/insights",
        headers,
        analysis_id=analyses_expected["mean_median_skew"],
        page_size=100,
    )
    check(
        "Filtro analysis_id devuelve solo su insight",
        isinstance(by_analysis, dict)
        and by_analysis["total"] == 1
        and by_analysis["items"][0]["rule_code"] == "mean_median_skew",
        str(by_analysis and by_analysis["total"]),
    )
    by_dataset = get_json(
        client, "/api/insights", headers, dataset_id=dataset_id,
        page_size=100,
    )
    check(
        "Filtro dataset_id → los 2 insights enlazados",
        isinstance(by_dataset, dict) and by_dataset["total"] == 2,
        str(by_dataset and by_dataset["total"]),
    )

    first_page = get_json(
        client, "/api/insights", headers, page=1, page_size=2
    )
    second_page = get_json(
        client, "/api/insights", headers, page=2, page_size=2
    )
    all_items = fetch_all(client, headers)
    check(
        "Paginación: página 1 con 2 elementos",
        isinstance(first_page, dict)
        and len(first_page["items"]) == 2
        and first_page["page"] == 1
        and first_page["total"] == len(all_items),
        str(first_page and len(first_page["items"])),
    )
    check(
        "Paginación: página 2 continúa y no repite ids",
        isinstance(second_page, dict)
        and {i["id"] for i in second_page["items"]}.isdisjoint(
            {i["id"] for i in first_page["items"]}
        ),
    )
    empty_page = get_json(
        client, "/api/insights", headers, page=9999, page_size=2
    )
    check(
        "Página fuera de rango → vacía con el mismo total",
        isinstance(empty_page, dict)
        and empty_page["items"] == []
        and empty_page["total"] == len(all_items),
    )
    oldest, newest = all_items[-1], all_items[0]
    check(
        "El historial ordena del más reciente al más antiguo",
        newest["created_at"] >= oldest["created_at"],
        f"{newest['created_at']} < {oldest['created_at']}",
    )

    # ---------------------------------------------------------------
    step("9. Validaciones")
    # ---------------------------------------------------------------
    bad_rule = client.get(
        "/api/insights", headers=headers, params={"rule_code": "no_existe"}
    )
    check("rule_code desconocido → 400",
          bad_rule.status_code == 400, str(bad_rule.status_code))
    bad_severity = client.get(
        "/api/insights", headers=headers, params={"severity": "rojo"}
    )
    check("severity inválido → 422",
          bad_severity.status_code == 422, str(bad_severity.status_code))
    bad_page = client.get(
        "/api/insights", headers=headers, params={"page": 0}
    )
    check("page=0 → 422", bad_page.status_code == 422,
          str(bad_page.status_code))
    bad_size = client.get(
        "/api/insights", headers=headers, params={"page_size": 101}
    )
    check("page_size=101 → 422",
          bad_size.status_code == 422, str(bad_size.status_code))

    bad_range = post_json(
        client,
        "/api/insights/generate",
        headers,
        {"date_from": (today - timedelta(days=1)).isoformat(),
         "date_to": (today - timedelta(days=5)).isoformat()},
    )
    check("Generación con rango invertido → 400",
          bad_range.status_code == 400, str(bad_range.status_code))
    bad_period = post_json(
        client, "/api/insights/generate", headers, {"period": "15"}
    )
    check("period=15 (no permitido) → 422",
          bad_period.status_code == 422, str(bad_period.status_code))

    # ---------------------------------------------------------------
    step("10. Períodos del frontend (30 días y histórico)")
    # ---------------------------------------------------------------
    expected_30 = (today - timedelta(days=29)).isoformat()
    gen30 = post_json(
        client, "/api/insights/generate", headers, {"period": "30"}
    )
    check("Generación con period=30 → 200",
          gen30.status_code == 200, gen30.text[:200])
    windowed30 = [
        item
        for item in gen30.json().get("created", [])
        if "date_from" in item["evidence"]
    ]
    check(
        "period=30 → ventana [hoy-29, hoy] en la evidencia",
        all(
            item["evidence"]["date_from"] == expected_30
            and item["evidence"]["date_to"] == today.isoformat()
            for item in windowed30
        ),
        str([i["evidence"].get("date_from") for i in windowed30[:3]]),
    )

    gen_all = post_json(
        client, "/api/insights/generate", headers, {"period": "all"}
    )
    check("Generación con period=all → 200",
          gen_all.status_code == 200, gen_all.text[:200])
    windowless = [
        item
        for item in gen_all.json().get("created", [])
        if "date_from" in item["evidence"]
    ]
    check(
        "period=all → sin ventana (fechas nulas) en la evidencia",
        all(item["evidence"]["date_from"] is None for item in windowless),
        str([i["evidence"].get("date_from") for i in windowless[:3]]),
    )

    # ---------------------------------------------------------------
    step("11. Aislamiento multiempresa")
    # ---------------------------------------------------------------
    other_list = get_json(
        client, "/api/insights", other_headers, page=1, page_size=10
    )
    admin_before = get_json(
        client, "/api/insights", headers, page=1, page_size=1
    )["total"]
    check(
        "Otra empresa no ve insights ajenos (total = 0)",
        isinstance(other_list, dict) and other_list["total"] == 0,
        str(other_list and other_list["total"]),
    )
    other_gen = post_json(
        client, "/api/insights/generate", other_headers
    )
    check(
        "Generación sin datos → 0 creados y 0 omitidos",
        other_gen.status_code == 200
        and other_gen.json()["created"] == []
        and other_gen.json()["skipped"] == 0,
        other_gen.text[:200],
    )
    admin_after = get_json(
        client, "/api/insights", headers, page=1, page_size=1
    )["total"]
    check(
        "La generación de otra empresa no toca los insights ajenos",
        admin_after == admin_before,
        f"{admin_before} != {admin_after}",
    )
    other_rules = get_json(client, "/api/insights/rules", other_headers)
    check(
        "Otra empresa también consulta el catálogo",
        isinstance(other_rules, list) and len(other_rules) == 12,
    )
    other_dataset_filter = get_json(
        client, "/api/insights", other_headers, dataset_id=dataset_id
    )
    check(
        "Filtro dataset_id ajeno no devuelve nada",
        isinstance(other_dataset_filter, dict)
        and other_dataset_filter["total"] == 0,
        str(other_dataset_filter and other_dataset_filter["total"]),
    )

    # ---------------------------------------------------------------
    step("12. Barrido final")
    # ---------------------------------------------------------------
    all_final = fetch_all(client, headers)
    fresh = [
        item for item in all_final if item["id"] not in ids_before_sale
    ]
    broken_final = broken_items(client, headers, fresh, catalog)
    check(
        f"Barrido final: {len(fresh)} insights posteriores a la nueva "
        "venta coinciden con sus datos",
        not broken_final,
        " | ".join(broken_final[:3]),
    )
    check(
        "Histórico con insights suficientes",
        len(all_final) >= 8,
        str(len(all_final)),
    )
    check(
        "Solo reglas del catálogo en el historial",
        all(item["rule_code"] in ALL_RULES for item in all_final),
    )
    check(
        "Solo severidades válidas en el historial",
        all(item["severity"] in SEVERITIES for item in all_final),
    )
    check(
        "Las reglas de análisis están vinculadas a su análisis",
        all(
            item["analysis_id"] is not None
            for item in all_final
            if item["rule_code"] in ANALYSIS_RULES
        ),
    )
    check(
        "Las reglas de ventas no llevan análisis",
        all(
            item["analysis_id"] is None
            for item in all_final
            if item["rule_code"] in SALES_RULES
        ),
    )

    client.close()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
