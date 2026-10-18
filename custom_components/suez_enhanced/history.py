"""Read-only SUEZ history continuity diagnostics.

No recorder writes are performed by this module. It is deliberately safe to
ship before implementing the opt-in historical-statistics writer.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")


@dataclass(frozen=True)
class DailyReading:
    day: date
    liters: float
    meter_index_liters: float | None


def daily_readings(measures: list) -> list[DailyReading]:
    """Normalize daily telemetry, reject duplicates and invalid readings."""
    by_day: dict[date, DailyReading] = {}
    for measure in measures:
        day = measure.date
        if isinstance(day, datetime):
            day = day.date()
        if not isinstance(day, date):
            continue
        volume = measure.volume
        if volume is None or not isinstance(volume, (int, float)):
            continue
        if volume < 0 or volume != volume or volume == float("inf"):
            continue
        index = measure.index
        if index is not None and (
            not isinstance(index, (int, float)) or index < 0
        ):
            index = None
        candidate = DailyReading(day, float(volume), float(index) if index is not None else None)
        if day in by_day and by_day[day] != candidate:
            raise ValueError(f"Conflicting SUEZ telemetry for {day}")
        by_day[day] = candidate
    return sorted(by_day.values(), key=lambda reading: reading.day)


def missing_complete_days(
    readings: list[DailyReading], last_recorded_day: date, today: date
) -> list[DailyReading]:
    """Return complete new days only; never fill missing days with zero."""
    new = [r for r in readings if last_recorded_day < r.day < today]
    expected = last_recorded_day + timedelta(days=1)
    result: list[DailyReading] = []
    for reading in new:
        if reading.day != expected:
            break
        result.append(reading)
        expected += timedelta(days=1)
    return result


def local_midnight_utc(day: date) -> datetime:
    """Daily statistics use the beginning of the next local calendar day."""
    return datetime.combine(day + timedelta(days=1), datetime.min.time(), PARIS).astimezone(
        ZoneInfo("UTC")
    )
