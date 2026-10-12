"""Esquemas del motor de analítica de ventas – Fase 10 (Dashboard)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class SummaryFilters(BaseModel):
    """Eco de los filtros aplicados a la consulta."""

    date_from: date | None = None
    date_to: date | None = None
    seller_id: int | None = None
    category_id: int | None = None


class Kpis(BaseModel):
    revenue: float
    sales_count: int
    avg_ticket: float
    customers_count: int
    items_sold: float


class Statistics(BaseModel):
    count: int
    mean: float | None = None
    median: float | None = None
    min: float | None = None
    max: float | None = None
    stddev: float | None = None


class PreviousPeriod(BaseModel):
    revenue: float
    sales_count: int
    revenue_change_pct: float | None = None


class SummaryOut(BaseModel):
    filters: SummaryFilters
    kpis: Kpis
    statistics: Statistics
    previous_period: PreviousPeriod | None = None


class SeriesPoint(BaseModel):
    bucket: str
    sales_count: int
    revenue: float


class SeriesOut(BaseModel):
    granularity: str
    items: list[SeriesPoint]


class BreakdownItem(BaseModel):
    id: int | None = None
    label: str
    revenue: float
    sales_count: int
    quantity: float | None = None


class BreakdownOut(BaseModel):
    group_by: str
    items: list[BreakdownItem]


class FrequencyBin(BaseModel):
    bin_start: float
    bin_end: float
    frequency: int
    relative: float


class FrequenciesOut(BaseModel):
    count: int
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    median: float | None = None
    bins: list[FrequencyBin]


class FilterOption(BaseModel):
    id: int
    name: str


class FilterOptionsOut(BaseModel):
    sellers: list[FilterOption]
    categories: list[FilterOption]
