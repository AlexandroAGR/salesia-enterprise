"""Motor de analítica de ventas – Fase 10 (Dashboard Analytics).

Agrega las ventas de la empresa para alimentar el dashboard:

  - KPIs: ingresos, nº de ventas, ticket promedio, clientes y unidades.
  - Estadística descriptiva de los importes: media, mediana, mín/máx y
    desviación típica poblacional.
  - Serie temporal por día, semana o mes con huecos a cero.
  - Desgloses por producto, categoría y vendedor.
  - Distribución de frecuencias (regla de Sturges) para el histograma.
  - Comparación con el periodo inmediatamente anterior.

Reglas de negocio:

  - Sólo se agregan las ventas que NO están canceladas ni reembolsadas.
  - El filtro de categoría incluye la venta si alguna de sus líneas
    pertenece a la categoría; el desglose reparte el total de la venta
    proporcionalmente entre sus líneas, de modo que la suma de los
    desgloses siempre coincide con el ingreso del periodo.
  - Todas las consultas quedan acotadas a la empresa del token.

El agregado se hace en Python sobre las filas filtradas (no en SQL) para
que el comportamiento sea idéntico en PostgreSQL y en el entorno SQLite
de pruebas.
"""

from __future__ import annotations

import math
import statistics
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.product import Product
from app.models.sale import Sale
from app.models.sale_detail import SaleDetail
from app.models.user import User

EXCLUDED_STATUSES = ("cancelled", "refunded")

GRANULARITIES = ("day", "week", "month")
GROUPS = ("product", "category", "seller")


class AnalyticsError(Exception):
    """Error de regla de negocio de la analítica."""


def _round2(value: float) -> float:
    return round(value, 2)


def _start_utc(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=timezone.utc)


def _check_range(date_from: date | None, date_to: date | None) -> None:
    if date_from and date_to and date_from > date_to:
        raise AnalyticsError(
            "El rango de fechas es inválido: la fecha inicial "
            "es posterior a la final"
        )


def _sale_filters(
    company_id: int,
    *,
    date_from: date | None,
    date_to: date | None,
    seller_id: int | None,
    category_id: int | None,
) -> list:
    """Condiciones comunes: empresa, estado, periodo, vendedor y categoría."""
    filters: list = [
        Sale.company_id == company_id,
        Sale.status.notin_(EXCLUDED_STATUSES),
    ]

    if date_from is not None:
        filters.append(Sale.sold_at >= _start_utc(date_from))
    if date_to is not None:
        filters.append(Sale.sold_at < _start_utc(date_to + timedelta(days=1)))
    if seller_id is not None:
        filters.append(Sale.created_by == seller_id)
    if category_id is not None:
        # Venta incluida si alguna línea pertenece a la categoría.
        filters.append(
            Sale.id.in_(
                select(SaleDetail.sale_id)
                .join(Product, SaleDetail.product_id == Product.id)
                .where(
                    Product.category_id == category_id,
                    Product.company_id == company_id,
                )
            )
        )

    return filters


def _load_sales(db: Session, filters: list) -> list[dict]:
    rows = db.execute(
        select(
            Sale.id,
            Sale.sold_at,
            Sale.total_amount,
            Sale.created_by,
            Sale.customer_id,
        )
        .where(*filters)
        .order_by(Sale.id)
    ).all()

    return [
        {
            "id": row.id,
            "sold_at": row.sold_at,
            "total": float(row.total_amount),
            "created_by": row.created_by,
            "customer_id": row.customer_id,
        }
        for row in rows
    ]


# ---------------------------------------------------------------
# Resumen (KPIs + estadística + periodo anterior)
# ---------------------------------------------------------------
def _descriptive_stats(totals: list[float]) -> dict:
    if not totals:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "min": None,
            "max": None,
            "stddev": None,
        }

    return {
        "count": len(totals),
        "mean": _round2(statistics.mean(totals)),
        "median": _round2(statistics.median(totals)),
        "min": _round2(min(totals)),
        "max": _round2(max(totals)),
        "stddev": _round2(statistics.pstdev(totals)),
    }


