import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from parking_marketplace_backend.core.deps import get_current_user
from parking_marketplace_backend.database import get_db
from parking_marketplace_backend.models import User
from parking_marketplace_backend.models.schedule import Schedule
from parking_marketplace_backend.models.spot import Spot
from parking_marketplace_backend.schemas.schedule import ScheduleCreate, ScheduleRead

router = APIRouter(prefix="/spots/{spot_id}/schedules", tags=["schedules"])


def _get_spot_or_404(db: Session, spot_id: uuid.UUID) -> Spot:
    spot = db.scalar(select(Spot).where(Spot.id == spot_id))
    if not spot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spot not found")
    return spot


def _require_owner(spot: Spot, current_user: User) -> None:
    if spot.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this spot")


@router.get("/", response_model=list[ScheduleRead])
def list_schedules(
        spot_id: uuid.UUID,
        db: Session = Depends(get_db),
):
    _get_spot_or_404(db, spot_id)

    stmt = (
        select(Schedule)
        .where(Schedule.spot_id == spot_id)
        .order_by(Schedule.day_of_week, Schedule.start_time)
    )
    return db.scalars(stmt).all()


@router.post("/", response_model=list[ScheduleRead], status_code=status.HTTP_201_CREATED)
def create_schedules(
        spot_id: uuid.UUID,
        payload: ScheduleCreate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    spot = _get_spot_or_404(db, spot_id)
    _require_owner(spot, current_user)

    new_schedules = [
        Schedule(
            spot_id=spot_id,
            day_of_week=day,
            start_time=payload.start_time,
            end_time=payload.end_time,
        )
        for day in payload.days_of_week
    ]
    db.add_all(new_schedules)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more of these schedules already exist for this spot",
        )

    for schedule in new_schedules:
        db.refresh(schedule)

    return new_schedules


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
        spot_id: uuid.UUID,
        schedule_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    spot = _get_spot_or_404(db, spot_id)
    _require_owner(spot, current_user)

    schedule = db.scalar(
        select(Schedule).where(Schedule.id == schedule_id, Schedule.spot_id == spot_id)
    )
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

    db.delete(schedule)
    db.commit()
    return None
