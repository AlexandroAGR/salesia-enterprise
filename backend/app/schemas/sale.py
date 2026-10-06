from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SaleItemInput(BaseModel):
    product_id: int
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0)


class PaymentInput(BaseModel):
    payment_method_id: int
    reference: str | None = Field(default=None, max_length=120)


class SaleCreate(BaseModel):
    customer_id: int | None = None
    items: list[SaleItemInput] = Field(min_length=1)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0)
    tax_rate: Decimal = Field(default=Decimal("0.18"), ge=0, le=1)
    payment: PaymentInput | None = None
    notes: str | None = None


class SaleItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    discount_amount: Decimal
    line_total: Decimal


class SalePaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payment_method_id: int
    payment_method_name: str
    amount: Decimal
    status: str
    reference: str | None
    paid_at: datetime | None


class SaleOut(BaseModel):
    id: int
    sale_number: str
    status: str
    currency: str
    customer_id: int | None
    customer_name: str | None
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    notes: str | None
    sold_at: datetime
    created_at: datetime


class SaleDetailOut(SaleOut):
    items: list[SaleItemOut] = []
    payment: SalePaymentOut | None = None


class InventoryOut(BaseModel):
    product_id: int
    sku: str
    product_name: str
    category_name: str | None
    quantity_on_hand: Decimal
    minimum_quantity: Decimal
    low_stock: bool


class InventoryMovementInput(BaseModel):
    product_id: int
    movement_type: str = Field(pattern="^(entrada|salida|ajuste)$")
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    reason: str | None = Field(default=None, max_length=255)
    sale_id: int | None = None


class InventoryMovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    movement_type: str
    quantity: Decimal
    reason: str | None
    sale_id: int | None
    created_at: datetime


class PaymentMethodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    is_active: bool


class PaymentMethodCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    code: str = Field(min_length=2, max_length=30)
