from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PaymentCreate(BaseModel):
    sale_id: int
    payment_method_id: int
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="PEN", min_length=3, max_length=3)
    reference: str | None = Field(default=None, max_length=100)


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sale_id: int
    payment_method_id: int
    amount: Decimal
    currency: str
    status: str
    reference: str | None
    paid_at: datetime | None
    created_at: datetime