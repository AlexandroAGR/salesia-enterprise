from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.product import Product
from app.schemas.sale import InventoryMovementInput

ZERO = Decimal("0")


class InventoryError(Exception):
    """Error de regla de negocio de inventario."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------
def list_inventory(
    db: Session,
    company_id: int,
    *,
    search: str | None = None,
    category_id: int | None = None,
    low_stock_only: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """Stock por producto con nombre, categoría y alerta de mínimo."""
    filters = [Product.company_id == company_id]

    if category_id is not None:
        filters.append(Product.category_id == category_id)

    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Product.name.ilike(term),
                Product.sku.ilike(term),
            )
        )

    # LEFT JOIN: un producto puede no tener fila en inventory aún
    base = (
        select(Product, Inventory, Category.name)
        .outerjoin(Inventory, Inventory.product_id == Product.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .where(*filters)
    )

    if low_stock_only:
        base = base.where(
            func.coalesce(
                Inventory.quantity_on_hand, ZERO
            ) <= func.coalesce(Inventory.minimum_quantity, ZERO)
        )

    total = db.execute(
        select(func.count()).select_from(base.subquery())
    ).scalar_one()

    rows = (
        db.execute(
            base.order_by(Product.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .all()
    )

    items = []
    for product, inventory, category_name in rows:
        on_hand = (
            inventory.quantity_on_hand if inventory else ZERO
        )
        minimum = inventory.minimum_quantity if inventory else ZERO

        items.append(
            {
                "product_id": product.id,
                "sku": product.sku,
                "product_name": product.name,
                "category_name": category_name,
                "quantity_on_hand": on_hand,
                "minimum_quantity": minimum,
                "low_stock": bool(on_hand <= minimum),
            }
        )

    return items, int(total)


def list_movements(
    db: Session,
    company_id: int,
    *,
    product_id: int | None = None,
    movement_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    filters = [InventoryMovement.company_id == company_id]

    if product_id is not None:
        filters.append(InventoryMovement.product_id == product_id)

    if movement_type:
        filters.append(InventoryMovement.movement_type == movement_type)

    total = db.execute(
        select(func.count())
        .select_from(InventoryMovement)
        .where(*filters)
    ).scalar_one()

    rows = (
        db.execute(
            select(InventoryMovement, Product.name)
            .join(Product, InventoryMovement.product_id == Product.id)
            .where(*filters)
            .order_by(
                InventoryMovement.created_at.desc(),
                InventoryMovement.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .all()
    )

    items = [
        {
            "id": movement.id,
            "product_id": movement.product_id,
            "product_name": product_name,
            "movement_type": movement.movement_type,
            "quantity": movement.quantity,
            "reason": movement.reason,
            "sale_id": movement.sale_id,
            "created_at": movement.created_at,
        }
        for movement, product_name in rows
    ]

    return items, int(total)


# ---------------------------------------------------------------
# Escritura (transaccional)
# ---------------------------------------------------------------
def _get_or_create_inventory(
    db: Session,
    company_id: int,
    product_id: int,
    now: datetime,
) -> Inventory:
    """Obtiene la fila de stock o la crea con 0 si no existe."""
    inventory = db.execute(
        select(Inventory).where(
            Inventory.company_id == company_id,
            Inventory.product_id == product_id,
        )
    ).scalar_one_or_none()

    if inventory is None:
        inventory = Inventory(
            company_id=company_id,
            product_id=product_id,
            quantity_on_hand=ZERO,
            minimum_quantity=ZERO,
            updated_at=now,
        )
        db.add(inventory)
        db.flush()

    return inventory


def apply_movement(
    db: Session,
    company_id: int,
    user_id: int,
    data: InventoryMovementInput,
) -> dict:
    """Aplica entrada / salida / ajuste de stock con trazabilidad.

    entrada : quantity_on_hand += quantity
    salida  : quantity_on_hand -= quantity  (valida stock)
    ajuste  : quantity_on_hand  = quantity  (fija el valor absoluto)
    """
    if data.movement_type not in {"entrada", "salida", "ajuste"}:
        raise InventoryError(
            "movement_type debe ser 'entrada', 'salida' o 'ajuste'"
        )

    product = db.execute(
        select(Product).where(
            Product.id == data.product_id,
            Product.company_id == company_id,
        )
    ).scalar_one_or_none()

    if product is None:
        raise InventoryError("El producto indicado no existe")
    if not product.is_active:
        raise InventoryError(f"El producto '{product.name}' está inactivo")

    now = _now()
    inventory = _get_or_create_inventory(
        db, company_id, data.product_id, now
    )
    before = inventory.quantity_on_hand

    if data.movement_type == "entrada":
        new_value = before + data.quantity
        reason = data.reason or "Entrada manual"

    elif data.movement_type == "salida":
        if data.quantity > before:
            raise InventoryError(
                f"Stock insuficiente de '{product.name}' "
                f"(disponible: {before}, solicitado: {data.quantity})"
            )
        new_value = before - data.quantity
        reason = data.reason or "Salida manual"

    else:  # ajuste
        new_value = data.quantity
        reason = data.reason or f"Ajuste (antes: {before})"

    inventory.quantity_on_hand = new_value
    inventory.updated_at = now

    movement = InventoryMovement(
        company_id=company_id,
        product_id=data.product_id,
        user_id=user_id,
        sale_id=data.sale_id,
        movement_type=data.movement_type,
        quantity=data.quantity,
        reason=reason,
        created_at=now,
    )
    db.add(movement)

    db.commit()
    db.refresh(movement)

    return {
        "movement": movement,
        "product_name": product.name,
        "previous_quantity": before,
        "new_quantity": new_value,
    }