"""Fase 14 – Pruebas unitarias del motor estadístico.

Media, mediana, Bayes, probabilidades, distribuciones y validadores
de entrada. Ejecutan los services directamente sobre la BD temporal
de pytest (ver conftest.py).
"""

from __future__ import annotations

import math
import statistics

import pytest
from pydantic import ValidationError

from app.schemas.analysis import BayesInput, ProbabilityInput
from app.schemas.customer import CustomerCreate
from app.schemas.sale import SaleCreate, SaleItemInput
from app.services import stats_service
from app.services.analytics_service import _descriptive_stats
from app.services.stats_service import (
    AnalysisError,
    _distribution_stats,
    _finite,
    run_bayes,
    run_mean_median,
    run_probability,
)


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
def _make_variable(db, values: list[float]):
    """Crea un dataset con una variable numérica y sus observaciones."""
    from datetime import datetime

    from app.models import Dataset, DatasetVariable, Observation

    now = datetime(2026, 10, 6, 12, 0, 0)
    dataset = Dataset(
        company_id=1,
        name="Ventas 2026",
        source_type="manual",
        description=None,
        created_by=1,
        created_at=now,
    )
    db.add(dataset)
    db.flush()

    variable = DatasetVariable(
        dataset_id=dataset.id,
        name="monto",
        data_type="numeric",
        variable_type="continua",
        description=None,
    )
    db.add(variable)
    db.flush()

    for value in values:
        db.add(
            Observation(
                dataset_id=dataset.id,
                variable_id=variable.id,
                numeric_value=value,
                text_value=None,
                observed_at=None,
                created_at=now,
            )
        )
    db.commit()
    return variable


def _metric(analysis: dict, name: str) -> dict:
    return next(
        item for item in analysis["results"] if item["metric_name"] == name
    )


# ---------------------------------------------------------------
# Utilidades puras
# ---------------------------------------------------------------
def test_finite_rechaza_nan_e_infinito():
    assert _finite(1.5, "x") == 1.5

    with pytest.raises(AnalysisError, match="finito"):
        _finite(math.nan, "x")

    with pytest.raises(AnalysisError, match="finito"):
        _finite(math.inf, "x")


# ---------------------------------------------------------------
# Distribuciones (esperanza y varianza teóricas)
# ---------------------------------------------------------------
def test_distribucion_uniforme():
    expected, variance, extra = _distribution_stats(
        "uniforme", {"a": 2.0, "b": 6.0}
    )
    assert expected == 4.0  # (2 + 6) / 2
    assert variance == pytest.approx(16 / 12)  # (b-a)² / 12
    assert extra["parameters"] == {"a": 2.0, "b": 6.0}


def test_distribucion_uniforme_b_menor_que_a():
    with pytest.raises(AnalysisError, match="b > a"):
        _distribution_stats("uniforme", {"a": 6.0, "b": 2.0})


def test_distribucion_bernoulli():
    expected, variance, _ = _distribution_stats("bernoulli", {"p": 0.3})
    assert expected == 0.3
    assert variance == pytest.approx(0.3 * 0.7)


def test_distribucion_bernoulli_p_fuera_de_rango():
    with pytest.raises(AnalysisError, match="entre 0 y 1"):
        _distribution_stats("bernoulli", {"p": 1.5})

    with pytest.raises(AnalysisError, match="entre 0 y 1"):
        _distribution_stats("bernoulli", {"p": -0.1})


def test_distribucion_binomial():
    expected, variance, _ = _distribution_stats(
        "binomial", {"n": 10.0, "p": 0.5}
    )
    assert expected == 5.0  # n·p
    assert variance == pytest.approx(2.5)  # n·p·(1-p)


def test_distribucion_binomial_n_no_entero():
    with pytest.raises(AnalysisError, match=">= 1"):
        _distribution_stats("binomial", {"n": 2.5, "p": 0.5})


def test_distribucion_normal():
    expected, variance, _ = _distribution_stats(
        "normal", {"mu": 10.0, "sigma": 2.0}
    )
    assert expected == 10.0
    assert variance == 4.0  # σ²


