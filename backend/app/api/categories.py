from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.services import category_service
from app.services.audit_service import record_audit

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
    _: User = Depends(require_permission("products:view")),
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
    _: User = Depends(require_permission("products:view")),
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("products:write")),
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

    record_audit(
        db,
        user=current_user,
        action="category.create",
        entity_type="category",
        entity_id=category.id,
        request=request,
        details={"name": category.name},
    )

    return CategoryOut.model_validate(category)


@router.patch("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("products:write")),
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

    record_audit(
        db,
        user=current_user,
        action="category.update",
        entity_type="category",
        entity_id=category_id,
        request=request,
        details={"fields": sorted(data.keys())},
    )

    return CategoryOut.model_validate(category)


@router.delete("/{category_id}")
def deactivate_category(
    category_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("products:write")),
):
    category = category_service.get_category(
        db, current_user.company_id, category_id
    )

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada",
        )

    category_name = category.name

    category_service.update_category(
        db, category, CategoryUpdate(is_active=False)
    )

    record_audit(
        db,
        user=current_user,
        action="category.delete",
        entity_type="category",
        entity_id=category_id,
        request=request,
        details={"name": category_name},
    )

    return {"id": category_id, "status": "inactive"}
