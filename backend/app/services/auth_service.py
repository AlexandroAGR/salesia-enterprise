from datetime import datetime

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.services.audit_service import record_audit


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> User | None:
    statement = select(User).where(User.email == email)
    user = db.execute(statement).scalar_one_or_none()

    if user is None:
        return None

    if not user.is_active:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def login_user(
    db: Session,
    email: str,
    password: str,
    request: Request | None = None,
) -> str | None:
    user = authenticate_user(db, email, password)

    if user is None:
        # Auditoría del intento fallido (Fase 13: registro de
        # acciones críticas): si el correo existe, queda vinculado
        # a su usuario y empresa; si no, sólo el detalle.
        existing = db.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()

        if existing is None:
            reason = "unknown_user"
        elif not existing.is_active:
            reason = "inactive_user"
        else:
            reason = "bad_password"

        record_audit(
            db,
            user=existing,
            action="auth.login_failed",
            entity_type="user",
            entity_id=existing.id if existing is not None else "-",
            request=request,
            details={"email": email, "reason": reason},
        )
        return None

    user.last_login_at = datetime.now()
    db.commit()

    token = create_access_token(str(user.id))

    record_audit(
        db,
        user=user,
        action="auth.login",
        entity_type="user",
        entity_id=user.id,
        request=request,
        details={"email": user.email},
    )

    return token