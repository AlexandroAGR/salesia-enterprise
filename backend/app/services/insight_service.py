"""Motor de insights empresariales – Fase 11.

Reglas deterministas y explicables sobre los datos del sistema:

 - 8 reglas sobre ventas (reutilizan el motor de analytics de la Fase 10)
 - 4 reglas sobre análisis estadísticos (resultados de la Fase 09)

Cada observación guarda en `evidence` los números que la originaron y se
deduplica con una huella (fingerprint) calculada sobre la regla, el
análisis y esa evidencia: repetir la generación sin cambiar los datos no
crea observaciones duplicadas, y cambiar los datos sí deja rastro nuevo
en el historial.
"""

import hashlib
import json
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.insight import Insight
from app.models.sale import Sale
from app.models.statistical_analysis import StatisticalAnalysis
from app.models.statistical_result import StatisticalResult
from app.schemas.insight import GenerateIn
from app.services import analytics_service, stats_service

# Ventana por defecto de las reglas de ventas (días, fecha UTC)
DEFAULT_WINDOW_DAYS = 7

# Límite de desglose usado al calcular concentraciones (máx. de la API)
BREAKDOWN_LIMIT = 25

SEVERITY_INFO = "info"
SEVERITY_POSITIVE = "positive"
SEVERITY_WARNING = "warning"

# Catálogo de reglas: código → metadatos (el orden define la salida)
RULES: dict[str, dict[str, str]] = {
    "revenue_trend": {
        "name": "Tendencia de ingresos",
        "source": "ventas",
        "description": (
            "Compara los ingresos del periodo con los del periodo "
            "inmediatamente anterior."
        ),
    },
    "category_concentration": {
        "name": "Concentración por categoría",
        "source": "ventas",
        "description": (
            "Una categoría concentra el 50% o más de los ingresos "
            "del periodo."
        ),
    },
    "product_concentration": {
        "name": "Concentración por producto",
        "source": "ventas",
        "description": (
            "Un producto concentra el 40% o más de los ingresos "
            "del periodo."
        ),
    },
    "top_seller": {
        "name": "Vendedor destacado",
        "source": "ventas",
        "description": (
            "Identifica al vendedor con más ingresos cuando hay "
            "dos o más con ventas."
        ),
    },
    "ticket_skew": {
        "name": "Sesgo del ticket promedio",
        "source": "ventas",
        "description": (
            "La media del ticket se aleja de la mediana: ventas "
            "puntuales elevan o deprimen el promedio."
        ),
    },
    "high_dispersion": {
        "name": "Alta dispersión de importes",
        "source": "ventas",
        "description": (
            "El coeficiente de variación de los importes de venta "
            "supera 1."
        ),
    },
    "pending_sales": {
        "name": "Ventas pendientes",
        "source": "ventas",
        "description": (
            "Existen ventas en estado pendiente de cobro o entrega."
        ),
    },
    "cancellation_rate": {
        "name": "Tasa de cancelación",
        "source": "ventas",
        "description": (
            "El 20% o más de las ventas registradas están canceladas "
            "o reembolsadas."
        ),
    },
    "mean_median_skew": {
        "name": "Sesgo media/mediana",
        "source": "analisis",
        "description": (
            "La media y la mediana de un análisis no coinciden."
        ),
    },
    "random_variable_expected": {
        "name": "Valor esperado de la variable",
        "source": "analisis",
        "description": (
            "Esperanza, varianza y desviación estándar de la variable "
            "aleatoria analizada."
        ),
    },
    "probability_independence": {
        "name": "Dependencia de eventos",
        "source": "analisis",
        "description": (
            "Compara P(A|B) con P(A) para verificar si los eventos "
            "son independientes."
        ),
    },
    "bayes_posterior": {
        "name": "Posterior de Bayes",
        "source": "analisis",
        "description": (
            "Probabilidad condicionada P(A|B) calculada con el "
            "teorema de Bayes."
        ),
    },
}


class InsightError(Exception):
    """Error controlado del motor de insights."""