def test_distribucion_normal_sigma_cero():
    with pytest.raises(AnalysisError, match="sigma"):
        _distribution_stats("normal", {"mu": 10.0, "sigma": 0.0})


def test_distribucion_parametro_nan():
    with pytest.raises(AnalysisError, match="finito"):
        _distribution_stats("normal", {"mu": math.nan, "sigma": 1.0})


# ---------------------------------------------------------------
# Media y mediana (sesgo)
# ---------------------------------------------------------------
def test_media_mayor_que_mediana(db):
    variable = _make_variable(db, [1.0, 2.0, 3.0, 100.0])

    analysis = run_mean_median(db, 1, 1, variable.id)

    assert analysis["analysis_type"] == "mean_median"
    assert _metric(analysis, "mean")["numeric_result"] == 26.5
    assert _metric(analysis, "median")["numeric_result"] == 2.5
    comparison = _metric(analysis, "comparison")
    assert (
        comparison["result_payload"]["relation"] == "media_mayor_mediana"
    )
    assert comparison["numeric_result"] == 24.0


def test_media_igual_a_mediana(db):
    variable = _make_variable(db, [1.0, 2.0, 3.0])

    analysis = run_mean_median(db, 1, 1, variable.id)

    assert _metric(analysis, "mean")["numeric_result"] == 2.0
    assert _metric(analysis, "median")["numeric_result"] == 2.0
    assert (
        _metric(analysis, "comparison")["result_payload"]["relation"]
        == "media_igual_mediana"
    )


def test_media_menor_que_mediana(db):
    variable = _make_variable(db, [-100.0, 1.0, 2.0])

    analysis = run_mean_median(db, 1, 1, variable.id)

    assert (
        _metric(analysis, "comparison")["result_payload"]["relation"]
        == "media_menor_mediana"
    )


def test_media_mediana_sin_observaciones(db):
    variable = _make_variable(db, [])

    with pytest.raises(AnalysisError, match="observaciones"):
        run_mean_median(db, 1, 1, variable.id)


# ---------------------------------------------------------------
# Probabilidades condicionales
# ---------------------------------------------------------------
def test_probabilidad_eventos_independientes(db):
    payload = ProbabilityInput(p_a=0.5, p_b=0.4, p_a_and_b=0.2)

    analysis = run_probability(db, 1, 1, payload)

    assert analysis["analysis_type"] == "probability"
    assert _metric(analysis, "p_a_given_b")["numeric_result"] == 0.5
    assert _metric(analysis, "p_b_given_a")["numeric_result"] == 0.4
    independence = _metric(analysis, "independence")
    assert independence["result_payload"]["independent"] is True


def test_probabilidad_eventos_dependientes(db):
    payload = ProbabilityInput(p_a=0.5, p_b=0.4, p_a_and_b=0.1)

    analysis = run_probability(db, 1, 1, payload)

    assert _metric(analysis, "p_b_given_a")["numeric_result"] == 0.2
    independence = _metric(analysis, "independence")
    assert independence["result_payload"]["independent"] is False


def test_probabilidad_interseccion_imposible(db):
    payload = ProbabilityInput(p_a=0.5, p_b=0.4, p_a_and_b=0.6)

    with pytest.raises(AnalysisError, match="no puede ser mayor"):
        run_probability(db, 1, 1, payload)


def test_probabilidad_cero_imposible(db):
    payload = ProbabilityInput(p_a=0.0, p_b=0.4, p_a_and_b=0.0)

    with pytest.raises(AnalysisError, match="mayores que cero"):
        run_probability(db, 1, 1, payload)


# ---------------------------------------------------------------
# Teorema de Bayes
# ---------------------------------------------------------------
def test_bayes_clasico(db):
    # Enfermedad 1%, test sensible 90%, test positivo 10% → 9%
    payload = BayesInput(
        probability_a=0.01,
        probability_b_given_a=0.9,
        probability_b=0.1,
    )

    analysis = run_bayes(db, 1, 1, payload)

    assert analysis["analysis_type"] == "bayes"
    posterior = _metric(analysis, "posterior_probability")
    assert posterior["numeric_result"] == 0.09
    bayes = analysis["bayes"]
    assert bayes["posterior_probability"] == 0.09
    assert "0.09" in bayes["explanation"]


