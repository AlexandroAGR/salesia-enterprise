from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# Clasificación estadística de variables (Semana 07):
#   cualitativa → atributo categórico
#   discreta    → cuantitativa con valores enteros separados
#   continua    → cuantitativa con valores en un intervalo
VARIABLE_TYPES = ("cualitativa", "discreta", "continua")
DATA_TYPES = ("numeric", "text")


class DatasetCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    source_type: str = Field(min_length=2, max_length=50)
    description: str | None = Field(default=None, max_length=1000)


class DatasetVariableCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    data_type: str = Field(pattern="^(numeric|text)$")
    variable_type: str = Field(pattern="^(cualitativa|discreta|continua)$")
    description: str | None = Field(default=None, max_length=500)


class DatasetVariableUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    data_type: str | None = Field(default=None, pattern="^(numeric|text)$")
    variable_type: str | None = Field(
        default=None, pattern="^(cualitativa|discreta|continua)$"
    )
    description: str | None = Field(default=None, max_length=500)


class DatasetVariableOut(BaseModel):
    id: int
    dataset_id: int
    name: str
    data_type: str
    variable_type: str
    description: str | None
    observations_count: int


class DatasetOut(BaseModel):
    id: int
    name: str
    source_type: str
    description: str | None
    variables_count: int
    created_at: datetime


class DatasetDetailOut(DatasetOut):
    variables: list[DatasetVariableOut] = []


class ObservationInput(BaseModel):
    variable_id: int
    numeric_value: float | None = None
    text_value: str | None = Field(default=None, max_length=1000)
    observed_at: datetime | None = None


class ObservationsCreate(BaseModel):
    items: list[ObservationInput] = Field(min_length=1, max_length=1000)


class ObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    variable_id: int
    numeric_value: float | None
    text_value: str | None
    observed_at: datetime | None
    created_at: datetime
