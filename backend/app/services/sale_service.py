import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.payment import Payment
from app.models.payment_method import PaymentMethod
from app.models.product import Product
from app.models.sale import Sale
from app.models.sale_detail import SaleDetail
from app.schemas.sale import SaleCreate

TWO_PLACES = Decimal("0.01")
ZERO = Decimal("0")


class SaleError(Exception):
    """Error de regla de negocio de ventas.

    El router lo captura y lo convierte en un HTTPException
    (404, 409, etc.). Así los services no dependen de FastAPI.
    """


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _money(value: Decimal) -> Decimal:
    """Redondea a 2 decimales (moneda)."""
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _next_sale_number() -> str:
    """Correlativo único por empresa: V-20261006-A1B2C3."""
    stamp = _now().strftime("%Y%m%d")
    suffix = uuid.uuid4().hex[:6].upper()
    return f"V-{stamp}-{suffix}"


# ---------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------
def list_sales(
    db: Session,
    company_id: int,
    *,
    search: str | None = None,
    status_filter: str | None = None,
    customer_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Sale], int]:
    filters = [Sale.company_id == company_id]

    if status_filter:
        filters.append(Sale.status == status_filter)

    if customer_id is not None:
        filters.append(Sale.customer_id == customer_id)

    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Sale.sale_number.ilike(term),
                Sale.notes.ilike(term),
            )
        )

    total = db.execute(
        select(func.count()).select_from(Sale).where(*filters)
    ).scalar_one()

    items = (
        db.execute(
            select(Sale)
            .where(*filters)
            .order_by(Sale.sold_at.desc(), Sale.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )

    return list(items), int(total)


def get_sale(
    db: Session,
    company_id: int,
    sale_id: int,
) -> Sale | None:
    statement = select(Sale).where(
        Sale.id == sale_id,
        Sale.company_id == company_id,
    )
    return db.execute(statement).scalar_one_or_none()


def get_sale_details(db: Session, sale_id: int) -> list[SaleDetail]:
    statement = (
        select(SaleDetail)
        .where(SaleDetail.sale_id == sale_id)
        .order_by(SaleDetail.id)
    )
    return list(db.execute(statement).scalars().all())


def get_payment(db: Session, sale_id: int) -> Payment | None:
    """Pago de la venta para el detalle, con el método adjunto.

    `amount` es la **suma de todos los pagos** de la venta: si se saldó con
    pagos parciales, el detalle debe mostrar el total pagado (p. ej. 100 +
    254 = 354.00), no sólo el último pago. El método, referencia y fecha
    corresponden al último pago registrado.
    """
    total = db.execute(
        select(func.sum(Payment.amount)).where(Payment.sale_id == sale_id)
    ).scalar_one()

    if total is None:  # sin pagos registrados
        return None

    statement = (
        select(Payment, PaymentMethod.name)
        .join(PaymentMethod, Payment.payment_method_id == PaymentMethod.id)
        .where(Payment.sale_id == sale_id)
        .order_by(Payment.id.desc())
        .limit(1)
    )
    row = db.execute(statement).first()

    if row is None:  # pragma: no cover - imposible con pagos existentes
        return None

    payment, method_name = row
    # Se separa de la sesión para poder responder con el total sin que
    # la mutación en memoria se llegue a persistir en la base de datos.
    db.expunge(payment)
    payment.amount = total
    payment.method_name = method_name  # atributo temporal para el router
    return payment


# ---------------------------------------------------------------
# Escritura (transaccional)
# ---------------------------------------------------------------
def create_sale(
    db: Session,
    company_id: int,
    created_by: int,
    data: SaleCreate,
) -> Sale:
    """Crea la venta completa: cabecera, detalles, pago e inventario.

    Si cualquier validación falla se lanza SaleError y el llamador
    (el router) hará rollback; no se persiste nada.
    """
    # 1) Cliente (opcional, pero si viene debe pertenecer a la empresa)
    if data.customer_id is not None:
        customer = db.execute(
            select(Customer).where(
                Customer.id == data.customer_id,
                Customer.company_id == company_id,
            )
        ).scalar_one_or_none()

        if customer is None:
            raise SaleError("El cliente indicado no existe")
        if not customer.is_active:
            raise SaleError("El cliente está inactivo")

    # 2) Productos: uno por uno, dentro de la misma empresa
    product_ids = {item.product_id for item in data.items}
    products = {
        product.id: product
        for product in db.execute(
            select(Product).where(
                Product.id.in_(product_ids),
                Product.company_id == company_id,
            )
        ).scalars().all()
    }

    for product_id in sorted(product_ids):
        if product_id not in products:
            raise SaleError(f"El producto {product_id} no existe")
        if not products[product_id].is_active:
            raise SaleError(
                f"El producto '{products[product_id].name}' está inactivo"
            )

    # 3) Stock actual de cada producto
    inventories = {
        inv.product_id: inv
        for inv in db.execute(
            select(Inventory).where(
                Inventory.company_id == company_id,
                Inventory.product_id.in_(product_ids),
            )
        ).scalars().all()
    }

    # 4) Cálculo de totales
    #    línea:        qty × precio − descuento de línea
    #    subtotal:     suma de (qty × precio)
    #    descuentos:   descuentos de línea + descuento de la venta
    #    base:         subtotal − descuentos
    #    IGV:          base × tax_rate
    #    total:        base + IGV
    subtotal = ZERO
    line_discount_total = ZERO

    for item in data.items:
        product = products[item.product_id]
        line_gross = (product.unit_price * item.quantity)

        if item.discount_amount > line_gross:
            raise SaleError(
                f"El descuento supera el importe de '{product.name}'"
            )

        subtotal += line_gross
        line_discount_total += item.discount_amount

    discount_total = line_discount_total + data.discount_amount

    if discount_total > subtotal:
        raise SaleError("El descuento total supera el subtotal")

    taxable_base = subtotal - discount_total
    tax_amount = _money(taxable_base * data.tax_rate)
    total_amount = _money(taxable_base + tax_amount)

    # 5) Validar stock antes de escribir nada
    for item in data.items:
        inventory = inventories.get(item.product_id)
        available = inventory.quantity_on_hand if inventory else ZERO

        if item.quantity > available:
            raise SaleError(
                f"Stock insuficiente de '{products[item.product_id].name}' "
                f"(disponible: {available}, solicitado: {item.quantity})"
            )

    # 6) Pago (opcional): si viene, la venta queda 'completed'
    payment_input = data.payment
    if payment_input is not None:
        method = db.execute(
            select(PaymentMethod).where(
                PaymentMethod.id == payment_input.payment_method_id,
                PaymentMethod.company_id == company_id,
                PaymentMethod.is_active.is_(True),
            )
        ).scalar_one_or_none()

        if method is None:
            raise SaleError("El método de pago indicado no existe")

    # ---------------- escritura ----------------
    now = _now()
    status = "completed" if payment_input is not None else "pending"

    sale = Sale(
        company_id=company_id,
        customer_id=data.customer_id,
        employee_id=None,
        created_by=created_by,
        sale_number=_next_sale_number(),
        status=status,
        currency="PEN",
        subtotal=_money(subtotal),
        discount_amount=_money(discount_total),
        tax_amount=tax_amount,
        total_amount=total_amount,
        notes=data.notes,
        sold_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(sale)
    db.flush()  # obtiene sale.id sin confirmar aún

    for item in data.items:
        product = products[item.product_id]
        line_gross = product.unit_price * item.quantity
        line_total = _money(line_gross - item.discount_amount)

        db.add(
            SaleDetail(
                sale_id=sale.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=product.unit_price,
                discount_amount=item.discount_amount,
                line_total=line_total,
                created_at=now,
            )
        )

        # descuento de stock + trazabilidad
        inventory = inventories[item.product_id]
        inventory.quantity_on_hand -= item.quantity
        inventory.updated_at = now

        db.add(
            InventoryMovement(
                company_id=company_id,
                product_id=item.product_id,
                user_id=created_by,
                sale_id=sale.id,
                movement_type="salida",
                quantity=item.quantity,
                reason=f"Venta {sale.sale_number}",
                created_at=now,
            )
        )

    if payment_input is not None:
        db.add(
            Payment(
                sale_id=sale.id,
                payment_method_id=payment_input.payment_method_id,
                amount=total_amount,
                currency="PEN",
                status="paid",
                reference=payment_input.reference,
                paid_at=now,
                created_at=now,
            )
        )

    db.commit()
    db.refresh(sale)
    return sale

def get_product_names(db: Session, product_ids: set[int]) -> dict[int, str]:
    """Mapa {product_id: nombre} para no hacer una consulta por item."""
    if not product_ids:
        return {}

    rows = db.execute(
        select(Product.id, Product.name).where(Product.id.in_(product_ids))
    ).all()

    return {product_id: name for product_id, name in rows}


def get_customer_names(
    db: Session, customer_ids: set[int]
) -> dict[int, str]:
    """Mapa {customer_id: nombre} (el modelo Sale no tiene relación)."""
    if not customer_ids:
        return {}

    rows = db.execute(
        select(Customer.id, Customer.full_name).where(
            Customer.id.in_(customer_ids)
        )
    ).all()

    return {customer_id: name for customer_id, name in rows}