def _round(value: float, digits: int = 2) -> float:
    return round(value, digits)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _fingerprint(
    rule_code: str, analysis_id: int | None, evidence: dict
) -> str:
    """Huella estable de una observación (regla + análisis + evidencia)."""
    canonical = json.dumps(
        {"rule": rule_code, "analysis": analysis_id, "evidence": evidence},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _candidate(
    rule_code: str,
    *,
    title: str,
    description: str,
    severity: str,
    evidence: dict,
    analysis_id: int | None = None,
    dataset_id: int | None = None,
) -> dict:
    return {
        "rule_code": rule_code,
        "title": title[:180],
        "description": description,
        "severity": severity,
        "evidence": evidence,
        "analysis_id": analysis_id,
        "dataset_id": dataset_id,
    }


def _resolve_scope(payload: GenerateIn | None) -> dict:
    """Ámbito de las reglas de ventas (por defecto: últimos 7 días)."""
    if payload is None:
        payload = GenerateIn()

    date_from = payload.date_from
    date_to = payload.date_to

    if date_from is None and date_to is None:
        if payload.period in {"7", "30", "90"}:
            date_to = _today()
            date_from = date_to - timedelta(days=int(payload.period) - 1)
        elif payload.period != "all":
            date_to = _today()
            date_from = date_to - timedelta(days=DEFAULT_WINDOW_DAYS - 1)
        # period == "all" → histórico completo (sin fechas)
    else:
        if date_to is None:
            date_to = _today()
        if date_from is None:
            date_from = date_to - timedelta(days=DEFAULT_WINDOW_DAYS - 1)

    if date_from is not None and date_to is not None and date_from > date_to:
        raise InsightError(
            "El rango de fechas es inválido: la fecha inicial "
            "es posterior a la final"
        )

    return {
        "date_from": date_from,
        "date_to": date_to,
        "seller_id": payload.seller_id,
        "category_id": payload.category_id,
    }


def _scope_evidence(scope: dict) -> dict:
    """Evidencia del ámbito: fechas ISO (o null) y filtros opcionales."""
    date_from: date | None = scope["date_from"]
    date_to: date | None = scope["date_to"]
    return {
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None,
        "seller_id": scope["seller_id"],
        "category_id": scope["category_id"],
    }


# ---------------------------------------------------------------
# Reglas sobre ventas
# ---------------------------------------------------------------
def _sales_candidates(db: Session, company_id: int, scope: dict) -> list[dict]:
    """Ejecuta las 8 reglas de ventas con el ámbito indicado."""
    summary = analytics_service.sales_summary(
        db,
        company_id,
        date_from=scope["date_from"],
        date_to=scope["date_to"],
        seller_id=scope["seller_id"],
        category_id=scope["category_id"],
    )
    kpis = summary["kpis"]
    stats = summary["statistics"]
    base = _scope_evidence(scope)
    total = kpis["revenue"]
    window = ""
    if scope["date_from"] and scope["date_to"]:
        window = (
            f" del {scope['date_from'].isoformat()}"
            f" al {scope['date_to'].isoformat()}"
        )

    candidates: list[dict] = []

    # 1) Tendencia de ingresos vs periodo inmediatamente anterior
    previous = summary["previous_period"]
    if previous is not None and previous["revenue"] > 0:
        change = previous["revenue_change_pct"] or 0.0
        if change >= 10:
            severity = SEVERITY_POSITIVE
            title = (
                f"Los ingresos crecieron {abs(change):.1f}% "
                "frente al periodo anterior"
            )
        elif change <= -10:
            severity = SEVERITY_WARNING
            title = (
                f"Los ingresos cayeron {abs(change):.1f}% "
                "frente al periodo anterior"
            )
        else:
            severity = SEVERITY_INFO
            title = (
                f"Ingresos estables ({change:+.1f}%) "
                "frente al periodo anterior"
            )
        candidates.append(
            _candidate(
                "revenue_trend",
                title=title,
                description=(
                    f"Se facturaron S/ {total:.2f} frente a "
                    f"S/ {previous['revenue']:.2f} en el periodo "
                    f"inmediatamente anterior{window} ({change:+.1f}%)."
                ),
                severity=severity,
                evidence={
                    **base,
                    "revenue": total,
                    "previous_revenue": previous["revenue"],
                    "change_pct": change,
                },
            )
        )

    # 2-4) Concentraciones por categoría/producto y vendedor destacado
    concentration_specs = (
        # regla, group_by, umbral (None = sin umbral), singular, plural
        (
            "category_concentration",
            "category",
            0.50,
            "categoría",
            "categorías",
        ),
        (
            "product_concentration",
            "product",
            0.40,
            "producto",
            "productos",
        ),
        (
            "top_seller",
            "seller",
            None,
            "vendedor",
            "vendedores",
        ),
    )
    for rule_code, group_by, threshold, singular, plural in concentration_specs:
        items = analytics_service.sales_breakdown(
            db,
            company_id,
            group_by=group_by,
            date_from=scope["date_from"],
            date_to=scope["date_to"],
            seller_id=scope["seller_id"],
            category_id=scope["category_id"],
            limit=BREAKDOWN_LIMIT,
        )["items"]
        if len(items) < 2:
            continue

        top = items[0]
        share = (top["revenue"] / total) if total else 0.0
        if threshold is not None and share < threshold:
            continue

        share_pct = _round(share * 100)
        description = (
            f"Facturó S/ {top['revenue']:.2f} de S/ {total:.2f} entre "
            f"{len(items)} {plural}{window}."
        )
        if threshold is not None:
            description += (
                f" Supera el umbral de concentración del "
                f"{threshold * 100:.0f}%."
            )
        candidates.append(
            _candidate(
                rule_code,
                title=(
                    f"«{top['label']}» concentra {share_pct:.0f}% "
                    f"de los ingresos por {singular}"
                ),
                description=description,
                severity=(
                    SEVERITY_WARNING
                    if threshold is not None
                    else SEVERITY_INFO
                ),
                evidence={
                    **base,
                    group_by: top["label"],
                    "revenue": top["revenue"],
                    "total_revenue": total,
                    "share_pct": share_pct,
                    "groups_count": len(items),
                },
            )
        )

    # 5) Sesgo del ticket promedio (media vs mediana)
    count = stats["count"]
    mean = stats["mean"]
    median = stats["median"]
    if count >= 3 and mean is not None and median:
        ratio_raw = mean / median
        if ratio_raw >= 1.2 or ratio_raw <= 0.83:
            if ratio_raw >= 1.2:
                reason = "ventas puntuales elevan el promedio"
            else:
                reason = "ventas pequeñas tiran del promedio"
            candidates.append(
                _candidate(
                    "ticket_skew",
                    title="El ticket promedio se aleja de la mediana",
                    description=(
                        f"La media de S/ {mean:.2f} frente a la mediana "
                        f"de S/ {median:.2f} (ratio {ratio_raw:.2f}) en "
                        f"{count} ventas{window}: {reason}."
                    ),
                    severity=SEVERITY_INFO,
                    evidence={
                        **base,
                        "count": count,
                        "mean": mean,
                        "median": median,
                        "ratio": _round(ratio_raw),
                    },
                )
            )

    # 6) Alta dispersión de los importes de venta
    stddev = stats["stddev"]
    if count >= 2 and mean and stddev is not None:
        cv_raw = stddev / mean
        if cv_raw >= 1:
            candidates.append(
                _candidate(
                    "high_dispersion",
                    title="Alta dispersión en los importes de venta",
                    description=(
                        f"Coeficiente de variación {cv_raw:.2f} "
                        f"(desviación S/ {stddev:.2f} sobre media "
                        f"S/ {mean:.2f}) en {count} ventas{window}."
                    ),
                    severity=SEVERITY_WARNING,
                    evidence={
                        **base,
                        "count": count,
                        "mean": mean,
                        "stddev": stddev,
                        "cv": _round(cv_raw),
                    },
                )
            )

    # 7) Ventas pendientes (ámbito de la empresa, sin ventana)
    pending = db.execute(
        select(Sale.total_amount).where(
            Sale.company_id == company_id,
            Sale.status == "pending",
        )
    ).scalars().all()
    if pending:
        pending_total = _round(float(sum(pending)))
        if len(pending) == 1:
            pending_title = "1 venta pendiente de cobro o entrega"
        else:
            pending_title = (
                f"{len(pending)} ventas pendientes de cobro o entrega"
            )
        candidates.append(
            _candidate(
                "pending_sales",
                title=pending_title,
                description=(
                    f"Suman S/ {pending_total:.2f} en estado pendiente; "
                    "revisa los cobros y las entregas."
                ),
                severity=SEVERITY_WARNING,
                evidence={"count": len(pending), "total_amount": pending_total},
            )
        )

    # 8) Tasa de cancelación/reembolso (ámbito de la empresa)
    statuses = db.execute(
        select(Sale.status).where(Sale.company_id == company_id)
    ).scalars().all()
    total_sales = len(statuses)
    cancelled = statuses.count("cancelled")
    refunded = statuses.count("refunded")
    excluded = cancelled + refunded
    if total_sales >= 5 and excluded and excluded / total_sales >= 0.20:
        rate = _round(excluded / total_sales * 100)
        candidates.append(
            _candidate(
                "cancellation_rate",
                title=f"Tasa de cancelación del {rate:.1f}%",
                description=(
                    f"{excluded} de {total_sales} ventas están canceladas "
                    f"o reembolsadas ({cancelled} canceladas y "
                    f"{refunded} reembolsadas)."
                ),
                severity=SEVERITY_WARNING,
                evidence={
                    "total": total_sales,
                    "cancelled": cancelled,
                    "refunded": refunded,
                    "rate_pct": rate,
                },
            )
        )

    return candidates


# ---------------------------------------------------------------
# Reglas sobre análisis estadísticos
# ---------------------------------------------------------------
def _metrics_by_name(
    db: Session, analysis_ids: list[int]
) -> dict[int, dict[str, StatisticalResult]]:
    """Resultados guardados agrupados por análisis y nombre de métrica."""
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
    grouped: dict[int, dict[str, StatisticalResult]] = {}
    for row in rows:
        grouped.setdefault(row.analysis_id, {})[row.metric_name] = row
    return grouped


def _analysis_candidate(
    analysis: StatisticalAnalysis,
    found: dict[str, StatisticalResult],
) -> dict | None:
    """Traduce un análisis completado en su observación (si aplica)."""
    params = analysis.parameters or {}
    analysis_id = analysis.id
    dataset_id = analysis.dataset_id

    def _number(metric: str) -> float | None:
        row = found.get(metric)
        return row.numeric_result if row is not None else None

    if analysis.analysis_type == "mean_median":
        needed = ("count", "mean", "median", "comparison")
        if any(metric not in found for metric in needed):
            return None
        relation = (found["comparison"].result_payload or {}).get("relation")
        if relation not in {"media_mayor_mediana", "media_menor_mediana"}:
            return None
        count = int(_number("count") or 0)
        mean = _number("mean")
        median = _number("median")
        variable = params.get("variable_name") or "la variable"
        if relation == "media_mayor_mediana":
            title = f"La media supera a la mediana en «{variable}»"
            reason = "valores altos puntuales elevan el promedio"
        else:
            title = f"La media queda por debajo de la mediana en «{variable}»"
            reason = "valores bajos puntuales deprimen el promedio"
        return _candidate(
            "mean_median_skew",
            title=title,
            description=(
                f"Media {mean:.2f} frente a mediana {median:.2f} en "
                f"{count} observaciones: {reason}."
            ),
            severity=SEVERITY_INFO,
            evidence={
                "variable": variable,
                "count": count,
                "mean": mean,
                "median": median,
                "relation": relation,
            },
            analysis_id=analysis_id,
            dataset_id=dataset_id,
        )

    if analysis.analysis_type == "random_variable":
        needed = ("expected_value", "variance", "std_dev")
        if any(metric not in found for metric in needed):
            return None
        expected = _number("expected_value")
        variance = _number("variance")
        std_dev = _number("std_dev")
        variable = params.get("variable_name") or "la variable"
        distribution = params.get("distribution") or "desconocida"
        evidence = {
            "variable": variable,
            "distribution": distribution,
            "expected_value": expected,
            "variance": variance,
            "std_dev": std_dev,
        }
        description = (
            f"Distribución {distribution}: E(X) = {expected:.2f}, "
            f"Var(X) = {variance:.2f}, σ = {std_dev:.2f}."
        )
        empirical = _number("empirical_mean")
        if empirical is not None:
            evidence["empirical_mean"] = empirical
            description += f" Media observada: {empirical:.2f}."
        return _candidate(
            "random_variable_expected",
            title=f"Valor esperado de «{variable}»: {expected:.2f}",
            description=description,
            severity=SEVERITY_INFO,
            evidence=evidence,
            analysis_id=analysis_id,
            dataset_id=dataset_id,
        )

    if analysis.analysis_type == "probability":
        needed = ("p_a_given_b", "p_b_given_a", "independence")
        if any(metric not in found for metric in needed):
            return None
        independent = bool(
            (found["independence"].result_payload or {}).get("independent")
        )
        p_a = params.get("p_a")
        p_b = params.get("p_b")
        p_a_given_b = _number("p_a_given_b")
        p_b_given_a = _number("p_b_given_a")
        difference = _number("independence")
        evidence = {
            "p_a": p_a,
            "p_b": p_b,
            "p_a_given_b": p_a_given_b,
            "p_b_given_a": p_b_given_a,
            "independent": independent,
            "difference": difference,
        }
        if independent:
            return _candidate(
                "probability_independence",
                title="Los eventos A y B son independientes",
                description=(
                    f"P(A|B) = {p_a_given_b:.4f} ≈ P(A) = {p_a:.4f}: "
                    "conocer B no modifica la probabilidad de A."
                ),
                severity=SEVERITY_INFO,
                evidence=evidence,
                analysis_id=analysis_id,
                dataset_id=dataset_id,
            )
        return _candidate(
            "probability_independence",
            title="Los eventos A y B no son independientes",
            description=(
                f"P(A|B) = {p_a_given_b:.4f} frente a P(A) = {p_a:.4f} "
                f"(diferencia {difference:.4f}): no asumas independencia "
                "al interpretar."
            ),
            severity=SEVERITY_WARNING,
            evidence=evidence,
            analysis_id=analysis_id,
            dataset_id=dataset_id,
        )

    if analysis.analysis_type == "bayes":
        needed = ("posterior_probability", "marginal_probability")
        if any(metric not in found for metric in needed):
            return None
        prior = params.get("probability_a")
        likelihood = params.get("probability_b_given_a")
        marginal = _number("marginal_probability")
        posterior = _number("posterior_probability")
        if posterior > prior:
            movement = "aumenta"
        elif posterior < prior:
            movement = "reduce"
        else:
            movement = "mantiene"
        return _candidate(
            "bayes_posterior",
            title=f"Posterior P(A|B) = {posterior:.4f}",
            description=(
                f"P(A) = {prior:.4f}, P(B|A) = {likelihood:.4f} y "
                f"P(B) = {marginal:.4f} → P(A|B) = {posterior:.4f}: "
                f"el evento B {movement} la probabilidad de A."
            ),
            severity=SEVERITY_INFO,
            evidence={
                "probability_a": prior,
                "probability_b_given_a": likelihood,
                "probability_b": marginal,
                "posterior_probability": posterior,
            },
            analysis_id=analysis_id,
            dataset_id=dataset_id,
        )

    return None


def _analysis_candidates(db: Session, company_id: int) -> list[dict]:
    analyses = (
        db.execute(
            select(StatisticalAnalysis)
            .where(
                StatisticalAnalysis.company_id == company_id,
                StatisticalAnalysis.status == "completed",
            )
            .order_by(StatisticalAnalysis.id)
        )
        .scalars()
        .all()
    )
    if not analyses:
        return []

    metrics = _metrics_by_name(db, [analysis.id for analysis in analyses])
    candidates = []
    for analysis in analyses:
        candidate = _analysis_candidate(analysis, metrics.get(analysis.id, {}))
        if candidate is not None:
            candidates.append(candidate)
    return candidates


# ---------------------------------------------------------------
# Generación, consulta y catálogo
# ---------------------------------------------------------------
def _enrich(db: Session, company_id: int, rows: list[Insight]) -> list[dict]:
    """Completa cada insight con nombre de regla, análisis y dataset."""
    analysis_ids = {row.analysis_id for row in rows if row.analysis_id}
    analyses: dict[int, StatisticalAnalysis] = {}
    if analysis_ids:
        analyses = {
            analysis.id: analysis
            for analysis in db.execute(
                select(StatisticalAnalysis).where(
                    StatisticalAnalysis.id.in_(analysis_ids),
                    StatisticalAnalysis.company_id == company_id,
                )
            ).scalars()
        }

    dataset_ids: set[int] = {row.dataset_id for row in rows if row.dataset_id}
    for row in rows:
        analysis = analyses.get(row.analysis_id)
        if analysis is not None and analysis.dataset_id is not None:
            dataset_ids.add(analysis.dataset_id)
    names = stats_service.dataset_names(db, company_id, dataset_ids)

    items = []
    for row in rows:
        analysis = analyses.get(row.analysis_id)
        dataset_id = row.dataset_id
        if dataset_id is None and analysis is not None:
            dataset_id = analysis.dataset_id
        items.append(
            {
                "id": row.id,
                "rule_code": row.rule_code,
                "rule_name": RULES[row.rule_code]["name"],
                "title": row.title,
                "description": row.description,
                "severity": row.severity,
                "evidence": row.evidence,
                "analysis_id": row.analysis_id,
                "analysis_type": (
                    analysis.analysis_type if analysis is not None else None
                ),
                "dataset_id": dataset_id,
                "dataset_name": names.get(dataset_id),
                "created_at": row.created_at,
            }
        )
    return items


def generate(
    db: Session,
    company_id: int,
    payload: GenerateIn | None = None,
) -> dict:
    """Ejecuta todas las reglas y persiste solo los insights nuevos."""
    scope = _resolve_scope(payload)
    candidates = _sales_candidates(db, company_id, scope)
    candidates += _analysis_candidates(db, company_id)

    existing = set(
        db.execute(
            select(Insight.fingerprint).where(
                Insight.company_id == company_id
            )
        ).scalars()
    )

    created: list[Insight] = []
    skipped = 0
    now = _now()
    for item in candidates:
        fingerprint = _fingerprint(
            item["rule_code"], item["analysis_id"], item["evidence"]
        )
        if fingerprint in existing:
            skipped += 1
            continue

        insight = Insight(
            company_id=company_id,
            analysis_id=item["analysis_id"],
            dataset_id=item["dataset_id"],
            rule_code=item["rule_code"],
            fingerprint=fingerprint,
            title=item["title"],
            description=item["description"],
            severity=item["severity"],
            evidence=item["evidence"],
            created_at=now,
        )
        try:
            # Savepoint: una carrera con la restricción única (company_id,
            # fingerprint) revierte solo esta fila y se cuenta como omitida.
            with db.begin_nested():
                db.add(insight)
                db.flush()
        except IntegrityError:
            skipped += 1
            continue

        existing.add(fingerprint)
        created.append(insight)

    db.commit()
    return {"created": _enrich(db, company_id, created), "skipped": skipped}


def list_insights(
    db: Session,
    company_id: int,
    *,
    rule_code: str | None = None,
    severity: str | None = None,
    analysis_id: int | None = None,
    dataset_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """Histórico paginado de la empresa con filtros opcionales."""
    filters = [Insight.company_id == company_id]

    if rule_code is not None:
        if rule_code not in RULES:
            raise InsightError(f"La regla '{rule_code}' no existe")
        filters.append(Insight.rule_code == rule_code)
    if severity is not None:
        filters.append(Insight.severity == severity)
    if analysis_id is not None:
        filters.append(Insight.analysis_id == analysis_id)
    if dataset_id is not None:
        filters.append(Insight.dataset_id == dataset_id)

    total = db.execute(
        select(func.count()).select_from(Insight).where(*filters)
    ).scalar_one()

    rows = (
        db.execute(
            select(Insight)
            .where(*filters)
            .order_by(Insight.created_at.desc(), Insight.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return _enrich(db, company_id, list(rows)), total


def rules_catalog() -> list[dict]:
    """Catálogo de reglas disponibles (código, nombre y fuente)."""
    return [
        {
            "code": code,
            "name": meta["name"],
            "description": meta["description"],
            "source": meta["source"],
        }
        for code, meta in RULES.items()
    ]