def _previous_period(
    db: Session,
    company_id: int,
    *,
    date_from: date,
    date_to: date | None,
    seller_id: int | None,
    category_id: int | None,
) -> dict | None:
    """Periodo inmediatamente anterior de la misma duración."""
    end = date_to if date_to is not None else date_from
    span = (end - date_from).days + 1
    prev_end = date_from - timedelta(days=1)
    prev_start = prev_end - timedelta(days=span - 1)

    rows = _load_sales(
        db,
        _sale_filters(
            company_id,
            date_from=prev_start,
            date_to=prev_end,
            seller_id=seller_id,
            category_id=category_id,
        ),
    )
    revenue = _round2(sum(row["total"] for row in rows))

    return {
        "revenue": revenue,
        "sales_count": len(rows),
        "revenue_change_pct": None,
    }


def sales_summary(
    db: Session,
    company_id: int,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    seller_id: int | None = None,
    category_id: int | None = None,
) -> dict:
    """KPIs, estadística descriptiva y comparación con el periodo previo."""
    _check_range(date_from, date_to)

    filters = _sale_filters(
        company_id,
        date_from=date_from,
        date_to=date_to,
        seller_id=seller_id,
        category_id=category_id,
    )
    rows = _load_sales(db, filters)
    totals = [row["total"] for row in rows]

    revenue = _round2(sum(totals))
    count = len(totals)
    avg_ticket = _round2(statistics.mean(totals)) if count else 0.0
    customers_count = len(
        {row["customer_id"] for row in rows if row["customer_id"] is not None}
    )

    items_sold = 0.0
    if count:
        quantities = db.execute(
            select(SaleDetail.quantity)
            .join(Sale, SaleDetail.sale_id == Sale.id)
            .where(*filters)
        ).scalars()
        items_sold = float(sum(quantities.all()))

    previous = None
    if date_from is not None:
        previous = _previous_period(
            db,
            company_id,
            date_from=date_from,
            date_to=date_to,
            seller_id=seller_id,
            category_id=category_id,
        )
        if previous["revenue"] > 0:
            previous["revenue_change_pct"] = _round2(
                (revenue - previous["revenue"]) / previous["revenue"] * 100
            )

    return {
        "filters": {
            "date_from": date_from,
            "date_to": date_to,
            "seller_id": seller_id,
            "category_id": category_id,
        },
        "kpis": {
            "revenue": revenue,
            "sales_count": count,
            "avg_ticket": avg_ticket,
            "customers_count": customers_count,
            "items_sold": _round2(items_sold),
        },
        "statistics": _descriptive_stats(totals),
        "previous_period": previous,
    }


# ---------------------------------------------------------------
# Serie temporal
# ---------------------------------------------------------------
def _bucket_key(day: date, granularity: str) -> str:
    if granularity == "day":
        return day.isoformat()
    if granularity == "week":
        monday = day - timedelta(days=day.isoweekday() - 1)
        return monday.isoformat()
    return f"{day.year:04d}-{day.month:02d}"


def _floor(day: date, granularity: str) -> date:
    if granularity == "week":
        return day - timedelta(days=day.isoweekday() - 1)
    if granularity == "month":
        return day.replace(day=1)
    return day


def _advance(day: date, granularity: str) -> date:
    if granularity == "day":
        return day + timedelta(days=1)
    if granularity == "week":
        return day + timedelta(days=7)
    if day.month == 12:
        return day.replace(year=day.year + 1, month=1)
    return day.replace(month=day.month + 1)


