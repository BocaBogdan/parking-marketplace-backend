import uuid
from datetime import date as date_
from datetime import datetime, time

from pydantic import BaseModel, model_validator

from parking_marketplace_backend.models.override import OverrideStatus


class OverrideCreate(BaseModel):
    date: date_
    start_time: time
    end_time: time
    status: OverrideStatus

    @model_validator(mode="after")
    def validate_time_range(self) -> "OverrideCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class OverrideRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    date: date_
    start_time: time
    end_time: time
    status: OverrideStatus
    created_at: datetime
    updated_at: datetime
