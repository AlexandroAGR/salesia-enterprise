from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.sale import InventoryMovementInput, InventoryOut
from app.services import inventory_service
from app.services.inventory_service import InventoryError

router = APIRouter(
    prefix="/api/inventory",
    tags=["Inventario"],
    dependencies=[Depends(get_current_user)],
)


def _qty(value) -> str:
    """Cantidades como string con 3 decimales, igual que el resto de la API.

    Sin esto, los números sueltos (int/float) se serializan como JSON numérico
    y rompen la consistencia con el resto de endpoints (p. ej. "10.000").
    """
    return str(Decimal(str(value)).quantize(Decimal("0.001")))


@router.get("", response_model=Page[InventoryOut])
def list_inventory(
    search: str | None = Query(default=None, min_length=1, max_length=100),
    category_id: int | None = Query(default=None, ge=1),
    low_stock_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = inventory_service.list_inventory(
        db,
        current_user.company_id,
        search=search,
        category_id=category_id,
        low_stock_only=low_stock_only,
        page=page,
        page_size=page_size,
    )

    return Page[InventoryOut](
        items=items, total=total, page=page, page_size=page_size
    )


@router.get("/movements", response_model=Page[dict])
def list_movements(
    product_id: int | None = Query(default=None, ge=1),
    movement_type: str | None = Query(
        default=None, pattern="^(entrada|salida|ajuste)$"
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = inventory_service.list_movements(
        db,
        current_user.company_id,
        product_id=product_id,
        movement_type=movement_type,
        page=page,
        page_size=page_size,
    )

    return Page[dict](
        items=items, total=total, page=page, page_size=page_size
    )


@router.post(
    "/movements",
    status_code=status.HTTP_201_CREATED,
)
def create_movement(
    payload: InventoryMovementInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = inventory_service.apply_movement(
            db,
            current_user.company_id,
            current_user.id,
            payload,
        )
    except InventoryError as error:
        message = str(error)
        code = (
            status.HTTP_404_NOT_FOUND
            if "no existe" in message
            else status.HTTP_409_CONFLICT
        )
        raise HTTPException(status_code=code, detail=message) from error

    movement = result.pop("movement")

    return {
        "id": movement.id,
        "product_id": movement.product_id,
        "product_name": result["product_name"],
        "movement_type": movement.movement_type,
        "quantity": _qty(movement.quantity),
        "reason": movement.reason,
        "sale_id": movement.sale_id,
        "created_at": movement.created_at,
        "previous_quantity": _qty(result["previous_quantity"]),
        "new_quantity": _qty(result["new_quantity"]),
    }