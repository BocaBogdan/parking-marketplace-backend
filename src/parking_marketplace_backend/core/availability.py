import uuid
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from parking_marketplace_backend.models.override import OverrideStatus, SpotOverride
from parking_marketplace_backend.models.reservation import Reservation, ReservationStatus
from parking_marketplace_backend.models.schedule import DayOfWeek, Schedule

WEEKDAY_BY_PY_INDEX = [
    DayOfWeek.MON,
    DayOfWeek.TUE,
    DayOfWeek.WED,
    DayOfWeek.THU,
    DayOfWeek.FRI,
    DayOfWeek.SAT,
    DayOfWeek.SUN,
]


def day_segments(window_from: datetime, window_to: datetime) -> list[tuple[date, time, time]]:
    segments = []
    current_date = window_from.date()
    last_date = window_to.date()

    while current_date <= last_date:
        seg_start = window_from.time() if current_date == window_from.date() else time.min
        seg_end = window_to.time() if current_date == last_date else time.max
        segments.append((current_date, seg_start, seg_end))
        current_date += timedelta(days=1)

    return segments


def fully_covers(seg_start: time, seg_end: time, intervals: list[tuple[time, time]]) -> bool:
    return any(start <= seg_start and end >= seg_end for start, end in intervals)


def overlaps(seg_start: time, seg_end: time, intervals: list[tuple[time, time]]) -> bool:
    return any(start < seg_end and end > seg_start for start, end in intervals)


async def has_overlapping_confirmed_reservation(
    db: AsyncSession, spot_id: uuid.UUID, window_from: datetime, window_to: datetime
) -> bool:
    stmt = (
        select(Reservation.id)
        .where(
            Reservation.spot_id == spot_id,
            Reservation.status == ReservationStatus.CONFIRMED,
            Reservation.start_at < window_to,
            Reservation.end_at > window_from,
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def is_spot_available(db: AsyncSession, spot_id: uuid.UUID, window_from: datetime, window_to: datetime) -> bool:
    if await has_overlapping_confirmed_reservation(db, spot_id, window_from, window_to):
        return False

    schedule_intervals_by_day: dict[DayOfWeek, list[tuple[time, time]]] = {}
    result = await db.execute(select(Schedule).where(Schedule.spot_id == spot_id))
    for schedule in result.scalars():
        schedule_intervals_by_day.setdefault(schedule.day_of_week, []).append(
            (schedule.start_time, schedule.end_time)
        )

    overrides_by_day: dict[date, dict[OverrideStatus, list[tuple[time, time]]]] = {}
    overrides_stmt = select(SpotOverride).where(
        SpotOverride.spot_id == spot_id,
        SpotOverride.date >= window_from.date(),
        SpotOverride.date <= window_to.date(),
    )
    result = await db.execute(overrides_stmt)
    for override in result.scalars():
        overrides_by_day.setdefault(override.date, {}).setdefault(override.status, []).append(
            (override.start_time, override.end_time)
        )

    for seg_date, seg_start, seg_end in day_segments(window_from, window_to):
        day_overrides = overrides_by_day.get(seg_date, {})

        busy_intervals = day_overrides.get(OverrideStatus.BUSY, [])
        if overlaps(seg_start, seg_end, busy_intervals):
            return False

        free_intervals = day_overrides.get(OverrideStatus.FREE, [])
        weekday = WEEKDAY_BY_PY_INDEX[seg_date.weekday()]
        schedule_intervals = schedule_intervals_by_day.get(weekday, [])

        if not fully_covers(seg_start, seg_end, free_intervals) and not fully_covers(
            seg_start, seg_end, schedule_intervals
        ):
            return False

    return True
