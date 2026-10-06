from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class InventoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    product_id: int
    quantity_on_hand: Decimal
    minimum_quantity: Decimal
    updated_at: datetime


class InventoryMovementCreate(BaseModel):
    company_id: int
    product_id: int
    movement_type: str = Field(min_length=1, max_length=30)
    quantity: Decimal = Field(gt=0)
    reason: str | None = Field(default=None, max_length=255)
    sale_id: int | None = None


class InventoryMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    product_id: int
    user_id: int | None
    sale_id: int | None
    movement_type: str
    quantity: Decimal
    reason: str | None
    created_at: datetime