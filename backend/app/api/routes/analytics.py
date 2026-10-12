"""Endpoints de analítica de ventas – Fase 10 (Dashboard Analytics)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.analytics import (
    BreakdownOut,
    FrequenciesOut,
    FilterOptionsOut,
    SeriesOut,
    SummaryOut,
)
from app.services import analytics_service
from app.services.analytics_service import AnalyticsError

router = APIRouter(
    prefix="/api/analytics",
    tags=["Analytics"],
    dependencies=[Depends(get_current_user)],
)


def _http_error(error: AnalyticsError) -> HTTPException:
    """Traduce errores de regla de negocio a respuestas HTTP."""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(error),
    )


def _filters(
    date_from: date | None = Query(
        default=None, description="Fecha inicial inclusive (YYYY-MM-DD)"
    ),
    date_to: date | None = Query(
        default=None, description="Fecha final inclusive (YYYY-MM-DD)"
    ),
    seller_id: int | None = Query(
        default=None, ge=1, description="Id del usuario vendedor"
    ),
    category_id: int | None = Query(
        default=None, ge=1, description="Id de la categoría"
    ),
) -> dict:
    """Filtros comunes: periodo, vendedor y categoría.

    El ámbito es siempre la empresa del token (el plan habla de filtro
    por sucursal, pero el modelo no tiene sucursales: cada empresa es un
    ámbito aislado y equivale a una sucursal).
    """
    return {
        "date_from": date_from,
        "date_to": date_to,
        "seller_id": seller_id,
        "category_id": category_id,
    }


@router.get("/summary", response_model=SummaryOut)
def get_summary(
    filters: dict = Depends(_filters),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SummaryOut:
    """KPIs, media/mediana y comparación con el periodo anterior."""
    try:
        return analytics_service.sales_summary(
            db, current_user.company_id, **filters
        )
    except AnalyticsError as error:
        raise _http_error(error) from None


@router.get("/series", response_model=SeriesOut)
def get_series(
    granularity: str = Query(default="day", pattern="^(day|week|month)$"),
    filters: dict = Depends(_filters),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SeriesOut:
    """Ventas por periodo (día, semana o mes) con huecos a cero."""
    try:
        return analytics_service.sales_series(
            db,
            current_user.company_id,
            granularity=granularity,
            **filters,
        )
    except AnalyticsError as error:
        raise _http_error(error) from None


@router.get("/breakdown", response_model=BreakdownOut)
def get_breakdown(
    group_by: str = Query(default="product", pattern="^(product|category|seller)$"),
    limit: int = Query(default=10, ge=1, le=25),
    filters: dict = Depends(_filters),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BreakdownOut:
    """Ingresos por producto, categoría o vendedor (top por importe)."""
    try:
        return analytics_service.sales_breakdown(
            db,
            current_user.company_id,
            group_by=group_by,
            limit=limit,
            **filters,
        )
    except AnalyticsError as error:
        raise _http_error(error) from None


@router.get("/frequencies", response_model=FrequenciesOut)
def get_frequencies(
    filters: dict = Depends(_filters),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FrequenciesOut:
    """Distribución de frecuencias de los importes de venta."""
    try:
        return analytics_service.sales_frequencies(
            db, current_user.company_id, **filters
        )
    except AnalyticsError as error:
        raise _http_error(error) from None


@router.get("/filters", response_model=FilterOptionsOut)
def get_filters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FilterOptionsOut:
    """Opciones para los selectores del dashboard (vendedores y categorías)."""
    return analytics_service.filter_options(db, current_user.company_id)
