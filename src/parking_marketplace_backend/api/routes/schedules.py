import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from parking_marketplace_backend.core.deps import get_current_user
from parking_marketplace_backend.database import get_db
from parking_marketplace_backend.models import User
from parking_marketplace_backend.models.schedule import Schedule
from parking_marketplace_backend.models.spot import Spot
from parking_marketplace_backend.schemas.schedule import ScheduleCreate, ScheduleRead

router = APIRouter(prefix="/spots/{spot_id}/schedules", tags=["schedules"])


async def _get_spot_or_404(db: AsyncSession, spot_id: uuid.UUID) -> Spot:
    result = await db.execute(select(Spot).where(Spot.id == spot_id))
    spot = result.scalar_one_or_none()
    if not spot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spot not found")
    return spot


def _require_owner(spot: Spot, current_user: User) -> None:
    if spot.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this spot")


@router.get("/", response_model=list[ScheduleRead])
async def list_schedules(
        spot_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    await _get_spot_or_404(db, spot_id)

    stmt = (
        select(Schedule)
        .where(Schedule.spot_id == spot_id)
        .order_by(Schedule.day_of_week, Schedule.start_time)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=list[ScheduleRead], status_code=status.HTTP_201_CREATED)
async def create_schedules(
        spot_id: uuid.UUID,
        payload: ScheduleCreate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    spot = await _get_spot_or_404(db, spot_id)
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
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more of these schedules already exist for this spot",
        )

    for schedule in new_schedules:
        await db.refresh(schedule)

    return new_schedules


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
        spot_id: uuid.UUID,
        schedule_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    spot = await _get_spot_or_404(db, spot_id)
    _require_owner(spot, current_user)

    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id, Schedule.spot_id == spot_id)
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

    await db.delete(schedule)
    await db.commit()
    return None
