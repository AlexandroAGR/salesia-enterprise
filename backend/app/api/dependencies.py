from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import role_has_permission
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.services.audit_service import record_audit


security = HTTPBearer()


def get_role_name(db: Session, user: User) -> str | None:
    """Nombre del rol del usuario (None si el rol no existe)."""
    if user.role_id is None:
        return None

    return db.execute(
        select(Role.name).where(Role.id == user.role_id)
    ).scalar_one_or_none()


def require_permission(permission: str):
    """Dependency factory: exige un permiso concreto de la matriz.

    Si el rol del usuario no posee el permiso se registra un
    ``access.denied`` en auditoría y se responde 403.
    """

    def dependency(
        request: Request,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user),
    ) -> User:
        role_name = get_role_name(db, user)

        if not role_has_permission(role_name, permission):
            record_audit(
                db,
                user=user,
                action="access.denied",
                entity_type="endpoint",
                entity_id=f"{request.method} {request.url.path}",
                request=request,
                details={"permission": permission, "role": role_name},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta operación",
            )

        return user

    return dependency


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials

    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    subject = payload.get("sub")

    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    statement = select(User).where(
        User.id == user_id,
        User.is_active.is_(True),
    )

    user = db.execute(statement).scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user