from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.analysis import (
    AnalysisOut,
    BayesInput,
    MeanMedianInput,
    ProbabilityInput,
    RandomVariableInput,
)
from app.schemas.common import Page
from app.services import stats_service
from app.services.stats_service import AnalysisError

router = APIRouter(
    prefix="/api/analyses",
    tags=["Análisis estadístico"],
    dependencies=[Depends(get_current_user)],
)


def _http_error(error: AnalysisError) -> HTTPException:
    """Traduce errores del motor a respuestas HTTP."""
    message = str(error)
    if "no existe" in message:
        code = status.HTTP_404_NOT_FOUND
    else:
        code = status.HTTP_400_BAD_REQUEST
    return HTTPException(status_code=code, detail=message)


@router.post(
    "/mean-median",
    status_code=status.HTTP_201_CREATED,
    response_model=AnalysisOut,
)
def mean_median(
    payload: MeanMedianInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Media aritmética y mediana de una variable, con comparación."""
    try:
        analysis = stats_service.run_mean_median(
            db,
            current_user.company_id,
            current_user.id,
            payload.variable_id,
        )
    except AnalysisError as error:
        raise _http_error(error) from error

    return analysis


@router.post(
    "/random-variable",
    status_code=status.HTTP_201_CREATED,
    response_model=AnalysisOut,
)
def random_variable(
    payload: RandomVariableInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Esperanza, varianza y desviación de una variable aleatoria."""
    try:
        analysis = stats_service.run_random_variable(
            db,
            current_user.company_id,
            current_user.id,
            payload.variable_id,
            payload.distribution,
            payload.parameters,
        )
    except AnalysisError as error:
        raise _http_error(error) from error

    return analysis


@router.post(
    "/probability",
    status_code=status.HTTP_201_CREATED,
    response_model=AnalysisOut,
)
def probability(
    payload: ProbabilityInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Probabilidades condicionales e independencia de dos eventos."""
    try:
        analysis = stats_service.run_probability(
            db,
            current_user.company_id,
            current_user.id,
            payload,
        )
    except AnalysisError as error:
        raise _http_error(error) from error

    return analysis


@router.post(
    "/bayes",
    status_code=status.HTTP_201_CREATED,
    response_model=AnalysisOut,
)
def bayes(
    payload: BayesInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Teorema de Bayes: posterior P(A|B) reproducible."""
    try:
        analysis = stats_service.run_bayes(
            db,
            current_user.company_id,
            current_user.id,
            payload,
        )
    except AnalysisError as error:
        raise _http_error(error) from error

    return analysis


@router.get("", response_model=Page[AnalysisOut])
def list_analyses(
    analysis_type: str | None = Query(
        default=None,
        pattern="^(mean_median|random_variable|probability|bayes)$",
    ),
    dataset_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = stats_service.list_analyses(
        db,
        current_user.company_id,
        analysis_type=analysis_type,
        dataset_id=dataset_id,
        page=page,
        page_size=page_size,
    )
    return Page[AnalysisOut](
        items=items, total=total, page=page, page_size=page_size
    )


@router.get("/{analysis_id}", response_model=AnalysisOut)
def get_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        analysis = stats_service.get_analysis(
            db, current_user.company_id, analysis_id
        )
    except AnalysisError as error:
        raise _http_error(error) from error

    return analysis
