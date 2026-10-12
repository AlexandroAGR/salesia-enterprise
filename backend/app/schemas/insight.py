"""Esquemas de la API de insights – Fase 11."""

from datetime import date, datetime

from pydantic import BaseModel, Field

# Severidades soportadas por el motor de insights
SEVERITIES = ("info", "positive", "warning")


class InsightOut(BaseModel):
    """Observación generada por una regla, con su evidencia numérica."""

    id: int
    rule_code: str
    rule_name: str
    title: str
    description: str
    severity: str
    evidence: dict
    analysis_id: int | None = None
    analysis_type: str | None = None
    dataset_id: int | None = None
    dataset_name: str | None = None
    created_at: datetime


class RuleInfoOut(BaseModel):
    """Entrada del catálogo de reglas disponibles."""

    code: str
    name: str
    description: str
    source: str


class GenerateIn(BaseModel):
    """Ámbito opcional para ejecutar las reglas.

    `period` es el atajo del frontend (7/30/90 días o "all" para el
    histórico completo); un rango explícito de fechas tiene prioridad
    sobre él. Sin período ni fechas se analizan los últimos 7 días.
    """

    period: str | None = Field(default=None, pattern="^(7|30|90|all)$")
    date_from: date | None = None
    date_to: date | None = None
    seller_id: int | None = Field(default=None, ge=1)
    category_id: int | None = Field(default=None, ge=1)


class GenerateOut(BaseModel):
    """Resultado de una ejecución: nuevos insights y duplicados omitidos."""

    created: list[InsightOut]
    skipped: int
