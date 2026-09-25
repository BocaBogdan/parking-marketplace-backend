import uuid
from datetime import datetime, time

from pydantic import BaseModel, Field, field_validator, model_validator

from parking_marketplace_backend.models.schedule import DayOfWeek


class ScheduleCreate(BaseModel):
    days_of_week: list[DayOfWeek] = Field(min_length=1)
    start_time: time
    end_time: time

    @field_validator("days_of_week")
    @classmethod
    def dedupe_days(cls, value: list[DayOfWeek]) -> list[DayOfWeek]:
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def validate_time_range(self) -> "ScheduleCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class ScheduleRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    created_at: datetime
    updated_at: datetime
