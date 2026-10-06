from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.dataset import (
    DatasetCreate,
    DatasetDetailOut,
    DatasetOut,
    DatasetVariableCreate,
    DatasetVariableOut,
    DatasetVariableUpdate,
    ObservationOut,
    ObservationsCreate,
)
from app.services import dataset_service
from app.services.dataset_service import DatasetError

router = APIRouter(
    prefix="/api/datasets",
    tags=["Datasets"],
    dependencies=[Depends(get_current_user)],
)


def _http_error(error: DatasetError) -> HTTPException:
    """Traduce errores de regla de negocio a respuestas HTTP."""
    message = str(error)
    lowered = message.lower()
    if "no existe" in lowered:
        code = status.HTTP_404_NOT_FOUND
    elif "ya existe" in lowered:
        code = status.HTTP_409_CONFLICT
    else:
        code = status.HTTP_400_BAD_REQUEST
    return HTTPException(status_code=code, detail=message)


def _variable_out(row) -> DatasetVariableOut:
    variable, observations_count = row
    return DatasetVariableOut(
        id=variable.id,
        dataset_id=variable.dataset_id,
        name=variable.name,
        data_type=variable.data_type,
        variable_type=variable.variable_type,
        description=variable.description,
        observations_count=observations_count,
    )


def _detail_out(dataset, variables) -> DatasetDetailOut:
    return DatasetDetailOut(
        id=dataset.id,
        name=dataset.name,
        source_type=dataset.source_type,
        description=dataset.description,
        variables_count=len(variables),
        created_at=dataset.created_at,
        variables=[_variable_out(row) for row in variables],
    )


@router.get("", response_model=Page[DatasetOut])
def list_datasets(
    search: str | None = Query(default=None, min_length=1, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = dataset_service.list_datasets(
        db,
        current_user.company_id,
        search=search,
        page=page,
        page_size=page_size,
    )
    return Page[DatasetOut](
        items=items, total=total, page=page, page_size=page_size
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=DatasetDetailOut,
)
def create_dataset(
    payload: DatasetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = dataset_service.create_dataset(
        db, current_user.company_id, current_user.id, payload
    )
    return _detail_out(dataset, [])


@router.get("/{dataset_id}", response_model=DatasetDetailOut)
def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        dataset = dataset_service.get_dataset(
            db, current_user.company_id, dataset_id
        )
    except DatasetError as error:
        raise _http_error(error) from error

    variables = dataset_service.list_dataset_variables(db, dataset.id)
    return _detail_out(dataset, variables)


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        dataset_service.delete_dataset(
            db, current_user.company_id, dataset_id
        )
    except DatasetError as error:
        raise _http_error(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{dataset_id}/variables",
    status_code=status.HTTP_201_CREATED,
    response_model=DatasetVariableOut,
)
def create_variable(
    dataset_id: int,
    payload: DatasetVariableCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        variable = dataset_service.create_variable(
            db, current_user.company_id, dataset_id, payload
        )
    except DatasetError as error:
        raise _http_error(error) from error

    return DatasetVariableOut(
        id=variable.id,
        dataset_id=variable.dataset_id,
        name=variable.name,
        data_type=variable.data_type,
        variable_type=variable.variable_type,
        description=variable.description,
        observations_count=0,
    )


@router.patch(
    "/{dataset_id}/variables/{variable_id}",
    response_model=DatasetVariableOut,
)
def update_variable(
    dataset_id: int,
    variable_id: int,
    payload: DatasetVariableUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        variable = dataset_service.update_variable(
            db, current_user.company_id, dataset_id, variable_id, payload
        )
        variables = dataset_service.list_dataset_variables(db, dataset_id)
    except DatasetError as error:
        raise _http_error(error) from error

    for row in variables:
        if row[0].id == variable.id:
            return _variable_out(row)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"La variable {variable_id} no existe",
    )


@router.post(
    "/{dataset_id}/observations",
    status_code=status.HTTP_201_CREATED,
)
def add_observations(
    dataset_id: int,
    payload: ObservationsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        created = dataset_service.add_observations(
            db, current_user.company_id, dataset_id, payload.items
        )
    except DatasetError as error:
        raise _http_error(error) from error

    return {"created": created}


@router.get(
    "/{dataset_id}/observations",
    response_model=Page[ObservationOut],
)
def list_observations(
    dataset_id: int,
    variable_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        items, total = dataset_service.list_observations(
            db,
            current_user.company_id,
            dataset_id,
            variable_id=variable_id,
            page=page,
            page_size=page_size,
        )
    except DatasetError as error:
        raise _http_error(error) from error

    return Page[ObservationOut](
        items=items, total=total, page=page, page_size=page_size
    )
