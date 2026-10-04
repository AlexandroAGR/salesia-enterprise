from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.customer import CustomerCreate, CustomerOut, CustomerUpdate
from app.services import customer_service

router = APIRouter(
    prefix="/api/customers",
    tags=["Clientes"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=Page[CustomerOut])
def list_customers(
    search: str | None = Query(default=None, min_length=1, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = customer_service.list_customers(
        db,
        current_user.company_id,
        search=search,
        page=page,
        page_size=page_size,
        include_inactive=include_inactive,
    )

    return Page[CustomerOut](
        items=[
            CustomerOut.model_validate(customer) for customer in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = customer_service.get_customer(
        db, current_user.company_id, customer_id
    )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )

    return CustomerOut.model_validate(customer)


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = customer_service.get_customer_by_document(
        db,
        current_user.company_id,
        payload.document_type,
        payload.document_number,
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un cliente con ese tipo y número de documento",
        )

    customer = customer_service.create_customer(
        db, current_user.company_id, payload
    )
    return CustomerOut.model_validate(customer)


@router.patch("/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = customer_service.get_customer(
        db, current_user.company_id, customer_id
    )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )

    data = payload.model_dump(exclude_unset=True)
    document_type = data.get("document_type", customer.document_type)
    document_number = data.get("document_number", customer.document_number)

    existing = customer_service.get_customer_by_document(
        db,
        current_user.company_id,
        document_type,
        document_number,
        exclude_id=customer_id,
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un cliente con ese tipo y número de documento",
        )

    customer = customer_service.update_customer(db, customer, payload)
    return CustomerOut.model_validate(customer)


@router.delete("/{customer_id}")
def deactivate_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    customer = customer_service.get_customer(
        db, current_user.company_id, customer_id
    )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )

    customer_service.update_customer(
        db, customer, CustomerUpdate(is_active=False)
    )

    return {"id": customer_id, "status": "inactive"}