def sales_series(
    db: Session,
    company_id: int,
    *,
    granularity: str = "day",
    date_from: date | None = None,
    date_to: date | None = None,
    seller_id: int | None = None,
    category_id: int | None = None,
) -> dict:
    """Serie de ingresos/ventas por bucket; los periodos sin ventas salen 0."""
    _check_range(date_from, date_to)

    rows = _load_sales(
        db,
        _sale_filters(
            company_id,
            date_from=date_from,
            date_to=date_to,
            seller_id=seller_id,
            category_id=category_id,
        )
    )

    buckets: dict[str, dict] = {}
    for row in rows:
        key = _bucket_key(row["sold_at"].date(), granularity)
        bucket = buckets.setdefault(
            key, {"bucket": key, "sales_count": 0, "revenue": 0.0}
        )
        bucket["sales_count"] += 1
        bucket["revenue"] += row["total"]

    data_dates = [row["sold_at"].date() for row in rows]
    low = date_from or (min(data_dates) if data_dates else None)
    high = date_to or (max(data_dates) if data_dates else None)

    if low is None or high is None:
        ordered = [buckets[key] for key in sorted(buckets)]
    else:
        ordered = []
        cursor = _floor(low, granularity)
        limit = high
        while cursor <= limit:
            key = _bucket_key(cursor, granularity)
            ordered.append(
                buckets.get(
                    key,
                    {"bucket": key, "sales_count": 0, "revenue": 0.0},
                )
            )
            cursor = _advance(cursor, granularity)

    for point in ordered:
        point["revenue"] = _round2(point["revenue"])

    return {"granularity": granularity, "items": ordered}


