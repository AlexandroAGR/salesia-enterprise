"""Gestión de datasets: la fuente de datos del motor estadístico.

Un dataset agrupa variables ya clasificadas (cualitativa / discreta /
continua) y sus observaciones, que son las que alimentan los análisis
de la Fase 09.
"""

import math
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.models.dataset_variable import DatasetVariable
from app.models.observation import Observation
from app.schemas.dataset import (
    DatasetCreate,
    DatasetVariableCreate,
    DatasetVariableUpdate,
    ObservationInput,
)


class DatasetError(Exception):
    """Error de regla de negocio de datasets."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------
def list_datasets(
    db: Session,
    company_id: int,
    *,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """Datasets de la empresa con su cantidad de variables."""
    filters = [Dataset.company_id == company_id]

    if search:
        filters.append(Dataset.name.ilike(f"%{search.strip()}%"))

    base = (
        select(Dataset, func.count(DatasetVariable.id))
        .outerjoin(DatasetVariable, DatasetVariable.dataset_id == Dataset.id)
        .where(*filters)
        .group_by(Dataset.id)
    )

    total = db.execute(
        select(func.count()).select_from(base.subquery())
    ).scalar_one()

    rows = (
        db.execute(
            base.order_by(Dataset.created_at.desc(), Dataset.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .all()
    )

    items = [
        {
            "id": dataset.id,
            "name": dataset.name,
            "source_type": dataset.source_type,
            "description": dataset.description,
            "variables_count": variables_count,
            "created_at": dataset.created_at,
        }
        for dataset, variables_count in rows
    ]
    return items, total


def _dataset_or_error(db: Session, company_id: int, dataset_id: int) -> Dataset:
    dataset = db.execute(
        select(Dataset).where(
            Dataset.id == dataset_id,
            Dataset.company_id == company_id,
        )
    ).scalar_one_or_none()

    if dataset is None:
        raise DatasetError(f"El dataset {dataset_id} no existe")

    return dataset


def get_dataset(db: Session, company_id: int, dataset_id: int) -> Dataset:
    """Dataset validado contra la empresa (lanza DatasetError si no existe)."""
    return _dataset_or_error(db, company_id, dataset_id)


def list_dataset_variables(
    db: Session, dataset_id: int
) -> list[tuple[DatasetVariable, int]]:
    return list(
        db.execute(
            select(DatasetVariable, func.count(Observation.id))
            .outerjoin(
                Observation,
                Observation.variable_id == DatasetVariable.id,
            )
            .where(DatasetVariable.dataset_id == dataset_id)
            .group_by(DatasetVariable.id)
            .order_by(DatasetVariable.id)
        ).all()
    )


# ---------------------------------------------------------------
# Escritura
# ---------------------------------------------------------------
def create_dataset(
    db: Session,
    company_id: int,
    user_id: int,
    payload: DatasetCreate,
) -> Dataset:
    dataset = Dataset(
        company_id=company_id,
        name=payload.name.strip(),
        source_type=payload.source_type.strip(),
        description=payload.description,
        created_by=user_id,
        created_at=_now(),
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


def delete_dataset(db: Session, company_id: int, dataset_id: int) -> None:
    dataset = _dataset_or_error(db, company_id, dataset_id)
    db.delete(dataset)
    db.commit()


def _validate_classification(data_type: str, variable_type: str) -> None:
    """Reglas de coherencia entre tipo de dato y clasificación."""
    if variable_type in ("discreta", "continua") and data_type != "numeric":
        raise DatasetError(
            "Una variable discreta o continua debe tener tipo de dato numérico"
        )


def create_variable(
    db: Session,
    company_id: int,
    dataset_id: int,
    payload: DatasetVariableCreate,
) -> DatasetVariable:
    _dataset_or_error(db, company_id, dataset_id)

    _validate_classification(payload.data_type, payload.variable_type)

    duplicated = db.execute(
        select(DatasetVariable).where(
            DatasetVariable.dataset_id == dataset_id,
            func.lower(DatasetVariable.name)
            == payload.name.strip().lower(),
        )
    ).scalar_one_or_none()

    if duplicated is not None:
        raise DatasetError(
            f"Ya existe una variable llamada '{payload.name.strip()}'"
        )

    variable = DatasetVariable(
        dataset_id=dataset_id,
        name=payload.name.strip(),
        data_type=payload.data_type,
        variable_type=payload.variable_type,
        description=payload.description,
    )
    db.add(variable)
    try:
        db.commit()
    except IntegrityError as error:
        # Carrera entre la comprobación previa y el INSERT: la restricción
        # única de la BD manda y se traduce al mismo error de negocio.
        db.rollback()
        raise DatasetError(
            f"Ya existe una variable llamada '{payload.name.strip()}'"
        ) from error
    db.refresh(variable)
    return variable


def update_variable(
    db: Session,
    company_id: int,
    dataset_id: int,
    variable_id: int,
    payload: DatasetVariableUpdate,
) -> DatasetVariable:
    _dataset_or_error(db, company_id, dataset_id)

    variable = db.execute(
        select(DatasetVariable).where(
            DatasetVariable.id == variable_id,
            DatasetVariable.dataset_id == dataset_id,
        )
    ).scalar_one_or_none()

    if variable is None:
        raise DatasetError(f"La variable {variable_id} no existe")

    data = payload.model_fields_set

    # Cambiar el tipo de dato con datos ya cargados dejaría huérfanas
    # las observaciones existentes: se bloquea para no corromper el dataset.
    if "data_type" in data and payload.data_type != variable.data_type:
        has_observations = db.execute(
            select(func.count(Observation.id)).where(
                Observation.variable_id == variable.id
            )
        ).scalar_one()

        if has_observations:
            raise DatasetError(
                "No se puede cambiar el tipo de datos con "
                f"{has_observations} observaciones registradas"
            )

    if "name" in data and payload.name is not None:
        stripped = payload.name.strip()
        if stripped.lower() != variable.name.lower():
            duplicated = db.execute(
                select(DatasetVariable).where(
                    DatasetVariable.dataset_id == dataset_id,
                    func.lower(DatasetVariable.name) == stripped.lower(),
                )
            ).scalar_one_or_none()
            if duplicated is not None:
                raise DatasetError(
                    f"Ya existe una variable llamada '{stripped}'"
                )
        variable.name = stripped

    if "data_type" in data and payload.data_type is not None:
        variable.data_type = payload.data_type

    if "variable_type" in data and payload.variable_type is not None:
        variable.variable_type = payload.variable_type

    if "description" in data:
        variable.description = payload.description

    _validate_classification(variable.data_type, variable.variable_type)

    db.commit()
    db.refresh(variable)
    return variable


def add_observations(
    db: Session,
    company_id: int,
    dataset_id: int,
    items: list[ObservationInput],
) -> int:
    """Registra observaciones en lote validando tipo de dato y clasificación."""
    _dataset_or_error(db, company_id, dataset_id)

    variable_ids = {item.variable_id for item in items}
    variables = {
        variable.id: variable
        for variable in db.execute(
            select(DatasetVariable).where(
                DatasetVariable.id.in_(variable_ids),
                DatasetVariable.dataset_id == dataset_id,
            )
        ).scalars()
    }

    now = _now()
    created = 0

    for item in items:
        variable = variables.get(item.variable_id)
        if variable is None:
            raise DatasetError(
                f"La variable {item.variable_id} no existe en este dataset"
            )

        if variable.data_type == "numeric":
            if item.numeric_value is None:
                raise DatasetError(
                    f"La variable '{variable.name}' es numérica: "
                    "usa numeric_value"
                )
            # JSON admite 1e400 / NaN, que llegan como inf/nan: no son
            # serializables de vuelta a JSON/jsonb ni comparables en JS.
            if not math.isfinite(item.numeric_value):
                raise DatasetError(
                    f"La variable '{variable.name}' admite solo valores "
                    "numéricos finitos"
                )
            observation = Observation(
                dataset_id=dataset_id,
                variable_id=variable.id,
                numeric_value=item.numeric_value,
                text_value=None,
                observed_at=item.observed_at,
                created_at=now,
            )
        else:
            if not item.text_value:
                raise DatasetError(
                    f"La variable '{variable.name}' es cualitativa: "
                    "usa text_value"
                )
            observation = Observation(
                dataset_id=dataset_id,
                variable_id=variable.id,
                numeric_value=None,
                text_value=item.text_value,
                observed_at=item.observed_at,
                created_at=now,
            )

        db.add(observation)
        created += 1

    db.commit()
    return created


# ---------------------------------------------------------------
# Observaciones (lectura)
# ---------------------------------------------------------------
def list_observations(
    db: Session,
    company_id: int,
    dataset_id: int,
    *,
    variable_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Observation], int]:
    _dataset_or_error(db, company_id, dataset_id)

    filters = [Observation.dataset_id == dataset_id]
    if variable_id is not None:
        filters.append(Observation.variable_id == variable_id)

    total = db.execute(
        select(func.count()).select_from(Observation).where(*filters)
    ).scalar_one()

    rows = (
        db.execute(
            select(Observation)
            .where(*filters)
            .order_by(Observation.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return list(rows), total


def numeric_values(
    db: Session, dataset_id: int, variable_id: int
) -> list[float]:
    """Valores numéricos observados de una variable (orden de registro)."""
    rows = db.execute(
        select(Observation.numeric_value)
        .where(
            Observation.dataset_id == dataset_id,
            Observation.variable_id == variable_id,
            Observation.numeric_value.is_not(None),
        )
        .order_by(Observation.id)
    ).scalars()
    return [float(value) for value in rows]
