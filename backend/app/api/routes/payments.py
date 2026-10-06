from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.schemas.sale import PaymentMethodOut
from app.services import payment_service
from app.services.payment_service import PaymentError

router = APIRouter(
    prefix="/api",
    tags=["Pagos"],
    dependencies=[Depends(get_current_user)],
)


def _payment_out(payment, sale_number: str | None = None) -> PaymentResponse:
    return PaymentResponse(
        id=payment.id,
        sale_id=payment.sale_id,
        payment_method_id=payment.payment_method_id,
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status,
        reference=payment.reference,
        paid_at=payment.paid_at,
        created_at=payment.created_at,
    )


# ---------------------------------------------------------------
# Catálogo de métodos de pago
# ---------------------------------------------------------------
@router.get("/payment-methods", response_model=list[PaymentMethodOut])
def list_payment_methods(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    methods = payment_service.list_payment_methods(
        db, current_user.company_id
    )

    return [
        PaymentMethodOut.model_validate(method) for method in methods
    ]


# ---------------------------------------------------------------
# Pagos de ventas
# ---------------------------------------------------------------
@router.get("/payments", response_model=Page[PaymentResponse])
def list_payments(
    sale_id: int | None = Query(default=None, ge=1),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        pattern="^(pending|paid|failed|refunded)$",
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows, total = payment_service.list_payments(
        db,
        current_user.company_id,
        sale_id=sale_id,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )

    return Page[PaymentResponse](
        items=[_payment_out(payment) for payment, _ in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        payment = payment_service.register_payment(
            db,
            current_user.company_id,
            payload,
        )
    except PaymentError as error:
        message = str(error)
        code = (
            status.HTTP_404_NOT_FOUND
            if "no existe" in message
            else status.HTTP_409_CONFLICT
        )
        raise HTTPException(status_code=code, detail=message) from error

    return _payment_out(payment)