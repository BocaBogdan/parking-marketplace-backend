import uuid
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from parking_marketplace_backend.models.override import OverrideStatus, SpotOverride
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


def fully_covers(seg_start: time, seg_end: time, intervals: list[tuple[time, time]]) -> bool:
    return any(start <= seg_start and end >= seg_end for start, end in intervals)


def overlaps(seg_start: time, seg_end: time, intervals: list[tuple[time, time]]) -> bool:
    return any(start < seg_end and end > seg_start for start, end in intervals)


def is_spot_available(db: Session, spot_id: uuid.UUID, window_from: datetime, window_to: datetime) -> bool:
    """A spot is available for [window_from, window_to) if, for every day the window touches,
    no BUSY override overlaps it and a schedule row or FREE override fully covers it."""
    schedule_intervals_by_day: dict[DayOfWeek, list[tuple[time, time]]] = {}
    for schedule in db.scalars(select(Schedule).where(Schedule.spot_id == spot_id)):
        schedule_intervals_by_day.setdefault(schedule.day_of_week, []).append(
            (schedule.start_time, schedule.end_time)
        )

    overrides_by_day: dict[date, dict[OverrideStatus, list[tuple[time, time]]]] = {}
    overrides_stmt = select(SpotOverride).where(
        SpotOverride.spot_id == spot_id,
        SpotOverride.date >= window_from.date(),
        SpotOverride.date <= window_to.date(),
    )
    for override in db.scalars(overrides_stmt):
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
