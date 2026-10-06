from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.payment import Payment
from app.models.payment_method import PaymentMethod
from app.models.sale import Sale
from app.schemas.payment import PaymentCreate

ZERO = Decimal("0")


class PaymentError(Exception):
    """Error de regla de negocio de pagos."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------
# Métodos de pago (catálogo)
# ---------------------------------------------------------------
def list_payment_methods(
    db: Session,
    company_id: int,
    *,
    only_active: bool = True,
) -> list[PaymentMethod]:
    filters = [PaymentMethod.company_id == company_id]

    if only_active:
        filters.append(PaymentMethod.is_active.is_(True))

    return list(
        db.execute(
            select(PaymentMethod)
            .where(*filters)
            .order_by(PaymentMethod.name)
        )
        .scalars()
        .all()
    )


# ---------------------------------------------------------------
# Pagos
# ---------------------------------------------------------------
def list_payments(
    db: Session,
    company_id: int,
    *,
    sale_id: int | None = None,
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[tuple[Payment, str]], int]:
    """Pagos con el número de venta asociado."""
    filters = [Sale.company_id == company_id]

    if sale_id is not None:
        filters.append(Payment.sale_id == sale_id)

    if status_filter:
        filters.append(Payment.status == status_filter)

    total = db.execute(
        select(func.count())
        .select_from(Payment)
        .join(Sale, Payment.sale_id == Sale.id)
        .where(*filters)
    ).scalar_one()

    rows = (
        db.execute(
            select(Payment, Sale.sale_number)
            .join(Sale, Payment.sale_id == Sale.id)
            .where(*filters)
            .order_by(Payment.created_at.desc(), Payment.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .all()
    )

    return [(payment, number) for payment, number in rows], int(total)


def get_sale(db: Session, company_id: int, sale_id: int) -> Sale | None:
    return db.execute(
        select(Sale).where(
            Sale.id == sale_id,
            Sale.company_id == company_id,
        )
    ).scalar_one_or_none()


def paid_amount(db: Session, sale_id: int) -> Decimal:
    """Suma ya pagada de una venta."""
    total = db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.sale_id == sale_id,
            Payment.status == "paid",
        )
    ).scalar_one()
    return Decimal(str(total))


def register_payment(
    db: Session,
    company_id: int,
    data: PaymentCreate,
) -> Payment:
    """Registra un pago sobre una venta y marca 'completed' si cubre el total.

    Reglas:
      - la venta debe existir y no estar cancelada/reembolsada
      - el método de pago debe pertenecer a la empresa y estar activo
      - el monto no puede superar el total pendiente
    """
    sale = get_sale(db, company_id, data.sale_id)

    if sale is None:
        raise PaymentError("La venta indicada no existe")

    if sale.status in {"cancelled", "refunded"}:
        raise PaymentError(
            f"La venta {sale.sale_number} está en estado '{sale.status}'"
        )

    if data.currency != sale.currency:
        raise PaymentError(
            f"La moneda del pago ({data.currency}) no coincide "
            f"con la venta ({sale.currency})"
        )

    method = db.execute(
        select(PaymentMethod).where(
            PaymentMethod.id == data.payment_method_id,
            PaymentMethod.company_id == company_id,
            PaymentMethod.is_active.is_(True),
        )
    ).scalar_one_or_none()

    if method is None:
        raise PaymentError("El método de pago indicado no existe")

    already_paid = paid_amount(db, data.sale_id)
    pending = sale.total_amount - already_paid

    if pending <= ZERO:
        raise PaymentError(
            f"La venta {sale.sale_number} ya está saldada"
        )

    if data.amount > pending:
        raise PaymentError(
            f"El monto supera el pendiente ({pending})"
        )

    now = _now()

    payment = Payment(
        sale_id=sale.id,
        payment_method_id=data.payment_method_id,
        amount=data.amount,
        currency=data.currency,
        status="paid",
        reference=data.reference,
        paid_at=now,
        created_at=now,
    )
    db.add(payment)

    # Si el pago cubre el total pendiente → venta completada
    if already_paid + data.amount >= sale.total_amount:
        sale.status = "completed"
        sale.updated_at = now
    else:
        sale.status = "pending"
        sale.updated_at = now

    db.commit()
    db.refresh(payment)
    return payment