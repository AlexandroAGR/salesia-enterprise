from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate
from app.services import category_service, product_service

router = APIRouter(
    prefix="/api/products",
    tags=["Productos"],
    dependencies=[Depends(get_current_user)],
)


def _to_out(product, category_name: str | None) -> ProductOut:
    out = ProductOut.model_validate(product)
    out.category_name = category_name
    return out


@router.get("", response_model=Page[ProductOut])
def list_products(
    search: str | None = Query(default=None, min_length=1, max_length=100),
    category_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = product_service.list_products(
        db,
        current_user.company_id,
        search=search,
        category_id=category_id,
        page=page,
        page_size=page_size,
        include_inactive=include_inactive,
    )

    return Page[ProductOut](
        items=[_to_out(product, name) for product, name in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = product_service.get_product(
        db, current_user.company_id, product_id
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )

    product, category_name = result
    return _to_out(product, category_name)


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = product_service.get_product_by_sku(
        db, current_user.company_id, payload.sku
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un producto con ese SKU",
        )

    if payload.category_id is not None:
        category = category_service.get_category(
            db, current_user.company_id, payload.category_id
        )
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La categoría indicada no existe",
            )

    product = product_service.create_product(
        db, current_user.company_id, payload
    )
    result = product_service.get_product(
        db, current_user.company_id, product.id
    )
    product, category_name = result
    return _to_out(product, category_name)


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = product_service.get_product(
        db, current_user.company_id, product_id
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )

    product, _ = result
    data = payload.model_dump(exclude_unset=True)

    if "sku" in data:
        existing = product_service.get_product_by_sku(
            db, current_user.company_id, data["sku"], exclude_id=product_id
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un producto con ese SKU",
            )

    if data.get("category_id") is not None:
        category = category_service.get_category(
            db, current_user.company_id, data["category_id"]
        )
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La categoría indicada no existe",
            )

    product = product_service.update_product(db, product, payload)
    result = product_service.get_product(
        db, current_user.company_id, product.id
    )
    product, category_name = result
    return _to_out(product, category_name)


@router.delete("/{product_id}")
def deactivate_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = product_service.get_product(
        db, current_user.company_id, product_id
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )

    product, _ = result
    product_service.update_product(db, product, ProductUpdate(is_active=False))

    return {"id": product_id, "status": "inactive"}
