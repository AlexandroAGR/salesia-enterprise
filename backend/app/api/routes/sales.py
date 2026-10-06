from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.sale import SaleCreate, SaleDetailOut, SaleOut
from app.services import sale_service
from app.services.sale_service import SaleError

router = APIRouter(
    prefix="/api/sales",
    tags=["Ventas"],
    dependencies=[Depends(get_current_user)],
)


def _http_error(error: SaleError) -> HTTPException:
    """Traduce errores de regla de negocio a respuestas HTTP."""
    message = str(error)
    if "no existe" in message:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=message
        )
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT, detail=message
    )


def _sale_out(sale, customer_name: str | None = None) -> SaleOut:
    """Arma el JSON de la venta con nombres derivados."""
    return SaleOut(
        id=sale.id,
        sale_number=sale.sale_number,
        status=sale.status,
        currency=sale.currency,
        customer_id=sale.customer_id,
        customer_name=customer_name,
        subtotal=sale.subtotal,
        discount_amount=sale.discount_amount,
        tax_amount=sale.tax_amount,
        total_amount=sale.total_amount,
        notes=sale.notes,
        sold_at=sale.sold_at,
        created_at=sale.created_at,
    )


@router.get("", response_model=Page[SaleOut])
def list_sales(
    search: str | None = Query(default=None, min_length=1, max_length=100),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        pattern="^(draft|pending|completed|cancelled|refunded)$",
    ),
    customer_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = sale_service.list_sales(
        db,
        current_user.company_id,
        search=search,
        status_filter=status_filter,
        customer_id=customer_id,
        page=page,
        page_size=page_size,
    )

    customer_names = sale_service.get_customer_names(
        db, {sale.customer_id for sale in items if sale.customer_id}
    )

    return Page[SaleOut](
        items=[
            _sale_out(
                sale,
                customer_names.get(sale.customer_id)
                if sale.customer_id
                else None,
            )
            for sale in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{sale_id}", response_model=SaleDetailOut)
def get_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sale = sale_service.get_sale(db, current_user.company_id, sale_id)

    if sale is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venta no encontrada",
        )

    customer_names = sale_service.get_customer_names(
        db, {sale.customer_id} if sale.customer_id else set()
    )
    base = _sale_out(
        sale,
        customer_names.get(sale.customer_id) if sale.customer_id else None,
    ).model_dump()

    details = sale_service.get_sale_details(db, sale_id)
    product_names = sale_service.get_product_names(
        db, {d.product_id for d in details}
    )

    payment = sale_service.get_payment(db, sale_id)
    payment_out = None
    if payment is not None:
        payment_out = {
            "payment_method_id": payment.payment_method_id,
            "payment_method_name": payment.method_name,
            "amount": payment.amount,
            "status": payment.status,
            "reference": payment.reference,
            "paid_at": payment.paid_at,
        }

    return SaleDetailOut(
        **base,
        items=[
            {
                "product_id": d.product_id,
                "product_name": product_names.get(
                    d.product_id, f"Producto {d.product_id}"
                ),
                "quantity": d.quantity,
                "unit_price": d.unit_price,
                "discount_amount": d.discount_amount,
                "line_total": d.line_total,
            }
            for d in details
        ],
        payment=payment_out,
    )


@router.post(
    "", response_model=SaleDetailOut, status_code=status.HTTP_201_CREATED
)
def create_sale(
    payload: SaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        sale = sale_service.create_sale(
            db,
            current_user.company_id,
            current_user.id,
            payload,
        )
    except SaleError as error:
        raise _http_error(error) from error

    # Devolvemos la venta recién creada con su detalle completo
    return get_sale(sale.id, db, current_user)