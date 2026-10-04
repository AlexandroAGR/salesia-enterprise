from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


def _now() -> datetime:
    return datetime.now(timezone.utc)


def list_products(
    db: Session,
    company_id: int,
    *,
    search: str | None = None,
    category_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
    include_inactive: bool = False,
) -> tuple[list[tuple[Product, str | None]], int]:
    filters = [Product.company_id == company_id]

    if not include_inactive:
        filters.append(Product.is_active.is_(True))

    if category_id is not None:
        filters.append(Product.category_id == category_id)

    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Product.name.ilike(term),
                Product.sku.ilike(term),
                Product.description.ilike(term),
            )
        )

    total = db.execute(
        select(func.count()).select_from(Product).where(*filters)
    ).scalar_one()

    rows = (
        db.execute(
            select(Product, Category.name)
            .outerjoin(Category, Product.category_id == Category.id)
            .where(*filters)
            .order_by(Product.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .all()
    )

    return [(product, category_name) for product, category_name in rows], int(total)


def get_product(
    db: Session,
    company_id: int,
    product_id: int,
) -> tuple[Product, str | None] | None:
    statement = (
        select(Product, Category.name)
        .outerjoin(Category, Product.category_id == Category.id)
        .where(
            Product.id == product_id,
            Product.company_id == company_id,
        )
    )
    row = db.execute(statement).one_or_none()

    if row is None:
        return None

    return row[0], row[1]


def get_product_by_sku(
    db: Session,
    company_id: int,
    sku: str,
    exclude_id: int | None = None,
) -> Product | None:
    statement = select(Product).where(
        Product.company_id == company_id,
        Product.sku == sku.strip(),
    )

    if exclude_id is not None:
        statement = statement.where(Product.id != exclude_id)

    return db.execute(statement).scalar_one_or_none()


def create_product(db: Session, company_id: int, data: ProductCreate) -> Product:
    product = Product(
        company_id=company_id,
        category_id=data.category_id,
        sku=data.sku,
        name=data.name,
        description=data.description,
        unit_price=data.unit_price,
        cost_price=data.cost_price,
        is_active=data.is_active,
        created_at=_now(),
        updated_at=_now(),
    )

    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(
    db: Session,
    product: Product,
    data: ProductUpdate,
) -> Product:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    product.updated_at = _now()

    db.commit()
    db.refresh(product)
    return product
