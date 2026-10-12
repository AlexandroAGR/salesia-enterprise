"""Consulta de auditoría – Fase 13 (RF-22).

Sólo el rol Administrador puede leer el registro de acciones
críticas, y sólo las filas de su propia empresa.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_permission
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit import AuditOut
from app.schemas.common import Page

router = APIRouter(
    prefix="/api/audit",
    tags=["Auditoría"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=Page[AuditOut])
def list_audit_logs(
    action: str | None = Query(default=None, min_length=1, max_length=100),
    entity_type: str | None = Query(default=None, min_length=1, max_length=80),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("audit:view")),
) -> Page[AuditOut]:
    """Histórico paginado de acciones críticas de la empresa."""
    filters = [AuditLog.company_id == current_user.company_id]

    if action is not None:
        filters.append(AuditLog.action == action)

    if entity_type is not None:
        filters.append(AuditLog.entity_type == entity_type)

    total = int(
        db.execute(
            select(func.count(AuditLog.id)).where(*filters)
        ).scalar_one()
    )

    rows = db.execute(
        select(AuditLog, User.full_name)
        .outerjoin(User, User.id == AuditLog.user_id)
        .where(*filters)
        .order_by(AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return Page[AuditOut](
        items=[
            AuditOut(
                id=row.id,
                company_id=row.company_id,
                user_id=row.user_id,
                user_name=user_name,
                action=row.action,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                ip_address=row.ip_address,
                details=row.details,
                created_at=row.created_at,
            )
            for row, user_name in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
