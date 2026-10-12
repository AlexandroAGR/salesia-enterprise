"""Esquemas de la API de reportes – Fase 12."""

from datetime import date, datetime

from pydantic import BaseModel, Field

# Códigos de reporte aceptados por el motor (el orden define el catálogo)
REPORT_TYPES = (
    "ventas",
    "estadistico",
    "productos",
    "clientes",
    "vendedores",
)


class ReportTypeInfoOut(BaseModel):
    """Entrada del catálogo de reportes disponibles."""

    code: str
    name: str
    description: str


class ReportGenerateIn(BaseModel):
    """Ámbito para generar un reporte.

    `period` es el atajo del frontend (7/30/90 días o "all" para el
    histórico completo); un rango explícito de fechas tiene prioridad
    sobre él. Sin período ni fechas se reportan los últimos 7 días.
    """

    report_type: str
    title: str | None = Field(default=None, min_length=1, max_length=180)
    period: str | None = Field(default=None, pattern="^(7|30|90|all)$")
    date_from: date | None = None
    date_to: date | None = None
    seller_id: int | None = Field(default=None, ge=1)
    category_id: int | None = Field(default=None, ge=1)


class ReportSummaryOut(BaseModel):
    """Metadatos de un reporte guardado (sin el contenido)."""

    id: int
    report_type: str
    report_type_label: str
    title: str
    filters: dict
    created_by: int | None = None
    created_by_name: str | None = None
    created_at: datetime


class ReportOut(ReportSummaryOut):
    """Reporte completo con la instantánea calculada al generarlo."""

    content: dict
