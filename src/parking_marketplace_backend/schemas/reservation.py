import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from parking_marketplace_backend.models.reservation import ReservationStatus


class ReservationCreate(BaseModel):
    spot_id: uuid.UUID
    car_id: uuid.UUID
    start_at: datetime

    @field_validator("start_at")
    @classmethod
    def validate_alignment(cls, value: datetime) -> datetime:
        if value.minute not in (0, 30) or value.second != 0 or value.microsecond != 0:
            raise ValueError("start_at must be aligned to :00 or :30")
        return value


class ReservationRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    spot_id: uuid.UUID
    car_id: uuid.UUID
    start_at: datetime
    end_at: datetime
    status: ReservationStatus
    created_at: datetime
    updated_at: datetime
