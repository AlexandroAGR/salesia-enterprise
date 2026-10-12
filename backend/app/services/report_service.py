"""Motor de reportes – Fase 12.

Genera y conserva el histórico de cinco reportes comerciales y
estadísticos sobre los datos de la empresa:

  - ventas: detalle de las ventas del periodo con sus totales
  - estadistico: KPIs, estadística descriptiva e interpretación
  - productos: ranking de productos por ingresos con su participación
  - clientes: ranking de clientes por facturación con ticket medio
  - vendedores: desempeño de cada vendedor con su participación

Cada generación guarda en la columna `content` una instantánea del
contenido calculado, de modo que las consultas históricas muestran los
números tal como estaban al emitir el reporte aunque luego cambien los
datos.

Reglas de negocio (idénticas a la analítica de la Fase 10):

  - Sólo se reportan las ventas que NO están canceladas ni reembolsadas.
  - El filtro de categoría incluye la venta si alguna de sus líneas
    pertenece a la categoría.
  - Todas las consultas quedan acotadas a la empresa del token.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.report import Report
from app.models.sale import Sale
from app.models.user import User
from app.schemas.report import ReportGenerateIn
from app.services import analytics_service

# Ventana por defecto del reporte (días, fecha UTC)
DEFAULT_WINDOW_DAYS = 7

# Límite de filas de los rankings (cubre el catálogo completo de la
# empresa; por encima se trunca y los totales siguen siendo los reales)
ALL_ROWS_LIMIT = 10_000

# Catálogo de reportes: código → metadatos (el orden define la salida)
REPORT_TYPES: dict[str, dict[str, str]] = {
    "ventas": {
        "name": "Reporte de ventas",
        "description": (
            "Detalle de las ventas del periodo con totales, "
            "impuestos y estados."
        ),
    },
    "estadistico": {
        "name": "Reporte estadístico",
        "description": (
            "KPIs, estadística descriptiva, comparación con el "
            "periodo anterior e interpretación."
        ),
    },
    "productos": {
        "name": "Reporte de productos",
        "description": (
            "Ranking de productos por ingresos con unidades "
            "vendidas y participación."
        ),
    },
    "clientes": {
        "name": "Reporte de clientes",
        "description": (
            "Ranking de clientes por facturación con ticket medio "
            "y última compra."
        ),
    },
    "vendedores": {
        "name": "Reporte de vendedores",
        "description": (
            "Desempeño de cada vendedor con ventas, ingresos, "
            "ticket medio y participación."
        ),
    },
}


class ReportError(Exception):
    """Error controlado del motor de reportes."""


def _round(value: float, digits: int = 2) -> float:
    return round(value, digits)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _resolve_scope(payload: ReportGenerateIn | None) -> dict:
    """Ámbito del reporte (por defecto: últimos 7 días)."""
    if payload is None:
        payload = ReportGenerateIn(report_type="ventas")

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
        raise ReportError(
            "El rango de fechas es inválido: la fecha inicial "
            "es posterior a la final"
        )

    return {
        "date_from": date_from,
        "date_to": date_to,
        "seller_id": payload.seller_id,
        "category_id": payload.category_id,
    }


def _scope_out(scope: dict) -> dict:
    """Ámbito serializado del contenido (fechas ISO o null)."""
    date_from: date | None = scope["date_from"]
    date_to: date | None = scope["date_to"]
    return {
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None,
        "seller_id": scope["seller_id"],
        "category_id": scope["category_id"],
    }


def _sale_filters(db: Session, company_id: int, scope: dict) -> list:
    """Mismas condiciones de ámbito que la analítica (Fase 10), para
    que los números del reporte y del dashboard coincidan siempre."""
    return analytics_service._sale_filters(
        company_id,
        date_from=scope["date_from"],
        date_to=scope["date_to"],
        seller_id=scope["seller_id"],
        category_id=scope["category_id"],
    )


def _summary(db: Session, company_id: int, scope: dict) -> dict:
    """Resumen del ámbito: KPIs, estadística y periodo anterior."""
    return analytics_service.sales_summary(
        db,
        company_id,
        date_from=scope["date_from"],
        date_to=scope["date_to"],
        seller_id=scope["seller_id"],
        category_id=scope["category_id"],
    )


def _default_title(report_type: str, scope: dict) -> str:
    name = REPORT_TYPES[report_type]["name"]
    date_from: date | None = scope["date_from"]
    date_to: date | None = scope["date_to"]
    if date_from and date_to:
        window = f" · {date_from.isoformat()} al {date_to.isoformat()}"
    elif date_from:
        window = f" · desde {date_from.isoformat()}"
    else:
        window = " · histórico completo"
    return f"{name}{window}"[:180]


# ---------------------------------------------------------------
# Constructores de contenido por tipo de reporte
# ---------------------------------------------------------------
def _build_ventas(
    db: Session, company_id: int, scope: dict, summary: dict
) -> dict:
    rows = db.execute(
        select(
            Sale,
            Customer.full_name.label("customer_name"),
            User.full_name.label("seller_name"),
        )
        .outerjoin(Customer, Sale.customer_id == Customer.id)
        .outerjoin(User, Sale.created_by == User.id)
        .where(*_sale_filters(db, company_id, scope))
        .order_by(Sale.sold_at.desc(), Sale.id.desc())
    ).all()

    items = [
        {
            "sale_number": sale.sale_number,
            "sold_at": sale.sold_at.isoformat(),
            "customer": customer_name or "Sin cliente",
            "seller": seller_name or "Sin vendedor",
            "status": sale.status,
            "subtotal": _round(float(sale.subtotal)),
            "discount_amount": _round(float(sale.discount_amount)),
            "tax_amount": _round(float(sale.tax_amount)),
            "total_amount": _round(float(sale.total_amount)),
        }
        for sale, customer_name, seller_name in rows
    ]

    return {
        "scope": _scope_out(scope),
        "summary": summary["kpis"],
        "rows": items,
    }


def _interpretation(summary: dict) -> list[str]:
    """Lectura del reporte estadístico a partir de sus propios números."""
    statistics = summary["statistics"]
    kpis = summary["kpis"]

    if statistics["count"] == 0:
        return ["Sin ventas en el periodo: no hay datos que interpretar."]

    lines: list[str] = []
    mean = statistics["mean"]
    median = statistics["median"]

    if mean is not None and median:
        if mean > median:
            lines.append(
                f"La media (S/ {mean:.2f}) supera a la mediana "
                f"(S/ {median:.2f}): valores altos puntuales elevan "
                "el promedio."
            )
        elif mean < median:
            lines.append(
                f"La media (S/ {mean:.2f}) queda por debajo de la "
                f"mediana (S/ {median:.2f}): valores bajos puntuales "
                "deprimen el promedio."
            )
        else:
            lines.append(
                f"La media y la mediana coinciden en S/ {mean:.2f}: "
                "el promedio no está sesgado por ventas extremas."
            )

    stddev = statistics["stddev"]
    if stddev is not None and mean:
        cv = stddev / mean
        if cv >= 1:
            lines.append(
                f"Alta dispersión: el coeficiente de variación es "
                f"{cv:.2f} (desviación S/ {stddev:.2f} sobre media "
                f"S/ {mean:.2f})."
            )
        else:
            lines.append(
                f"Los importes se mantienen agrupados: coeficiente de "
                f"variación {cv:.2f} (desviación S/ {stddev:.2f} sobre "
                f"media S/ {mean:.2f})."
            )

    lines.append(
        f"Los tickets van de S/ {statistics['min']:.2f} a "
        f"S/ {statistics['max']:.2f} con un ticket promedio de "
        f"S/ {kpis['avg_ticket']:.2f}."
    )

    previous = summary["previous_period"]
    if previous is None:
        lines.append("Histórico completo: sin periodo anterior comparable.")
    elif previous["revenue_change_pct"] is None:
        lines.append("Sin ingresos en el periodo anterior con los que comparar.")
    elif previous["revenue_change_pct"] >= 0:
        lines.append(
            f"Los ingresos suben {previous['revenue_change_pct']:.1f}% "
            f"frente al periodo anterior (S/ {previous['revenue']:.2f})."
        )
    else:
        lines.append(
            f"Los ingresos bajan "
            f"{abs(previous['revenue_change_pct']):.1f}% frente al "
            f"periodo anterior (S/ {previous['revenue']:.2f})."
        )

    return lines


def _build_estadistico(scope: dict, summary: dict) -> dict:
    return {
        "scope": _scope_out(scope),
        "kpis": summary["kpis"],
        "statistics": summary["statistics"],
        "previous_period": summary["previous_period"],
        "interpretation": _interpretation(summary),
    }


def _build_productos(
    db: Session, company_id: int, scope: dict, summary: dict
) -> dict:
    breakdown = analytics_service.sales_breakdown(
        db,
        company_id,
        group_by="product",
        date_from=scope["date_from"],
        date_to=scope["date_to"],
        seller_id=scope["seller_id"],
        category_id=scope["category_id"],
        limit=ALL_ROWS_LIMIT,
    )
    kpis = summary["kpis"]
    total = kpis["revenue"]

    items = [
        {
            "product": item["label"],
            "revenue": item["revenue"],
            "sales_count": item["sales_count"],
            "quantity": item["quantity"] or 0,
            "share_pct": _round(item["revenue"] / total * 100) if total else 0.0,
        }
        for item in breakdown["items"]
    ]

    return {
        "scope": _scope_out(scope),
        "totals": {
            "revenue": total,
            "products_count": len(items),
            "units": _round(sum(row["quantity"] for row in items)),
        },
        "rows": items,
    }


def _build_clientes(
    db: Session, company_id: int, scope: dict, summary: dict
) -> dict:
    sales = db.execute(
        select(Sale.customer_id, Sale.total_amount, Sale.sold_at)
        .where(*_sale_filters(db, company_id, scope))
        .order_by(Sale.id)
    ).all()

    known = {row.customer_id for row in sales if row.customer_id is not None}
    names: dict = {}
    if known:
        names = dict(
            db.execute(
                select(Customer.id, Customer.full_name).where(
                    Customer.id.in_(known)
                )
            ).all()
        )

    groups: dict = {}
    for row in sales:
        group = groups.setdefault(
            row.customer_id,
            {"count": 0, "revenue": 0.0, "last": None},
        )
        group["count"] += 1
        group["revenue"] += float(row.total_amount)
        if group["last"] is None or row.sold_at > group["last"]:
            group["last"] = row.sold_at

    items = sorted(
        (
            {
                "customer": names.get(customer_id) or "Sin cliente",
                "sales_count": group["count"],
                "revenue": _round(group["revenue"]),
                "avg_ticket": _round(group["revenue"] / group["count"]),
                "last_purchase": group["last"].isoformat(),
            }
            for customer_id, group in groups.items()
        ),
        key=lambda item: (-item["revenue"], item["customer"]),
    )

    kpis = summary["kpis"]
    return {
        "scope": _scope_out(scope),
        "totals": {
            "customers_count": kpis["customers_count"],
            "revenue": kpis["revenue"],
            "sales_count": kpis["sales_count"],
        },
        "rows": items,
    }


def _build_vendedores(
    db: Session, company_id: int, scope: dict, summary: dict
) -> dict:
    breakdown = analytics_service.sales_breakdown(
        db,
        company_id,
        group_by="seller",
        date_from=scope["date_from"],
        date_to=scope["date_to"],
        seller_id=scope["seller_id"],
        category_id=scope["category_id"],
        limit=ALL_ROWS_LIMIT,
    )
    kpis = summary["kpis"]
    total = kpis["revenue"]

    items = [
        {
            "seller": item["label"],
            "revenue": item["revenue"],
            "sales_count": item["sales_count"],
            "avg_ticket": (
                _round(item["revenue"] / item["sales_count"])
                if item["sales_count"]
                else 0.0
            ),
            "share_pct": _round(item["revenue"] / total * 100) if total else 0.0,
        }
        for item in breakdown["items"]
    ]

    return {
        "scope": _scope_out(scope),
        "totals": {
            "sellers_count": len(items),
            "revenue": total,
            "sales_count": kpis["sales_count"],
        },
        "rows": items,
    }


def _build_content(
    db: Session, company_id: int, report_type: str, scope: dict
) -> dict:
    summary = _summary(db, company_id, scope)

    if report_type == "ventas":
        content = _build_ventas(db, company_id, scope, summary)
    elif report_type == "estadistico":
        content = _build_estadistico(scope, summary)
    elif report_type == "productos":
        content = _build_productos(db, company_id, scope, summary)
    elif report_type == "clientes":
        content = _build_clientes(db, company_id, scope, summary)
    else:
        content = _build_vendedores(db, company_id, scope, summary)

    return content


# ---------------------------------------------------------------
# Generación, consulta y catálogo
# ---------------------------------------------------------------
def _to_out(
    report: Report,
    *,
    created_by_name: str | None,
    include_content: bool = False,
) -> dict:
    data: dict = {
        "id": report.id,
        "report_type": report.report_type,
        "report_type_label": REPORT_TYPES[report.report_type]["name"],
        "title": report.title,
        "filters": report.filters,
        "created_by": report.created_by,
        "created_by_name": created_by_name,
        "created_at": report.created_at,
    }
    if include_content:
        data["content"] = report.content
    return data


def _user_names(
    db: Session, company_id: int, ids: set[int]
) -> dict[int, str]:
    if not ids:
        return {}
    return dict(
        db.execute(
            select(User.id, User.full_name).where(
                User.id.in_(ids),
                User.company_id == company_id,
            )
        ).all()
    )


def generate(
    db: Session,
    company_id: int,
    user_id: int,
    payload: ReportGenerateIn,
) -> dict:
    """Calcula el contenido del reporte y guarda la instantánea."""
    report_type = payload.report_type
    if report_type not in REPORT_TYPES:
        raise ReportError(f"El tipo de reporte '{report_type}' no existe")

    scope = _resolve_scope(payload)
    content = _build_content(db, company_id, report_type, scope)

    filters = {
        "period": payload.period,
        "date_from": (
            scope["date_from"].isoformat() if scope["date_from"] else None
        ),
        "date_to": (
            scope["date_to"].isoformat() if scope["date_to"] else None
        ),
        "seller_id": payload.seller_id,
        "category_id": payload.category_id,
    }

    report = Report(
        company_id=company_id,
        report_type=report_type,
        title=(payload.title or _default_title(report_type, scope))[:180],
        filters=filters,
        content=content,
        created_by=user_id,
        created_at=_now(),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    names = _user_names(db, company_id, {user_id})
    return _to_out(
        report, created_by_name=names.get(user_id), include_content=True
    )


def list_reports(
    db: Session,
    company_id: int,
    *,
    report_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """Histórico paginado de reportes con filtro opcional por tipo."""
    filters = [Report.company_id == company_id]

    if report_type is not None:
        if report_type not in REPORT_TYPES:
            raise ReportError(
                f"El tipo de reporte '{report_type}' no existe"
            )
        filters.append(Report.report_type == report_type)

    total = db.execute(
        select(func.count()).select_from(Report).where(*filters)
    ).scalar_one()

    rows = (
        db.execute(
            select(Report)
            .where(*filters)
            .order_by(Report.created_at.desc(), Report.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )

    names = _user_names(
        db, company_id, {row.created_by for row in rows if row.created_by}
    )
    items = [
        _to_out(row, created_by_name=names.get(row.created_by))
        for row in rows
    ]
    return items, total


def get_report(
    db: Session, company_id: int, report_id: int
) -> dict | None:
    """Instantánea completa de un reporte (None si no existe)."""
    report = db.execute(
        select(Report).where(
            Report.id == report_id,
            Report.company_id == company_id,
        )
    ).scalar_one_or_none()
    if report is None:
        return None

    names = _user_names(
        db, company_id, {report.created_by} if report.created_by else set()
    )
    return _to_out(
        report,
        created_by_name=names.get(report.created_by),
        include_content=True,
    )


def types_catalog() -> list[dict]:
    """Catálogo de reportes disponibles (código, nombre y descripción)."""
    return [
        {
            "code": code,
            "name": meta["name"],
            "description": meta["description"],
        }
        for code, meta in REPORT_TYPES.items()
    ]
