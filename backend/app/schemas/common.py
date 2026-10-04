from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Respuesta paginada estándar de la API."""

    items: list[T]
    total: int
    page: int
    page_size: int
