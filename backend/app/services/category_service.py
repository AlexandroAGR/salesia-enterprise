from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


def _now() -> datetime:
    return datetime.now(timezone.utc)


def list_categories(
    db: Session,
    company_id: int,
    *,
    search: str | None = None,
    include_inactive: bool = False,
) -> list[Category]:
    filters = [Category.company_id == company_id]

    if not include_inactive:
        filters.append(Category.is_active.is_(True))

    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Category.name.ilike(term),
                Category.description.ilike(term),
            )
        )

    statement = (
        select(Category)
        .where(*filters)
        .order_by(Category.name)
    )

    return list(db.execute(statement).scalars().all())


def count_active(db: Session, company_id: int) -> int:
    return int(
        db.execute(
            select(func.count())
            .select_from(Category)
            .where(
                Category.company_id == company_id,
                Category.is_active.is_(True),
            )
        ).scalar_one()
    )


def get_category(db: Session, company_id: int, category_id: int) -> Category | None:
    statement = select(Category).where(
        Category.id == category_id,
        Category.company_id == company_id,
    )
    return db.execute(statement).scalar_one_or_none()


def get_category_by_name(
    db: Session,
    company_id: int,
    name: str,
    exclude_id: int | None = None,
) -> Category | None:
    statement = select(Category).where(
        Category.company_id == company_id,
        Category.name.ilike(name.strip()),
    )

    if exclude_id is not None:
        statement = statement.where(Category.id != exclude_id)

    return db.execute(statement).scalar_one_or_none()


def create_category(db: Session, company_id: int, data: CategoryCreate) -> Category:
    category = Category(
        company_id=company_id,
        name=data.name,
        description=data.description,
        is_active=data.is_active,
        created_at=_now(),
    )

    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(
    db: Session,
    category: Category,
    data: CategoryUpdate,
) -> Category:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)
    return category
