"""Registro de acciones críticas en audit_logs – Fase 13 (RF-22).

Toda operación crítica (autenticación, altas/bajas/cambios de datos
de negocio, movimientos de stock, generación de reportes y accesos
denegados) deja una fila en ``audit_logs`` con usuario, empresa,
acción, entidad, dirección IP y detalles en JSON.
"""

import ipaddress
from datetime import datetime

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User


def client_ip(request: Request | None) -> str | None:
    """Dirección IP válida de la petición (NULL si no es una IP real)."""
    if request is None or request.client is None:
        return None

    host = request.client.host

    try:
        ipaddress.ip_address(host)
    except ValueError:
        return None

    return host


def record_audit(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: int | str | None = None,
    user: User | None = None,
    request: Request | None = None,
    details: dict | None = None,
) -> AuditLog:
    """Inserta y confirma una fila de auditoría.

    Se invoca DESPUÉS del commit de la operación principal: si el
    registro falla, la operación crítica ya quedó aplicada y el
    error de auditoría se propaga en lugar de silenciarse.
    """
    row = AuditLog(
        company_id=user.company_id if user is not None else None,
        user_id=user.id if user is not None else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else "-",
        ip_address=client_ip(request),
        details=details or {},
        created_at=datetime.now(),
    )

    db.add(row)
    db.commit()
    return row


def count_audit(
    db: Session,
    company_id: int | None,
    action: str | None = None,
) -> int:
    """Filas de auditoría de una empresa (para comparaciones previas)."""
    from sqlalchemy import func, select

    statement = select(func.count(AuditLog.id)).where(
        AuditLog.company_id == company_id
    )

    if action is not None:
        statement = statement.where(AuditLog.action == action)

    return int(db.execute(statement).scalar_one())