# ---------------------------------------------------------------
# Desgloses (producto / categoría / vendedor)
# ---------------------------------------------------------------
def _product_lines(db: Session, sale_ids: list[int]) -> list[dict]:
    rows = db.execute(
        select(
            SaleDetail.sale_id,
            SaleDetail.product_id,
            SaleDetail.quantity,
            SaleDetail.line_total,
            Product.name.label("product_name"),
            Product.category_id,
            Category.name.label("category_name"),
        )
        .join(Product, SaleDetail.product_id == Product.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .where(SaleDetail.sale_id.in_(sale_ids))
    ).all()

    return [
        {
            "sale_id": row.sale_id,
            "product_id": row.product_id,
            "quantity": float(row.quantity),
            "line_total": float(row.line_total),
            "product_name": row.product_name,
            "category_id": row.category_id,
            "category_name": row.category_name,
        }
        for row in rows
    ]


def _attribute(sales: list[dict], lines: list[dict]) -> list[dict]:
    """Reparte cada total de venta entre sus líneas por proporción de importe.

    Así los desgloses suman siempre el ingreso del periodo, incluso con
    impuestos o descuentos de cabecera.
    """
    line_sums: dict[int, float] = {}
    for line in lines:
        line_sums[line["sale_id"]] = (
            line_sums.get(line["sale_id"], 0.0) + line["line_total"]
        )

    totals = {sale["id"]: sale["total"] for sale in sales}
    attributed = []
    for line in lines:
        base = line_sums.get(line["sale_id"], 0.0)
        share = (line["line_total"] / base) if base else 0.0
        attributed.append({**line, "revenue": totals[line["sale_id"]] * share})

    return attributed


def sales_breakdown(
    db: Session,
    company_id: int,
    *,
    group_by: str = "product",
    date_from: date | None = None,
    date_to: date | None = None,
    seller_id: int | None = None,
    category_id: int | None = None,
    limit: int = 10,
) -> dict:
    """Desglose de ingresos por producto, categoría o vendedor."""
    _check_range(date_from, date_to)

    filters = _sale_filters(
        company_id,
        date_from=date_from,
        date_to=date_to,
        seller_id=seller_id,
        category_id=category_id,
    )
    sales = _load_sales(db, filters)

    groups: dict = {}

    if group_by == "seller":
        for sale in sales:
            key = sale["created_by"]
            group = groups.setdefault(
                key,
                {"id": key, "label": "", "revenue": 0.0, "sales_count": 0},
            )
            group["revenue"] += sale["total"]
            group["sales_count"] += 1

        known = [key for key in groups if key is not None]
        names: dict = {}
        if known:
            names = dict(
                db.execute(
                    select(User.id, User.full_name).where(User.id.in_(known))
                ).all()
            )
        for key, group in groups.items():
            if key is None:
                group["label"] = "Sin vendedor"
            else:
                group["label"] = names.get(key, f"Usuario {key}")
    else:
        lines = _product_lines(db, [sale["id"] for sale in sales])
        attributed = _attribute(sales, lines)

        for line in attributed:
            if group_by == "product":
                key = line["product_id"]
                label = line["product_name"]
            else:
                key = line["category_id"]
                label = line["category_name"] or "Sin categoría"

            group = groups.setdefault(
                key,
                {
                    "id": key,
                    "label": label,
                    "revenue": 0.0,
                    "sales_count": 0,
                    "quantity": 0.0,
                    "_sales": set(),
                },
            )
            group["revenue"] += line["revenue"]
            group["quantity"] += line["quantity"]
            group["_sales"].add(line["sale_id"])

        for group in groups.values():
            group["sales_count"] = len(group.pop("_sales"))

    items = sorted(
        (
            {
                "id": group["id"],
                "label": group["label"],
                "revenue": _round2(group["revenue"]),
                "sales_count": group["sales_count"],
                "quantity": (
                    _round2(group["quantity"])
                    if group.get("quantity") is not None
                    else None
                ),
            }
            for group in groups.values()
        ),
        key=lambda item: (-item["revenue"], item["label"]),
    )

    return {"group_by": group_by, "items": items[:limit]}


# ---------------------------------------------------------------
# Distribución de frecuencias
# ---------------------------------------------------------------
def sales_frequencies(
    db: Session,
    company_id: int,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    seller_id: int | None = None,
    category_id: int | None = None,
) -> dict:
    """Histograma de los importes de venta (regla de Sturges)."""
    _check_range(date_from, date_to)

    totals = [
        row["total"]
        for row in _load_sales(
            db,
            _sale_filters(
                company_id,
                date_from=date_from,
                date_to=date_to,
                seller_id=seller_id,
                category_id=category_id,
            ),
        )
    ]

    if not totals:
        return {
            "count": 0,
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "bins": [],
        }

    low, high = min(totals), max(totals)
    count = len(totals)

    if low == high:
        edges = [low, high]
        frequencies = [count]
    else:
        # Regla de Sturges: k = ceil(log2(n) + 1)
        bins = max(1, math.ceil(math.log2(count) + 1))
        width = (high - low) / bins
        edges = [low + index * width for index in range(bins + 1)]
        frequencies = [0] * bins
        for value in totals:
            index = min(int((value - low) / width), bins - 1)
            frequencies[index] += 1

    bins_out = []
    for index, frequency in enumerate(frequencies):
        bins_out.append(
            {
                "bin_start": _round2(edges[index]),
                "bin_end": _round2(edges[index + 1]),
                "frequency": frequency,
                "relative": round(frequency / count, 4),
            }
        )

    stats = _descriptive_stats(totals)
    return {
        "count": count,
        "min": stats["min"],
        "max": stats["max"],
        "mean": stats["mean"],
        "median": stats["median"],
        "bins": bins_out,
    }


# ---------------------------------------------------------------
# Opciones de filtro
# ---------------------------------------------------------------
def filter_options(db: Session, company_id: int) -> dict:
    """Vendedores con ventas y categorías activas de la empresa."""
    sellers = [
        {"id": user_id, "name": name}
        for user_id, name in db.execute(
            select(User.id, User.full_name)
            .join(Sale, Sale.created_by == User.id)
            .where(Sale.company_id == company_id)
            .distinct()
            .order_by(User.full_name)
        ).all()
    ]

    categories = [
        {"id": category_id, "name": name}
        for category_id, name in db.execute(
            select(Category.id, Category.name)
            .where(
                Category.company_id == company_id,
                Category.is_active.is_(True),
            )
            .order_by(Category.name)
        ).all()
    ]

    return {"sellers": sellers, "categories": categories}
