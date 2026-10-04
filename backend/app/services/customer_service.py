from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate


def _now() -> datetime:
    return datetime.now(timezone.utc)


def list_customers(
    db: Session,
    company_id: int,
    *,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
    include_inactive: bool = False,
) -> tuple[list[Customer], int]:
    filters = [Customer.company_id == company_id]

    if not include_inactive:
        filters.append(Customer.is_active.is_(True))

    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Customer.full_name.ilike(term),
                Customer.email.ilike(term),
                Customer.document_number.ilike(term),
                Customer.phone.ilike(term),
            )
        )

    total = db.execute(
        select(func.count()).select_from(Customer).where(*filters)
    ).scalar_one()

    items = (
        db.execute(
            select(Customer)
            .where(*filters)
            .order_by(Customer.full_name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )

    return list(items), int(total)


def get_customer(db: Session, company_id: int, customer_id: int) -> Customer | None:
    statement = select(Customer).where(
        Customer.id == customer_id,
        Customer.company_id == company_id,
    )
    return db.execute(statement).scalar_one_or_none()


def get_customer_by_document(
    db: Session,
    company_id: int,
    document_type: str | None,
    document_number: str | None,
    exclude_id: int | None = None,
) -> Customer | None:
    if not document_type or not document_number:
        return None

    statement = select(Customer).where(
        Customer.company_id == company_id,
        Customer.document_type == document_type,
        Customer.document_number == document_number,
    )

    if exclude_id is not None:
        statement = statement.where(Customer.id != exclude_id)

    return db.execute(statement).scalar_one_or_none()


def create_customer(db: Session, company_id: int, data: CustomerCreate) -> Customer:
    customer = Customer(
        company_id=company_id,
        document_type=data.document_type,
        document_number=data.document_number,
        full_name=data.full_name,
        email=data.email,
        phone=data.phone,
        address=data.address,
        is_active=data.is_active,
        created_at=_now(),
        updated_at=_now(),
    )

    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def update_customer(
    db: Session,
    customer: Customer,
    data: CustomerUpdate,
) -> Customer:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)

    customer.updated_at = _now()

    db.commit()
    db.refresh(customer)
    return customer
