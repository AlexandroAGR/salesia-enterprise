from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.services import category_service

router = APIRouter(
    prefix="/api/categories",
    tags=["Categorías"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[CategoryOut])
def list_categories(
    search: str | None = Query(default=None, min_length=1, max_length=100),
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = category_service.list_categories(
        db,
        current_user.company_id,
        search=search,
        include_inactive=include_inactive,
    )
    return [CategoryOut.model_validate(item) for item in items]


@router.get("/{category_id}", response_model=CategoryOut)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    category = category_service.get_category(
        db, current_user.company_id, category_id
    )

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada",
        )

    return CategoryOut.model_validate(category)


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = category_service.get_category_by_name(
        db, current_user.company_id, payload.name
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una categoría con ese nombre",
        )

    category = category_service.create_category(
        db, current_user.company_id, payload
    )
    return CategoryOut.model_validate(category)


@router.patch("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    category = category_service.get_category(
        db, current_user.company_id, category_id
    )

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada",
        )

    data = payload.model_dump(exclude_unset=True)
    name = data.get("name", category.name)

    existing = category_service.get_category_by_name(
        db, current_user.company_id, name, exclude_id=category_id
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una categoría con ese nombre",
        )

    category = category_service.update_category(db, category, payload)
    return CategoryOut.model_validate(category)


@router.delete("/{category_id}")
def deactivate_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    category = category_service.get_category(
        db, current_user.company_id, category_id
    )

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada",
        )

    category_service.update_category(
        db, category, CategoryUpdate(is_active=False)
    )

    return {"id": category_id, "status": "inactive"}
