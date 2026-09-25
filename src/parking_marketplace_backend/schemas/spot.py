import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from parking_marketplace_backend.models.spot import SpotStatus


class SpotCreate(BaseModel):
    spot_number: int

class SpotUpdate(BaseModel):
    spot_number: int | None
    status: SpotStatus | None


class SpotRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    status: SpotStatus
    spot_number: int
    created_at: datetime
    updated_at: datetime
