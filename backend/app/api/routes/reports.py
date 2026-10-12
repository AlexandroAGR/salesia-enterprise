"""Endpoints de reportes – Fase 12."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.report import (
    ReportGenerateIn,
    ReportOut,
    ReportSummaryOut,
    ReportTypeInfoOut,
)
from app.services import report_service
from app.services.report_service import ReportError

router = APIRouter(
    prefix="/api/reports",
    tags=["Reportes"],
    dependencies=[Depends(get_current_user)],
)


def _http_error(error: ReportError) -> HTTPException:
    """Traduce errores del motor a respuestas HTTP."""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(error),
    )


@router.get("/types", response_model=list[ReportTypeInfoOut])
def list_types() -> list[ReportTypeInfoOut]:
    """Catálogo de reportes disponibles."""
    return report_service.types_catalog()


@router.post(
    "/generate",
    response_model=ReportOut,
    status_code=status.HTTP_201_CREATED,
)
def generate_report(
    payload: ReportGenerateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportOut:
    """Calcula un reporte y guarda su instantánea en el histórico."""
    try:
        return report_service.generate(
            db, current_user.company_id, current_user.id, payload
        )
    except ReportError as error:
        raise _http_error(error) from None


@router.get("", response_model=Page[ReportSummaryOut])
def list_reports(
    report_type: str | None = Query(
        default=None, description="Código del reporte (400 si no existe)"
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Page[ReportSummaryOut]:
    """Histórico paginado de reportes con filtro opcional por tipo."""
    try:
        items, total = report_service.list_reports(
            db,
            current_user.company_id,
            report_type=report_type,
            page=page,
            page_size=page_size,
        )
    except ReportError as error:
        raise _http_error(error) from None
    return Page[ReportSummaryOut](
        items=items, total=total, page=page, page_size=page_size
    )


@router.get("/{report_id}", response_model=ReportOut)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportOut:
    """Instantánea completa de un reporte guardado."""
    result = report_service.get_report(
        db, current_user.company_id, report_id
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reporte no encontrado",
        )
    return result
