import uuid
from collections import defaultdict
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sqlalchemy import func, select

from parking_marketplace_backend.core.deps import get_current_user
from parking_marketplace_backend.database import get_db
from parking_marketplace_backend.models import User
from parking_marketplace_backend.models.override import OverrideStatus, SpotOverride
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


def _day_segments(window_from: datetime, window_to: datetime) -> list[tuple[date, time, time]]:
    """Split a (possibly multi-day) window into one (date, start_time, end_time) segment per day."""
    segments = []
    current_date = window_from.date()
    last_date = window_to.date()

    while current_date <= last_date:
        seg_start = window_from.time() if current_date == window_from.date() else time.min
        seg_end = window_to.time() if current_date == last_date else time.max
        segments.append((current_date, seg_start, seg_end))
        current_date += timedelta(days=1)

    return segments


def _fully_covers(seg_start: time, seg_end: time, intervals: list[tuple[time, time]]) -> bool:
    return any(start <= seg_start and end >= seg_end for start, end in intervals)


def _overlaps(seg_start: time, seg_end: time, intervals: list[tuple[time, time]]) -> bool:
    return any(start < seg_end and end > seg_start for start, end in intervals)


@router.post("/", response_model=SpotRead)
def create_spot(
        payload: SpotCreate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    new_spot = Spot(
        spot_number=payload.spot_number,
        user_id = current_user.id
    )

    db.add(new_spot)
    try:
        db.commit()
    except:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This spot already exists")

    db.refresh(new_spot)

    return new_spot

@router.get("/mine", response_model=list[SpotRead])
def get_my_spots(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    stmt = (
        select(Spot)
        .where(Spot.user_id == current_user.id)
        .order_by(Spot.spot_number.asc())
    )
    return db.scalars(stmt).all()

@router.get("/available", response_model=list[SpotRead])
def get_available_spots(
        from_: datetime = Query(alias="from"),
        to: datetime = Query(),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    if to <= from_:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'to' must be after 'from'",
        )

    approved_spots = db.scalars(select(Spot).where(Spot.status == SpotStatus.APPROVED)).all()
    if not approved_spots:
        return []

    spot_ids = [spot.id for spot in approved_spots]

    schedules_by_spot: dict[uuid.UUID, dict[DayOfWeek, list[tuple[time, time]]]] = defaultdict(lambda: defaultdict(list))
    for schedule in db.scalars(select(Schedule).where(Schedule.spot_id.in_(spot_ids))):
        schedules_by_spot[schedule.spot_id][schedule.day_of_week].append((schedule.start_time, schedule.end_time))

    overrides_by_spot: dict[uuid.UUID, dict[date, dict[OverrideStatus, list[tuple[time, time]]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    overrides_stmt = select(SpotOverride).where(
        SpotOverride.spot_id.in_(spot_ids),
        SpotOverride.date >= from_.date(),
        SpotOverride.date <= to.date(),
    )
    for override in db.scalars(overrides_stmt):
        overrides_by_spot[override.spot_id][override.date][override.status].append(
            (override.start_time, override.end_time)
        )

    segments = _day_segments(from_, to)

    available_spots = []
    for spot in approved_spots:
        spot_schedules = schedules_by_spot.get(spot.id, {})
        spot_overrides = overrides_by_spot.get(spot.id, {})

        is_available = True
        for seg_date, seg_start, seg_end in segments:
            day_overrides = spot_overrides.get(seg_date, {})

            busy_intervals = day_overrides.get(OverrideStatus.BUSY, [])
            if _overlaps(seg_start, seg_end, busy_intervals):
                is_available = False
                break

            free_intervals = day_overrides.get(OverrideStatus.FREE, [])
            weekday = _WEEKDAY_BY_PY_INDEX[seg_date.weekday()]
            schedule_intervals = spot_schedules.get(weekday, [])

            if not _fully_covers(seg_start, seg_end, free_intervals) and not _fully_covers(
                seg_start, seg_end, schedule_intervals
            ):
                is_available = False
                break

        if is_available:
            available_spots.append(spot)

    return available_spots


@router.put("/{spot_id}", response_model=SpotRead)
def update_spot(
        spot_id: uuid.UUID,
        payload: SpotUpdate,
        db: Session = Depends(get_db)
):
    current_spot = db.scalar(select(Spot).where(Spot.id == spot_id))

    if not current_spot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spot not found")

    update_data = payload.model_dump(exclude_unset=True)

    if "status" in update_data:
        current_spot.status = update_data["status"]
    if "spot_number" in update_data:
        current_spot.spot_number = update_data["spot_number"]

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This spot already exists")


    db.refresh(current_spot)
    return current_spot

@router.delete("/{spot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_spot(spot_id: uuid.UUID, db: Session = Depends(get_db)):
    current_spot = db.scalar(select(Spot).where(Spot.id == spot_id))

    if not current_spot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spot not found")

    db.delete(current_spot)

    db.commit()
    return None