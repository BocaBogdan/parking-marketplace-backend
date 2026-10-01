import uuid
from collections import defaultdict
from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from parking_marketplace_backend.core.availability import day_segments, fully_covers, overlaps
from parking_marketplace_backend.core.deps import get_current_user
from parking_marketplace_backend.database import get_db
from parking_marketplace_backend.models import User
from parking_marketplace_backend.models.override import OverrideStatus, SpotOverride
from parking_marketplace_backend.models.reservation import Reservation, ReservationStatus
from parking_marketplace_backend.models.schedule import DayOfWeek, Schedule
from parking_marketplace_backend.models.spot import Spot, SpotStatus
from parking_marketplace_backend.schemas.spot import SpotRead, SpotCreate, SpotUpdate

router = APIRouter(prefix="/spots", tags=["spots"])

_WEEKDAY_BY_PY_INDEX = [
    DayOfWeek.MON,
    DayOfWeek.TUE,
    DayOfWeek.WED,
    DayOfWeek.THU,
    DayOfWeek.FRI,
    DayOfWeek.SAT,
    DayOfWeek.SUN,
]


@router.post("/", response_model=SpotRead)
async def create_spot(
        payload: SpotCreate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    new_spot = Spot(
        spot_number=payload.spot_number,
        notes=payload.notes,
        user_id = current_user.id
    )

    db.add(new_spot)
    try:
        await db.commit()
    except:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This spot already exists")

    await db.refresh(new_spot)

    return new_spot

@router.get("/mine", response_model=list[SpotRead])
async def get_my_spots(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Spot)
        .where(Spot.user_id == current_user.id)
        .order_by(Spot.spot_number.asc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/available", response_model=list[SpotRead])
async def get_available_spots(
        from_: datetime = Query(alias="from"),
        to: datetime = Query(),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    if to <= from_:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'to' must be after 'from'",
        )

    result = await db.execute(select(Spot).where(Spot.status == SpotStatus.APPROVED))
    approved_spots = result.scalars().all()
    if not approved_spots:
        return []

    spot_ids = [spot.id for spot in approved_spots]

    schedules_by_spot: dict[uuid.UUID, dict[DayOfWeek, list[tuple[time, time]]]] = defaultdict(lambda: defaultdict(list))
    result = await db.execute(select(Schedule).where(Schedule.spot_id.in_(spot_ids)))
    for schedule in result.scalars():
        schedules_by_spot[schedule.spot_id][schedule.day_of_week].append((schedule.start_time, schedule.end_time))

    overrides_by_spot: dict[uuid.UUID, dict[date, dict[OverrideStatus, list[tuple[time, time]]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    overrides_stmt = select(SpotOverride).where(
        SpotOverride.spot_id.in_(spot_ids),
        SpotOverride.date >= from_.date(),
        SpotOverride.date <= to.date(),
    )
    result = await db.execute(overrides_stmt)
    for override in result.scalars():
        overrides_by_spot[override.spot_id][override.date][override.status].append(
            (override.start_time, override.end_time)
        )

    result = await db.execute(
        select(Reservation.spot_id)
        .where(
            Reservation.spot_id.in_(spot_ids),
            Reservation.status == ReservationStatus.CONFIRMED,
            Reservation.start_at < to,
            Reservation.end_at > from_,
        )
        .distinct()
    )
    reserved_spot_ids = set(result.scalars().all())

    segments = day_segments(from_, to)

    available_spots = []
    for spot in approved_spots:
        if spot.id in reserved_spot_ids:
            continue

        spot_schedules = schedules_by_spot.get(spot.id, {})
        spot_overrides = overrides_by_spot.get(spot.id, {})

        is_available = True
        for seg_date, seg_start, seg_end in segments:
            day_overrides = spot_overrides.get(seg_date, {})

            busy_intervals = day_overrides.get(OverrideStatus.BUSY, [])
            if overlaps(seg_start, seg_end, busy_intervals):
                is_available = False
                break

            free_intervals = day_overrides.get(OverrideStatus.FREE, [])
            weekday = _WEEKDAY_BY_PY_INDEX[seg_date.weekday()]
            schedule_intervals = spot_schedules.get(weekday, [])

            if not fully_covers(seg_start, seg_end, free_intervals) and not fully_covers(
                seg_start, seg_end, schedule_intervals
            ):
                is_available = False
                break

        if is_available:
            available_spots.append(spot)

    return available_spots


@router.put("/{spot_id}", response_model=SpotRead)
async def update_spot(
        spot_id: uuid.UUID,
        payload: SpotUpdate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Spot).where(Spot.id == spot_id))
    current_spot = result.scalar_one_or_none()

    if not current_spot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spot not found")

    if current_spot.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this spot")

    update_data = payload.model_dump(exclude_unset=True)

    if "spot_number" in update_data:
        current_spot.spot_number = update_data["spot_number"]
    if "notes" in update_data:
        current_spot.notes = update_data["notes"]

    # Editing a rejected spot is how an owner re-submits it for review.
    if current_spot.status == SpotStatus.REJECTED:
        current_spot.status = SpotStatus.PENDING
        current_spot.rejection_reason = None

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This spot already exists")


    await db.refresh(current_spot)
    return current_spot

@router.delete("/{spot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_spot(
        spot_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Spot).where(Spot.id == spot_id))
    current_spot = result.scalar_one_or_none()

    if not current_spot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spot not found")

    if current_spot.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this spot")

    if current_spot.status == SpotStatus.INACTIVE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Spot is already inactive")

    current_spot.status = SpotStatus.INACTIVE

    await db.commit()
    return None
