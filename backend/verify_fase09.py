"""
Verificación end-to-end de la Fase 09 (Motor estadístico – Semana 07).

Cubre los criterios de aceptación de la fase:
  - El sistema calcula correctamente media y mediana.
  - El sistema permite identificar variables estadísticas.
  - El sistema puede analizar variables aleatorias definidas.
  - El módulo de Bayes devuelve un resultado reproducible.
  - Los análisis quedan almacenados y pueden consultarse.

Requisitos:
  - Backend corriendo:  uvicorn app.main:app --reload --port 8000
  - (opcional) PostgreSQL: sin él, la comprobación de BD se omite

Uso:
  python verify_fase09.py
"""
from __future__ import annotations

import sys
import uuid

import httpx

BASE_URL = "http://localhost:8000"
EMAIL = "admin@salesia.com"
PASSWORD = "Admin123*"
OTHER_EMAIL = "gerente@otraempresa.com"
OTHER_PASSWORD = "Gerente123*"

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


def metric(analysis: dict, name: str) -> dict | None:
    for item in analysis.get("results", []):
        if item["metric_name"] == name:
            return item
    return None


def main() -> int:
    client = httpx.Client(base_url=BASE_URL, timeout=15.0)

    # ---------------------------------------------------------------
    step("1. Servidor")
    # ---------------------------------------------------------------
    try:
        root = client.get("/")
        check("API responde en /", root.status_code == 200, str(root.status_code))
    except httpx.ConnectError:
        print("  ❌ No se pudo conectar. ¿Está uvicorn corriendo en :8000?")
        return 1

    health = client.get("/health/database")
    if health.status_code == 200:
        data = health.json()
        check("PostgreSQL conectado", True, str(data))
        print(f"     BD: {data['database']} · {data['database_user']}")
    else:
        print(
            "  ⚠️  PostgreSQL no disponible (entorno SQLite): "
            "se omite la comprobación de BD"
        )

    # ---------------------------------------------------------------
    step("2. Autenticación")
    # ---------------------------------------------------------------
    login = client.post(
        "/api/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
    )
    check("Login admin", login.status_code == 200, login.text)
    token = login.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}

    login_other = client.post(
        "/api/auth/login",
        json={"email": OTHER_EMAIL, "password": OTHER_PASSWORD},
    )
    check(
        "Login segunda empresa",
        login_other.status_code == 200,
        login_other.text,
    )
    other_headers = {
        "Authorization": f"Bearer {login_other.json().get('access_token', '')}"
    }

    # ---------------------------------------------------------------
    step("3. Datasets y clasificación de variables")
    # ---------------------------------------------------------------
    suffix = uuid.uuid4().hex[:6]
    dataset_payload = {
        "name": f"Ventas semana 07 {suffix}",
        "source_type": "manual",
        "description": "Dataset de prueba del motor estadístico",
    }
    created = client.post(
        "/api/datasets", json=dataset_payload, headers=headers
    )
    check("Crear dataset", created.status_code == 201, created.text)
    dataset_id = created.json().get("id")

    # 3.1 Variables con las tres clasificaciones de la Semana 07
    var_specs = [
        {
            "name": "zona",
            "data_type": "text",
            "variable_type": "cualitativa",
            "description": "Zona de venta",
        },
        {
            "name": "clientes_por_dia",
            "data_type": "numeric",
            "variable_type": "discreta",
            "description": "Clientes atendidos por día",
        },
        {
            "name": "monto_venta",
            "data_type": "numeric",
            "variable_type": "continua",
            "description": "Monto de cada venta",
        },
    ]
    variable_ids = {}
    for spec in var_specs:
        response = client.post(
            f"/api/datasets/{dataset_id}/variables",
            json=spec,
            headers=headers,
        )
        check(
            f"Crear variable '{spec['name']}' ({spec['variable_type']})",
            response.status_code == 201,
            response.text,
        )
        variable_ids[spec["name"]] = response.json().get("id")

    # 3.2 Reglas de clasificación
    invalid_class = client.post(
        f"/api/datasets/{dataset_id}/variables",
        json={
            "name": "mala_clasificacion",
            "data_type": "text",
            "variable_type": "continua",
        },
        headers=headers,
    )
    check(
        "Cualitativa no puede ser continua → 400",
        invalid_class.status_code == 400,
        str(invalid_class.status_code),
    )

    duplicated = client.post(
        f"/api/datasets/{dataset_id}/variables",
        json=var_specs[0],
        headers=headers,
    )
    check(
        "Variable duplicada → 409",
        duplicated.status_code == 409,
        str(duplicated.status_code),
    )

    # 3.3 Observaciones en lote
    monto_id = variable_ids["monto_venta"]
    zona_id = variable_ids["zona"]
    montos = [10.0, 20.0, 30.0, 40.0, 100.0]
    observations = client.post(
        f"/api/datasets/{dataset_id}/observations",
        json={
            "items": [
                {"variable_id": monto_id, "numeric_value": value}
                for value in montos
            ]
            + [
                {"variable_id": zona_id, "text_value": zona}
                for zona in ("Norte", "Sur", "Este")
            ]
        },
        headers=headers,
    )
    check(
        "Registrar observaciones en lote (5 numéricas + 3 texto)",
        observations.status_code == 201 and observations.json().get("created") == 8,
        observations.text,
    )

    wrong_type = client.post(
        f"/api/datasets/{dataset_id}/observations",
        json={"items": [{"variable_id": zona_id, "numeric_value": 5}]},
        headers=headers,
    )
    check(
        "Observación numérica en variable cualitativa → 400",
        wrong_type.status_code == 400,
        str(wrong_type.status_code),
    )

    detail = client.get(f"/api/datasets/{dataset_id}", headers=headers)
    variables = detail.json().get("variables", [])
    counts = {var["name"]: var["observations_count"] for var in variables}
    check(
        "Detalle del dataset con conteos",
        detail.status_code == 200
        and counts.get("monto_venta") == 5
        and counts.get("zona") == 3,
        str(counts),
    )

    # ---------------------------------------------------------------
    step("4. Media y mediana (criterio de aceptación)")
    # ---------------------------------------------------------------
    mean_median = client.post(
        "/api/analyses/mean-median",
        json={"variable_id": monto_id},
        headers=headers,
    )
    check("Análisis media/mediana → 201", mean_median.status_code == 201, mean_median.text)
    mm = mean_median.json()

    mean_value = (metric(mm, "mean") or {}).get("numeric_result")
    median_value = (metric(mm, "median") or {}).get("numeric_result")
    count_value = (metric(mm, "count") or {}).get("numeric_result")
    comparison = (metric(mm, "comparison") or {}).get("result_payload", {})

    check("Media = 40", close(float(mean_value), 40.0), str(mean_value))
    check("Mediana = 30", close(float(median_value), 30.0), str(median_value))
    check("n = 5", close(float(count_value), 5.0), str(count_value))
    check(
        "Comparación: media > mediana (sesgo positivo)",
        comparison.get("relation") == "media_mayor_mediana"
        and "positivo" in comparison.get("interpretation", ""),
        str(comparison),
    )

    # 4.1 Par (media == mediana)
    par_id = client.post(
        f"/api/datasets/{dataset_id}/variables",
        json={
            "name": "valores_pares",
            "data_type": "numeric",
            "variable_type": "discreta",
        },
        headers=headers,
    ).json().get("id")
    client.post(
        f"/api/datasets/{dataset_id}/observations",
        json={
            "items": [
                {"variable_id": par_id, "numeric_value": value}
                for value in (1.0, 2.0, 3.0, 4.0)
            ]
        },
        headers=headers,
    )
    par_analysis = client.post(
        "/api/analyses/mean-median",
        json={"variable_id": par_id},
        headers=headers,
    ).json()
    par_comparison = (metric(par_analysis, "comparison") or {}).get(
        "result_payload", {}
    )
    check(
        "Par: media = mediana = 2.5 (simétrica)",
        close(
            float((metric(par_analysis, "mean") or {}).get("numeric_result", 0)),
            2.5,
        )
        and close(
            float((metric(par_analysis, "median") or {}).get("numeric_result", 0)),
            2.5,
        )
        and par_comparison.get("relation") == "media_igual_mediana",
        str(par_comparison),
    )

    # 4.2 Casos inválidos
    qualitative = client.post(
        "/api/analyses/mean-median",
        json={"variable_id": zona_id},
        headers=headers,
    )
    check(
        "Media sobre variable cualitativa → 400",
        qualitative.status_code == 400,
        str(qualitative.status_code),
    )

    empty_var = client.post(
        f"/api/datasets/{dataset_id}/variables",
        json={
            "name": "sin_datos",
            "data_type": "numeric",
            "variable_type": "continua",
        },
        headers=headers,
    ).json().get("id")
    empty = client.post(
        "/api/analyses/mean-median",
        json={"variable_id": empty_var},
        headers=headers,
    )
    check(
        "Media sin observaciones → 400",
        empty.status_code == 400,
        str(empty.status_code),
    )

    missing = client.post(
        "/api/analyses/mean-median",
        json={"variable_id": 999999},
        headers=headers,
    )
    check("Variable inexistente → 404", missing.status_code == 404, str(missing.status_code))

    # ---------------------------------------------------------------
    step("5. Variables aleatorias")
    # ---------------------------------------------------------------
    random_cases = [
        # (distribución, parámetros, esperanza, varianza)
        ("uniforme", {"a": 2.0, "b": 8.0}, 5.0, 3.0),
        ("bernoulli", {"p": 0.25}, 0.25, 0.1875),
        ("binomial", {"n": 10, "p": 0.5}, 5.0, 2.5),
        ("normal", {"mu": 100.0, "sigma": 15.0}, 100.0, 225.0),
    ]
    for distribution, parameters, expected, variance in random_cases:
        response = client.post(
            "/api/analyses/random-variable",
            json={
                "variable_id": monto_id,
                "distribution": distribution,
                "parameters": parameters,
            },
            headers=headers,
        )
        data = response.json()
        exp_value = (metric(data, "expected_value") or {}).get("numeric_result")
        var_value = (metric(data, "variance") or {}).get("numeric_result")
        std_value = (metric(data, "std_dev") or {}).get("numeric_result")
        check(
            f"{distribution}{parameters} → E(X)={expected}, Var={variance}",
            response.status_code == 201
            and exp_value is not None
            and close(float(exp_value), expected)
            and close(float(var_value), variance)
            and close(float(std_value), variance**0.5),
            response.text,
        )

    empirical = metric(
        client.post(
            "/api/analyses/random-variable",
            json={
                "variable_id": monto_id,
                "distribution": "normal",
                "parameters": {"mu": 40.0, "sigma": 10.0},
            },
            headers=headers,
        ).json(),
        "empirical_mean",
    )
    check(
        "Comparación con media empírica (40)",
        empirical is not None and close(float(empirical.get("numeric_result")), 40.0),
        str(empirical),
    )

    bad_distribution = client.post(
        "/api/analyses/random-variable",
        json={
            "variable_id": monto_id,
            "distribution": "poisson",
            "parameters": {"lambda": 3},
        },
        headers=headers,
    )
    check(
        "Distribución no soportada → 422 (schema)",
        bad_distribution.status_code == 422,
        str(bad_distribution.status_code),
    )

    bad_params = client.post(
        "/api/analyses/random-variable",
        json={
            "variable_id": monto_id,
            "distribution": "bernoulli",
            "parameters": {"p": 1.5},
        },
        headers=headers,
    )
    check(
        "Parámetro inválido (p=1.5) → 400",
        bad_params.status_code == 400,
        str(bad_params.status_code),
    )

    # ---------------------------------------------------------------
    step("6. Probabilidades")
    # ---------------------------------------------------------------
    prob = client.post(
        "/api/analyses/probability",
        json={"p_a": 0.6, "p_b": 0.5, "p_a_and_b": 0.3},
        headers=headers,
    )
    check("Análisis de probabilidad → 201", prob.status_code == 201, prob.text)
    prob_data = prob.json()
    p_a_given_b = (metric(prob_data, "p_a_given_b") or {}).get("numeric_result")
    p_b_given_a = (metric(prob_data, "p_b_given_a") or {}).get("numeric_result")
    independence = (metric(prob_data, "independence") or {}).get("result_payload", {})
    check("P(A|B) = 0.6", close(float(p_a_given_b), 0.6), str(p_a_given_b))
    check("P(B|A) = 0.5", close(float(p_b_given_a), 0.5), str(p_b_given_a))
    check(
        "A y B independientes (0.3 = 0.6·0.5)",
        independence.get("independent") is True,
        str(independence),
    )

    dependent = client.post(
        "/api/analyses/probability",
        json={"p_a": 0.6, "p_b": 0.5, "p_a_and_b": 0.4},
        headers=headers,
    ).json()
    dep_independence = (metric(dependent, "independence") or {}).get(
        "result_payload", {}
    )
    check(
        "Eventos no independientes detectados",
        dep_independence.get("independent") is False,
        str(dep_independence),
    )

    impossible = client.post(
        "/api/analyses/probability",
        json={"p_a": 0.3, "p_b": 0.5, "p_a_and_b": 0.6},
        headers=headers,
    )
    check(
        "P(A ∩ B) > P(A) → 400",
        impossible.status_code == 400,
        str(impossible.status_code),
    )

    zero_b = client.post(
        "/api/analyses/probability",
        json={"p_a": 0.6, "p_b": 0.0, "p_a_and_b": 0.0},
        headers=headers,
    )
    check("P(B)=0 → 422 (schema gt...)", zero_b.status_code in (400, 422), str(zero_b.status_code))

    # ---------------------------------------------------------------
    step("7. Teorema de Bayes (criterio de aceptación)")
    # ---------------------------------------------------------------
    # 7.1 Con P(B) directa
    bayes = client.post(
        "/api/analyses/bayes",
        json={
            "probability_a": 0.3,
            "probability_b_given_a": 0.9,
            "probability_b": 0.42,
        },
        headers=headers,
    )
    check("Bayes con P(B) directa → 201", bayes.status_code == 201, bayes.text)
    bayes_data = bayes.json()
    posterior = (metric(bayes_data, "posterior_probability") or {}).get(
        "numeric_result"
    )
    # 0.3 · 0.9 / 0.42 = 0.642857...
    check(
        "Posterior = 0.642857 (reproducible)",
        posterior is not None and close(float(posterior), 0.642857, 1e-5),
        str(posterior),
    )
    check(
        "Bloque bayes persistido",
        bayes_data.get("bayes") is not None
        and close(float(bayes_data["bayes"]["posterior_probability"]), 0.642857, 1e-5)
        and "P(A|B)" in (bayes_data["bayes"].get("explanation") or ""),
        str(bayes_data.get("bayes")),
    )

    # 7.2 Con ley de probabilidad total (complemento)
    # P(A)=0.01, P(B|A)=0.9, P(B|¬A)=0.2
    # P(B) = 0.9·0.01 + 0.2·0.99 = 0.207
    # P(A|B) = 0.009 / 0.207 = 0.043478...
    bayes2 = client.post(
        "/api/analyses/bayes",
        json={
            "probability_a": 0.01,
            "probability_b_given_a": 0.9,
            "probability_b_given_not_a": 0.2,
        },
        headers=headers,
    )
    check("Bayes con complemento → 201", bayes2.status_code == 201, bayes2.text)
    bayes2_data = bayes2.json()
    posterior2 = (metric(bayes2_data, "posterior_probability") or {}).get(
        "numeric_result"
    )
    marginal2 = (metric(bayes2_data, "marginal_probability") or {}).get(
        "numeric_result"
    )
    check(
        "P(B) total = 0.207",
        marginal2 is not None and close(float(marginal2), 0.207),
        str(marginal2),
    )
    check(
        "Posterior = 0.043478",
        posterior2 is not None and close(float(posterior2), 0.043478, 1e-5),
        str(posterior2),
    )
    check(
        "Explicación con la fórmula completa",
        "probabilidad total" in (
            (bayes2_data.get("bayes") or {}).get("explanation") or ""
        ),
        str(bayes2_data.get("bayes")),
    )

    # 7.3 Casos inválidos
    no_denominator = client.post(
        "/api/analyses/bayes",
        json={"probability_a": 0.3, "probability_b_given_a": 0.9},
        headers=headers,
    )
    check(
        "Sin P(B) ni P(B|¬A) → 400",
        no_denominator.status_code == 400,
        str(no_denominator.status_code),
    )

    inconsistent = client.post(
        "/api/analyses/bayes",
        json={
            "probability_a": 0.5,
            "probability_b_given_a": 0.9,
            "probability_b": 0.2,
        },
        headers=headers,
    )
    check(
        "Posterior > 1 → 400 (inconsistentes)",
        inconsistent.status_code == 400,
        str(inconsistent.status_code),
    )

    # ---------------------------------------------------------------
    step("8. Historial: análisis almacenados")
    # ---------------------------------------------------------------
    history = client.get("/api/analyses", params={"page_size": 100}, headers=headers)
    check("Listar análisis", history.status_code == 200, history.text)
    history_data = history.json()
    check(
        "Hay al menos 8 análisis registrados",
        history_data.get("total", 0) >= 8,
        str(history_data.get("total")),
    )
    check(
        "Cada análisis trae sus resultados",
        all(item.get("results") for item in history_data.get("items", [])),
        "analisis sin resultados",
    )

    filtered = client.get(
        "/api/analyses",
        params={"analysis_type": "bayes"},
        headers=headers,
    )
    check(
        "Filtro por tipo 'bayes'",
        filtered.status_code == 200
        and filtered.json().get("total", 0) >= 2
        and all(
            item["analysis_type"] == "bayes"
            for item in filtered.json().get("items", [])
        ),
        str(filtered.json().get("total")),
    )

    first_id = history_data["items"][0]["id"]
    detail_analysis = client.get(
        f"/api/analyses/{first_id}", headers=headers
    )
    check(
        "Detalle de análisis concreto",
        detail_analysis.status_code == 200
        and detail_analysis.json().get("id") == first_id,
        detail_analysis.text,
    )

    missing_analysis = client.get("/api/analyses/999999", headers=headers)
    check(
        "Análisis inexistente → 404",
        missing_analysis.status_code == 404,
        str(missing_analysis.status_code),
    )

    # ---------------------------------------------------------------
    step("9. Aislamiento entre empresas")
    # ---------------------------------------------------------------
    other_datasets = client.get(
        "/api/datasets", headers=other_headers
    )
    check(
        "Otra empresa no ve nuestros datasets",
        other_datasets.status_code == 200
        and all(
            item["id"] != dataset_id
            for item in other_datasets.json().get("items", [])
        ),
        str(other_datasets.json()),
    )

    other_detail = client.get(
        f"/api/datasets/{dataset_id}", headers=other_headers
    )
    check(
        "Detalle de dataset ajeno → 404",
        other_detail.status_code == 404,
        str(other_detail.status_code),
    )

    other_history = client.get("/api/analyses", headers=other_headers)
    check(
        "Otra empresa no ve nuestros análisis",
        other_history.status_code == 200
        and all(
            item["id"] != first_id
            for item in other_history.json().get("items", [])
        ),
        str(other_history.json().get("total")),
    )

    other_analysis = client.post(
        "/api/analyses/mean-median",
        json={"variable_id": monto_id},
        headers=other_headers,
    )
    check(
        "Otra empresa no analiza variables ajenas → 404",
        other_analysis.status_code == 404,
        str(other_analysis.status_code),
    )

    # ---------------------------------------------------------------
    step("10. Reclasificación y borrado de dataset")
    # ---------------------------------------------------------------
    reclassified = client.patch(
        f"/api/datasets/{dataset_id}/variables/{par_id}",
        json={"variable_type": "continua"},
        headers=headers,
    )
    check(
        "Reclasificar variable discreta → continua",
        reclassified.status_code == 200
        and reclassified.json().get("variable_type") == "continua",
        reclassified.text,
    )

    blocked_change = client.patch(
        f"/api/datasets/{dataset_id}/variables/{monto_id}",
        json={"data_type": "text"},
        headers=headers,
    )
    check(
        "Cambiar tipo de dato con observaciones → 400",
        blocked_change.status_code == 400,
        str(blocked_change.status_code),
    )

    deleted = client.delete(f"/api/datasets/{dataset_id}", headers=headers)
    check("Borrar dataset → 204", deleted.status_code == 204, str(deleted.status_code))

    deleted_again = client.delete(f"/api/datasets/{dataset_id}", headers=headers)
    check("Borrar dataset inexistente → 404", deleted_again.status_code == 404, str(deleted_again.status_code))

    # ---------------------------------------------------------------
    print(f"\n{'=' * 60}")
    print(f"RESULTADO: {passed} correctas · {failed} incorrectas")
    print("=" * 60)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
