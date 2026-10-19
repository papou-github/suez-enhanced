"""Validation and selection of SUEZ daily readings (no recorder writes)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from math import isfinite
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")


@dataclass(frozen=True)
class DailyReading:
    day: date
    liters: float
    meter_index_liters: float | None


def daily_readings(measures: list) -> list[DailyReading]:
    """Reject contradictory, negative, non-finite and inconsistent telemetry."""
    by_day: dict[date, DailyReading] = {}
    for measure in measures:
        day = measure.date
        if isinstance(day, datetime):
            day = day.astimezone(PARIS).date() if day.tzinfo else day.date()
        if not isinstance(day, date):
            continue
        volume = measure.volume
        if not isinstance(volume, (int, float)) or not isfinite(volume) or volume < 0:
            continue
        index = measure.index
        if index is not None and (
            not isinstance(index, (int, float)) or not isfinite(index) or index < 0
        ):
            index = None
        candidate = DailyReading(day, float(volume), float(index) if index is not None else None)
        if day in by_day and by_day[day] != candidate:
            raise ValueError(f"Conflicting SUEZ telemetry for {day}")
        by_day[day] = candidate
    return sorted(by_day.values(), key=lambda reading: reading.day)


def select_consecutive(
    readings: list[DailyReading], last_day: date, latest_eligible_day: date
) -> list[DailyReading]:
    """Stop at first missing date; never synthesize zero consumption."""
    by_day = {reading.day: reading for reading in readings}
    selected = []
    day = last_day + timedelta(days=1)
    while day <= latest_eligible_day and day in by_day:
        selected.append(by_day[day])
        day += timedelta(days=1)
    return selected


def validate_index_deltas(
    readings: list[DailyReading], *, tolerance_liters: float = 2.0
) -> None:
    """Refuse inconsistent consecutive index/volume pairs when indices exist."""
    for previous, current in zip(readings, readings[1:]):
        if current.day != previous.day + timedelta(days=1):
            continue
        if previous.meter_index_liters is None or current.meter_index_liters is None:
            continue
        delta = current.meter_index_liters - previous.meter_index_liters
        if delta < 0 or abs(delta - current.liters) > tolerance_liters:
            raise ValueError(f"Index/volume mismatch for {current.day}")


def local_midnight_utc(day: date) -> datetime:
    """A daily volume is stored at the next midnight in Europe/Paris."""
    return datetime.combine(
        day + timedelta(days=1), datetime.min.time(), PARIS
    ).astimezone(timezone.utc)