def test_bayes_con_ley_de_probabilidad_total(db):
    # P(B) = P(B|A)·P(A) + P(B|¬A)·P(¬A) = 0.8·0.1 + 0.3·0.9 = 0.35
    payload = BayesInput(
        probability_a=0.1,
        probability_b_given_a=0.8,
        probability_b_given_not_a=0.3,
    )

    analysis = run_bayes(db, 1, 1, payload)

    posterior = _metric(analysis, "posterior_probability")
    assert posterior["numeric_result"] == round(0.08 / 0.35, 6)
    marginal = _metric(analysis, "marginal_probability")
    assert marginal["numeric_result"] == 0.35
    assert marginal["result_payload"]["computed_from_complement"] is True


def test_bayes_sin_probabilidad_total(db):
    payload = BayesInput(probability_a=0.1, probability_b_given_a=0.8)

    with pytest.raises(AnalysisError, match="probabilidad total"):
        run_bayes(db, 1, 1, payload)


def test_bayes_probabilidad_total_cero(db):
    # El esquema rechaza probability_b=0, pero la ley de probabilidad
    # total puede dar P(B)=0 si ambas condicionales son 0.
    payload = BayesInput(
        probability_a=0.1,
        probability_b_given_a=0.0,
        probability_b_given_not_a=0.0,
    )

    with pytest.raises(AnalysisError, match="mayor que cero"):
        run_bayes(db, 1, 1, payload)


def test_bayes_posterior_inconsistente(db):
    # P(B) < P(A)·P(B|A) daría posterior > 1
    payload = BayesInput(
        probability_a=0.9,
        probability_b_given_a=0.9,
        probability_b=0.1,
    )

    with pytest.raises(AnalysisError, match="inconsistentes"):
        run_bayes(db, 1, 1, payload)


# ---------------------------------------------------------------
# Estadística descriptiva (analytics)
# ---------------------------------------------------------------
def test_descriptive_stats_vacio():
    stats = _descriptive_stats([])
    assert stats["count"] == 0
    assert stats["mean"] is None
    assert stats["median"] is None
    assert stats["stddev"] is None


def test_descriptive_stats_valores():
    stats = _descriptive_stats([1.0, 2.0, 3.0, 4.0])
    assert stats["count"] == 4
    assert stats["mean"] == 2.5
    assert stats["median"] == 2.5
    assert stats["min"] == 1.0
    assert stats["max"] == 4.0
    assert stats["stddev"] == round(statistics.pstdev([1, 2, 3, 4]), 2)


# ---------------------------------------------------------------
# Validadores de entrada (pydantic)
# ---------------------------------------------------------------
def test_probability_input_valida():
    payload = ProbabilityInput(p_a=0.5, p_b=0.4, p_a_and_b=0.2)
    assert payload.p_a == 0.5


def test_probability_input_fuera_de_rango():
    with pytest.raises(ValidationError):
        ProbabilityInput(p_a=1.5, p_b=0.4, p_a_and_b=0.2)


def test_bayes_input_probability_a_cero():
    with pytest.raises(ValidationError):
        BayesInput(probability_a=0.0, probability_b_given_a=0.5)


def test_bayes_input_probability_b_mayor_que_uno():
    with pytest.raises(ValidationError):
        BayesInput(
            probability_a=0.5,
            probability_b_given_a=0.5,
            probability_b=1.2,
        )


def test_sale_item_quantity_cero():
    with pytest.raises(ValidationError):
        SaleItemInput(product_id=1, quantity=0)


def test_sale_tax_rate_mayor_que_uno():
    with pytest.raises(ValidationError):
        SaleCreate(
            items=[SaleItemInput(product_id=1, quantity=1)],
            tax_rate=1.5,
        )


def test_sale_sin_items():
    with pytest.raises(ValidationError):
        SaleCreate(items=[])


def test_customer_nombre_corto():
    with pytest.raises(ValidationError):
        CustomerCreate(full_name="A")
