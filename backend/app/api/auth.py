from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_role_name
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.audit_service import record_audit
from app.services.auth_service import login_user


router = APIRouter(
    prefix="/api/auth",
    tags=["Autenticación"],
)


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    credentials: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    access_token = login_user(
        db=db,
        email=credentials.email,
        password=credentials.password,
        request=request,
    )

    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(
        access_token=access_token,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Registra el cierre de sesión en auditoría.

    El JWT caduca por sí solo a los 60 minutos; este endpoint deja
    constancia del momento en que el usuario cierra sesión.
    """
    record_audit(
        db,
        user=current_user,
        action="auth.logout",
        entity_type="user",
        entity_id=current_user.id,
        request=request,
        details={"email": current_user.email},
    )


@router.get("/me")
def get_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "company_id": current_user.company_id,
        "role_id": current_user.role_id,
        "role": get_role_name(db, current_user),
        "is_active": current_user.is_active,
    }
