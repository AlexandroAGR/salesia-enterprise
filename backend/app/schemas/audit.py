from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
