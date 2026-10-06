from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# Distribuciones soportadas por el motor de variables aleatorias
DISTRIBUTIONS = ("uniforme", "bernoulli", "binomial", "normal")


class MeanMedianInput(BaseModel):
    variable_id: int = Field(ge=1)


class RandomVariableInput(BaseModel):
    variable_id: int = Field(ge=1)
    distribution: str = Field(pattern="^(uniforme|bernoulli|binomial|normal)$")
    parameters: dict[str, float] = Field(default_factory=dict)


class ProbabilityInput(BaseModel):
    """Probabilidades marginales y conjunta de dos eventos A y B."""

    p_a: float = Field(ge=0, le=1)
    p_b: float = Field(ge=0, le=1)
    p_a_and_b: float = Field(ge=0, le=1)


class BayesInput(BaseModel):
    """Teorema de Bayes: P(A|B) = P(A)·P(B|A) / P(B).

    Si no se envía `probability_b`, el motor lo calcula con la ley de la
    probabilidad total a partir de `probability_b_given_not_a`.
    """

    probability_a: float = Field(gt=0, le=1)
    probability_b_given_a: float = Field(ge=0, le=1)
    probability_b: float | None = Field(default=None, gt=0, le=1)
    probability_b_given_not_a: float | None = Field(
        default=None, ge=0, le=1
    )


class StatisticalResultOut(BaseModel):
    id: int
    metric_name: str
    numeric_result: float | None
    result_payload: dict


class BayesOut(BaseModel):
    probability_a: float
    probability_b_given_a: float
    probability_b: float
    posterior_probability: float
    explanation: str | None


class AnalysisOut(BaseModel):
    id: int
    analysis_type: str
    dataset_id: int | None
    dataset_name: str | None
    status: str
    parameters: dict
    created_at: datetime
    results: list[StatisticalResultOut] = []
    bayes: BayesOut | None = None
