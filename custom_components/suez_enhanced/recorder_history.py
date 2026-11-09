"""Read existing SUEZ daily readings from Home Assistant long-term statistics."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import isfinite
from zoneinfo import ZoneInfo

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import statistics_during_period

from .history import DailyReading
from .statistics_sync import legacy_statistic_id

PARIS = ZoneInfo("Europe/Paris")


async def async_recorder_daily_readings(hass, counter_id: str, year: int) -> list[DailyReading]:
    """Read the already-imported daily states without changing Recorder."""
    start = datetime(year, 1, 1, tzinfo=PARIS).astimezone(timezone.utc) - timedelta(days=2)
    # Dec 31 consumption is stored at midnight Jan 1 of the next year.
    end = datetime(year + 1, 1, 2, tzinfo=PARIS).astimezone(timezone.utc)
    statistic_id = legacy_statistic_id(counter_id)
    result = await get_instance(hass).async_add_executor_job(
        statistics_during_period, hass, start, end, {statistic_id}, "hour", None, {"state"}
    )
    readings = {}
    for record in result.get(statistic_id, []):
        timestamp = record.get("start")
        value = record.get("state")
        if timestamp is None or not isinstance(value, (int, float)):
            continue
        if not isfinite(value) or value < 0:
            continue
        local_start = datetime.fromtimestamp(timestamp, timezone.utc).astimezone(PARIS)
        # Existing SUEZ statistics use next-day Paris midnight as their start.
        if local_start.time() != datetime.min.time():
            continue
        day = local_start.date() - timedelta(days=1)
        if day.year == year:
            readings[day] = DailyReading(day, float(value), None)
    return sorted(readings.values(), key=lambda reading: reading.day)


def summarize_calendar_year(readings_by_day: dict, year: int, price_per_m3: float) -> dict | None:
    """Summarize observed days, explicitly marking incomplete years."""
    from calendar import isleap
    from datetime import date

    days = {day: liters for day, liters in readings_by_day.items() if day.year == year}
    if not days:
        return None
    total = sum(days.values())
    expected = 366 if isleap(year) else 365
    return {
        "liters": round(total, 3),
        "m3": round(total / 1000, 3),
        "estimated_cost_eur": round(total / 1000 * price_per_m3, 2)
            if price_per_m3 > 0 else None,
        "recorded_days": len(days),
        "expected_days": expected,
        "complete": len(days) == expected,
        "first_day": min(days).isoformat(),
        "last_day": max(days).isoformat(),
    }


async def async_recorder_multi_year_summary(
    hass, counter_id: str, first_year: int, last_year: int,
    price_per_m3: float, archive_days: dict | None = None,
) -> dict:
    """Combine isolated older archive and Recorder, prioritizing Recorder."""
    from datetime import date

    if first_year > last_year or last_year - first_year >= 20:
        raise ValueError("Invalid multi-year summary range")
    if not isfinite(price_per_m3) or price_per_m3 < 0:
        raise ValueError("Invalid price")
    archive_days = archive_days or {}
    archive = {}
    for day_text, liters in archive_days.items():
        day = date.fromisoformat(day_text)
        if not isinstance(liters, (int, float)) or not isfinite(liters) or liters < 0:
            raise ValueError("Invalid archived daily consumption")
        if first_year <= day.year <= last_year:
            archive[day] = float(liters)
    result = {}
    for year in range(first_year, last_year + 1):
        days = {day: value for day, value in archive.items() if day.year == year}
        recorded = await async_recorder_daily_readings(hass, counter_id, year)
        # Recorder wins on overlap; archive never changes Recorder values.
        days.update({reading.day: reading.liters for reading in recorded})
        summary = summarize_calendar_year(days, year, price_per_m3)
        if summary is not None:
            summary["recorder_days"] = len(recorded)
            summary["archive_only_days"] = len(days) - len(recorded)
            result[str(year)] = summary
    return result
