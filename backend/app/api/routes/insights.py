"""Endpoints de insights empresariales – Fase 11."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.insight import GenerateIn, GenerateOut, InsightOut, RuleInfoOut
from app.services import insight_service
from app.services.audit_service import record_audit
from app.services.insight_service import InsightError

router = APIRouter(
    prefix="/api/insights",
    tags=["Insights"],
    dependencies=[Depends(get_current_user)],
)


def _http_error(error: InsightError) -> HTTPException:
    """Traduce errores del motor a respuestas HTTP."""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(error),
    )


@router.get("/rules", response_model=list[RuleInfoOut])
def list_rules(
    _: User = Depends(require_permission("insights:view")),
) -> list[RuleInfoOut]:
    """Catálogo de reglas deterministas del motor de insights."""
    return insight_service.rules_catalog()


@router.get("", response_model=Page[InsightOut])
def list_insights(
    rule_code: str | None = Query(
        default=None, description="Código de la regla (400 si no existe)"
    ),
    severity: str | None = Query(
        default=None, pattern="^(info|positive|warning)$"
    ),
    analysis_id: int | None = Query(default=None, ge=1),
    dataset_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("insights:view")),
) -> Page[InsightOut]:
    """Histórico paginado de insights con filtros opcionales."""
    try:
        items, total = insight_service.list_insights(
            db,
            current_user.company_id,
            rule_code=rule_code,
            severity=severity,
            analysis_id=analysis_id,
            dataset_id=dataset_id,
            page=page,
            page_size=page_size,
        )
    except InsightError as error:
        raise _http_error(error) from None
    return Page[InsightOut](
        items=items, total=total, page=page, page_size=page_size
    )


@router.post("/generate", response_model=GenerateOut)
def generate_insights(
    request: Request,
    payload: GenerateIn | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("insights:generate")),
) -> GenerateOut:
    """Ejecuta las reglas y guarda solo las observaciones nuevas."""
    try:
        result = insight_service.generate(
            db, current_user.company_id, payload
        )
    except InsightError as error:
        raise _http_error(error) from None

    record_audit(
        db,
        user=current_user,
        action="insight.generate",
        entity_type="insight",
        entity_id="-",
        request=request,
        details={
            "created": len(result.get("created", [])),
            "skipped": result.get("skipped", 0),
        },
    )

    return GenerateOut(**result)
