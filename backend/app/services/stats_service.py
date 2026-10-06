"""Motor estadístico – Fase 09 (Semana 07).

Implementa las operaciones académicas de la Semana 07 sobre los datos
del sistema y registra cada análisis con sus resultados:

  - Clasificación de variables (cualitativa / discreta / continua)
  - Media aritmética y mediana, con comparación entre ambas
  - Variables aleatorias (uniforme, bernoulli, binomial, normal)
  - Probabilidades (condicionales e independencia)
  - Teorema de Bayes (posterior reproducible)

Cada ejecución deja constancia en `statistical_analyses` +
`statistical_results` (y en `bayes_analyses` / `random_variables`
cuando corresponde), de modo que el historial puede consultarse.
"""

import math
import statistics
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.bayes_analysis import BayesAnalysis
from app.models.dataset import Dataset
from app.models.dataset_variable import DatasetVariable
from app.models.random_variable import RandomVariable
from app.models.statistical_analysis import StatisticalAnalysis
from app.models.statistical_result import StatisticalResult
from app.schemas.analysis import BayesInput, ProbabilityInput
from app.services import dataset_service

TOLERANCE = 1e-9


class AnalysisError(Exception):
    """Error de regla de negocio del motor estadístico."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _round(value: float) -> float:
    """Redondeo estable para persistir y comparar resultados."""
    return round(float(value), 6)


# ---------------------------------------------------------------
# Utilidades de datos
# ---------------------------------------------------------------
def _get_numeric_variable(
    db: Session, company_id: int, variable_id: int
) -> tuple[Dataset, DatasetVariable]:
    """Variable numérica de la empresa (valida clasificación y alcance)."""
    row = db.execute(
        select(Dataset, DatasetVariable)
        .join(Dataset, DatasetVariable.dataset_id == Dataset.id)
        .where(
            DatasetVariable.id == variable_id,
            Dataset.company_id == company_id,
        )
    ).first()

    if row is None:
        raise AnalysisError(f"La variable {variable_id} no existe")

    dataset, variable = row

    if variable.data_type != "numeric":
        raise AnalysisError(
            f"La variable '{variable.name}' es cualitativa: "
            "las operaciones numéricas requieren datos numéricos"
        )

    return dataset, variable


def _register_analysis(
    db: Session,
    *,
    company_id: int,
    user_id: int,
    analysis_type: str,
    parameters: dict,
    dataset_id: int | None,
    results: list[dict],
) -> StatisticalAnalysis:
    """Persiste el análisis con sus resultados (patrón de la fase 09)."""
    analysis = StatisticalAnalysis(
        company_id=company_id,
        dataset_id=dataset_id,
        analysis_type=analysis_type,
        parameters=parameters,
        status="completed",
        created_by=user_id,
        created_at=_now(),
    )
    db.add(analysis)
    db.flush()

    for item in results:
        db.add(
            StatisticalResult(
                analysis_id=analysis.id,
                metric_name=item["metric_name"],
                numeric_result=item.get("numeric_result"),
                result_payload=item.get("result_payload") or {},
                created_at=_now(),
            )
        )

    db.commit()
    db.refresh(analysis)
    return analysis


# ---------------------------------------------------------------
# Media y mediana
# ---------------------------------------------------------------
def run_mean_median(
    db: Session,
    company_id: int,
    user_id: int,
    variable_id: int,
) -> StatisticalAnalysis:
    """Calcula media y mediana de una variable y compara ambas."""
    dataset, variable = _get_numeric_variable(db, company_id, variable_id)

    values = dataset_service.numeric_values(db, dataset.id, variable.id)

    if not values:
        raise AnalysisError(
            f"La variable '{variable.name}' no tiene observaciones numéricas"
        )

    mean = _round(statistics.mean(values))
    median = _round(statistics.median(values))
    difference = _round(mean - median)

    if abs(difference) <= TOLERANCE:
        relation = "media_igual_mediana"
        interpretation = (
            "La media y la mediana coinciden: distribución aproximadamente "
            "simétrica."
        )
    elif difference > 0:
        relation = "media_mayor_mediana"
        interpretation = (
            "La media supera a la mediana: sesgo positivo "
            "(cola hacia la derecha)."
        )
    else:
        relation = "media_menor_mediana"
        interpretation = (
            "La media es inferior a la mediana: sesgo negativo "
            "(cola hacia la izquierda)."
        )

    analysis = _register_analysis(
        db,
        company_id=company_id,
        user_id=user_id,
        analysis_type="mean_median",
        parameters={
            "variable_id": variable.id,
            "variable_name": variable.name,
            "observations": len(values),
        },
        dataset_id=dataset.id,
        results=[
            {
                "metric_name": "count",
                "numeric_result": float(len(values)),
                "result_payload": {},
            },
            {
                "metric_name": "mean",
                "numeric_result": mean,
                "result_payload": {
                    "formula": "suma de valores / cantidad de valores",
                },
            },
            {
                "metric_name": "median",
                "numeric_result": median,
                "result_payload": {
                    "formula": "valor central de los datos ordenados",
                },
            },
            {
                "metric_name": "comparison",
                "numeric_result": difference,
                "result_payload": {
                    "relation": relation,
                    "difference": difference,
                    "interpretation": interpretation,
                },
            },
        ],
    )
    return get_analysis(db, company_id, analysis.id)


# ---------------------------------------------------------------
# Variables aleatorias
# ---------------------------------------------------------------
def _distribution_stats(
    distribution: str, parameters: dict[str, float]
) -> tuple[float, float, dict]:
    """Esperanza y varianza teóricas de la distribución indicada."""
    try:
        if distribution == "uniforme":
            a = float(parameters["a"])
            b = float(parameters["b"])
            if b <= a:
                raise AnalysisError(
                    "La distribución uniforme requiere b > a"
                )
            expected = (a + b) / 2
            variance = (b - a) ** 2 / 12
            normalized = {"a": a, "b": b}
            formulas = {
                "expected": "E(X) = (a + b) / 2",
                "variance": "Var(X) = (b - a)² / 12",
            }

        elif distribution == "bernoulli":
            p = float(parameters["p"])
            if not 0 <= p <= 1:
                raise AnalysisError("La probabilidad p debe estar entre 0 y 1")
            expected = p
            variance = p * (1 - p)
            normalized = {"p": p}
            formulas = {
                "expected": "E(X) = p",
                "variance": "Var(X) = p · (1 - p)",
            }

        elif distribution == "binomial":
            if "n" not in parameters or "p" not in parameters:
                raise AnalysisError(
                    "La distribución binomial requiere n y p"
                )
            n_float = float(parameters["n"])
            p = float(parameters["p"])
            if n_float != int(n_float) or int(n_float) < 1:
                raise AnalysisError("El número de ensayos n debe ser >= 1")
            if not 0 <= p <= 1:
                raise AnalysisError("La probabilidad p debe estar entre 0 y 1")
            n = int(n_float)
            expected = n * p
            variance = n * p * (1 - p)
            normalized = {"n": float(n), "p": p}
            formulas = {
                "expected": "E(X) = n · p",
                "variance": "Var(X) = n · p · (1 - p)",
            }

        elif distribution == "normal":
            mu = float(parameters["mu"])
            sigma = float(parameters["sigma"])
            if sigma <= 0:
                raise AnalysisError(
                    "La desviación estándar sigma debe ser mayor que cero"
                )
            expected = mu
            variance = sigma**2
            normalized = {"mu": mu, "sigma": sigma}
            formulas = {
                "expected": "E(X) = μ",
                "variance": "Var(X) = σ²",
            }

        else:  # pragma: no cover - el schema ya restringe el patrón
            raise AnalysisError(
                f"Distribución no soportada: {distribution}"
            )
    except (KeyError, TypeError, ValueError) as error:
        raise AnalysisError(
            f"Parámetros inválidos para la distribución {distribution}: {error}"
        ) from error

    return expected, variance, {"parameters": normalized, "formulas": formulas}


def run_random_variable(
    db: Session,
    company_id: int,
    user_id: int,
    variable_id: int,
    distribution: str,
    parameters: dict[str, float],
) -> StatisticalAnalysis:
    """Analiza una variable aleatoria: esperanza, varianza y desviación."""
    dataset, variable = _get_numeric_variable(db, company_id, variable_id)

    expected, variance, extra = _distribution_stats(distribution, parameters)
    std_dev = _round(math.sqrt(variance))

    results = [
        {
            "metric_name": "expected_value",
            "numeric_result": _round(expected),
            "result_payload": {"formula": extra["formulas"]["expected"]},
        },
        {
            "metric_name": "variance",
            "numeric_result": _round(variance),
            "result_payload": {"formula": extra["formulas"]["variance"]},
        },
        {
            "metric_name": "std_dev",
            "numeric_result": std_dev,
            "result_payload": {"formula": "σ = √Var(X)"},
        },
    ]

    # Comparación con la media empírica de las observaciones (si existen)
    observed = dataset_service.numeric_values(db, dataset.id, variable.id)
    if observed:
        empirical_mean = _round(statistics.mean(observed))
        results.append(
            {
                "metric_name": "empirical_mean",
                "numeric_result": empirical_mean,
                "result_payload": {
                    "difference": _round(empirical_mean - expected),
                    "observations": len(observed),
                },
            }
        )

    analysis = _register_analysis(
        db,
        company_id=company_id,
        user_id=user_id,
        analysis_type="random_variable",
        parameters={
            "variable_id": variable.id,
            "variable_name": variable.name,
            "distribution": distribution,
            "distribution_parameters": extra["parameters"],
        },
        dataset_id=dataset.id,
        results=results,
    )

    # La definición de la variable aleatoria también queda almacenada
    db.add(
        RandomVariable(
            dataset_id=dataset.id,
            variable_id=variable.id,
            distribution_name=distribution,
            parameters=extra["parameters"],
            created_at=_now(),
        )
    )
    db.commit()

    return get_analysis(db, company_id, analysis.id)


# ---------------------------------------------------------------
# Probabilidades
# ---------------------------------------------------------------
def run_probability(
    db: Session,
    company_id: int,
    user_id: int,
    payload: ProbabilityInput,
) -> StatisticalAnalysis:
    """P(A|B), P(B|A) e independencia de dos eventos."""
    p_a, p_b, p_ab = payload.p_a, payload.p_b, payload.p_a_and_b

    if p_a <= 0 or p_b <= 0:
        raise AnalysisError(
            "P(A) y P(B) deben ser mayores que cero para calcular "
            "probabilidades condicionales"
        )

    if p_ab > min(p_a, p_b) + TOLERANCE:
        raise AnalysisError(
            "P(A ∩ B) no puede ser mayor que P(A) ni que P(B)"
        )

    p_b_given_a = _round(p_ab / p_a)
    p_a_given_b = _round(p_ab / p_b)
    product = _round(p_a * p_b)
    difference = _round(p_ab - product)
    independent = abs(p_ab - product) <= TOLERANCE

    interpretation = (
        "P(A ∩ B) coincide con P(A)·P(B): los eventos A y B son "
        "independientes."
        if independent
        else (
            "P(A ∩ B) difiere de P(A)·P(B): los eventos A y B "
            "no son independientes."
        )
    )

    analysis = _register_analysis(
        db,
        company_id=company_id,
        user_id=user_id,
        analysis_type="probability",
        parameters={
            "p_a": p_a,
            "p_b": p_b,
            "p_a_and_b": p_ab,
        },
        dataset_id=None,
        results=[
            {
                "metric_name": "p_a_given_b",
                "numeric_result": p_a_given_b,
                "result_payload": {"formula": "P(A|B) = P(A ∩ B) / P(B)"},
            },
            {
                "metric_name": "p_b_given_a",
                "numeric_result": p_b_given_a,
                "result_payload": {"formula": "P(B|A) = P(A ∩ B) / P(A)"},
            },
            {
                "metric_name": "independence",
                "numeric_result": difference,
                "result_payload": {
                    "independent": independent,
                    "p_a_times_p_b": product,
                    "difference": difference,
                    "interpretation": interpretation,
                },
            },
        ],
    )
    return get_analysis(db, company_id, analysis.id)


# ---------------------------------------------------------------
# Teorema de Bayes
# ---------------------------------------------------------------
def run_bayes(
    db: Session,
    company_id: int,
    user_id: int,
    payload: BayesInput,
) -> StatisticalAnalysis:
    """Posterior P(A|B) = P(A)·P(B|A) / P(B), reproducible."""
    p_a = payload.probability_a
    p_b_given_a = payload.probability_b_given_a
    p_b_computed = False

    if payload.probability_b is not None:
        p_b = payload.probability_b
    elif payload.probability_b_given_not_a is not None:
        # Ley de probabilidad total:
        # P(B) = P(B|A)·P(A) + P(B|¬A)·P(¬A)
        p_b = p_b_given_a * p_a + payload.probability_b_given_not_a * (
            1 - p_a
        )
        p_b_computed = True
    else:
        raise AnalysisError(
            "Indica P(B) o P(B|¬A) para calcular la probabilidad total"
        )

    if p_b <= 0:
        raise AnalysisError("P(B) debe ser mayor que cero")

    posterior = p_a * p_b_given_a / p_b

    if posterior > 1 + TOLERANCE:
        raise AnalysisError(
            "Probabilidades inconsistentes: P(B) no puede ser menor "
            "que P(A)·P(B|A)"
        )

    posterior = min(posterior, 1.0)
    p_b_rounded = _round(p_b)
    posterior_rounded = _round(posterior)

    explanation = (
        f"P(A|B) = [P(A) · P(B|A)] / P(B) = "
        f"[{_round(p_a)} · {_round(p_b_given_a)}] / {p_b_rounded} = "
        f"{posterior_rounded}"
    )
    if p_b_computed:
        explanation += (
            " · P(B) calculada con la ley de probabilidad total: "
            "P(B) = P(B|A)·P(A) + P(B|¬A)·P(¬A)"
        )

    analysis = _register_analysis(
        db,
        company_id=company_id,
        user_id=user_id,
        analysis_type="bayes",
        parameters={
            "probability_a": p_a,
            "probability_b_given_a": p_b_given_a,
            "probability_b": p_b_rounded,
            "probability_b_given_not_a": payload.probability_b_given_not_a,
            "p_b_computed": p_b_computed,
        },
        dataset_id=None,
        results=[
            {
                "metric_name": "posterior_probability",
                "numeric_result": posterior_rounded,
                "result_payload": {
                    "formula": "P(A|B) = P(A)·P(B|A) / P(B)",
                    "explanation": explanation,
                },
            },
            {
                "metric_name": "marginal_probability",
                "numeric_result": p_b_rounded,
                "result_payload": {
                    "computed_from_complement": p_b_computed,
                },
            },
        ],
    )

    db.add(
        BayesAnalysis(
            analysis_id=analysis.id,
            probability_a=p_a,
            probability_b_given_a=p_b_given_a,
            probability_b=p_b_rounded,
            posterior_probability=posterior_rounded,
            explanation=explanation,
            created_at=_now(),
        )
    )
    db.commit()

    return get_analysis(db, company_id, analysis.id)


# ---------------------------------------------------------------
# Historial de análisis
# ---------------------------------------------------------------
def _result_dict(result: StatisticalResult) -> dict:
    return {
        "id": result.id,
        "metric_name": result.metric_name,
        "numeric_result": result.numeric_result,
        "result_payload": result.result_payload or {},
    }


def _analysis_dict(
    analysis: StatisticalAnalysis,
    *,
    dataset_name: str | None,
    results: list[StatisticalResult],
    bayes: BayesAnalysis | None,
) -> dict:
    return {
        "id": analysis.id,
        "analysis_type": analysis.analysis_type,
        "dataset_id": analysis.dataset_id,
        "dataset_name": dataset_name,
        "status": analysis.status,
        "parameters": analysis.parameters or {},
        "created_at": analysis.created_at,
        "results": [_result_dict(item) for item in results],
        "bayes": (
            {
                "probability_a": bayes.probability_a,
                "probability_b_given_a": bayes.probability_b_given_a,
                "probability_b": bayes.probability_b,
                "posterior_probability": bayes.posterior_probability,
                "explanation": bayes.explanation,
            }
            if bayes is not None
            else None
        ),
    }


def _load_results(
    db: Session, analysis_ids: list[int]
) -> dict[int, list[StatisticalResult]]:
    if not analysis_ids:
        return {}

    rows = (
        db.execute(
            select(StatisticalResult)
            .where(StatisticalResult.analysis_id.in_(analysis_ids))
            .order_by(StatisticalResult.id)
        )
        .scalars()
        .all()
    )
    grouped: dict[int, list[StatisticalResult]] = {}
    for row in rows:
        grouped.setdefault(row.analysis_id, []).append(row)
    return grouped


def _load_bayes(
    db: Session, analysis_ids: list[int]
) -> dict[int, BayesAnalysis]:
    if not analysis_ids:
        return {}

    rows = (
        db.execute(
            select(BayesAnalysis).where(
                BayesAnalysis.analysis_id.in_(analysis_ids)
            )
        )
        .scalars()
        .all()
    )
    return {row.analysis_id: row for row in rows}


def list_analyses(
    db: Session,
    company_id: int,
    *,
    analysis_type: str | None = None,
    dataset_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    filters = [StatisticalAnalysis.company_id == company_id]

    if analysis_type:
        filters.append(StatisticalAnalysis.analysis_type == analysis_type)
    if dataset_id is not None:
        filters.append(StatisticalAnalysis.dataset_id == dataset_id)

    total = db.execute(
        select(func.count())
        .select_from(StatisticalAnalysis)
        .where(*filters)
    ).scalar_one()

    rows = (
        db.execute(
            select(StatisticalAnalysis)
            .where(*filters)
            .order_by(
                StatisticalAnalysis.created_at.desc(),
                StatisticalAnalysis.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )

    analysis_ids = [row.id for row in rows]
    results_by_analysis = _load_results(db, analysis_ids)
    bayes_by_analysis = _load_bayes(db, analysis_ids)
    dataset_ids = {row.dataset_id for row in rows if row.dataset_id}
    names = dataset_names(db, company_id, dataset_ids)

    items = [
        _analysis_dict(
            row,
            dataset_name=names.get(row.dataset_id) if row.dataset_id else None,
            results=results_by_analysis.get(row.id, []),
            bayes=bayes_by_analysis.get(row.id),
        )
        for row in rows
    ]
    return items, total


def get_analysis(
    db: Session, company_id: int, analysis_id: int
) -> dict:
    analysis = db.execute(
        select(StatisticalAnalysis).where(
            StatisticalAnalysis.id == analysis_id,
            StatisticalAnalysis.company_id == company_id,
        )
    ).scalar_one_or_none()

    if analysis is None:
        raise AnalysisError(f"El análisis {analysis_id} no existe")

    dataset_name = None
    if analysis.dataset_id:
        names = dataset_names(db, company_id, {analysis.dataset_id})
        dataset_name = names.get(analysis.dataset_id)

    return _analysis_dict(
        analysis,
        dataset_name=dataset_name,
        results=_load_results(db, [analysis.id]).get(analysis.id, []),
        bayes=_load_bayes(db, [analysis.id]).get(analysis.id),
    )


def dataset_names(
    db: Session, company_id: int, dataset_ids: set[int]
) -> dict[int, str]:
    if not dataset_ids:
        return {}
    rows = db.execute(
        select(Dataset.id, Dataset.name).where(
            Dataset.id.in_(dataset_ids),
            Dataset.company_id == company_id,
        )
    ).all()
    return {dataset_id: name for dataset_id, name in rows}
