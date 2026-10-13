from datetime import datetime
from ipaddress import IPv4Address, IPv6Address

from pydantic import BaseModel, ConfigDict, field_validator


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int | None
    user_id: int | None
    user_name: str | None
    action: str
    entity_type: str
    entity_id: str
    ip_address: str | None
    details: dict
    created_at: datetime

    @field_validator("ip_address", mode="before")
    @classmethod
    def _ip_a_texto(cls, value: object) -> str | None:
        # PostgreSQL devuelve INET como IPv4Address/IPv6Address;
        # en SQLite (shim a String) ya es texto.
        if isinstance(value, (IPv4Address, IPv6Address)):
            return str(value)
        return value if isinstance(value, str) or value is None else str(value)
