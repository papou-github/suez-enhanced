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
    end = datetime(year + 1, 1, 1, tzinfo=PARIS).astimezone(timezone.utc)
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


async def async_recorder_multi_year_summary(hass, counter_id: str, first_year: int, last_year: int, price_per_m3: float) -> dict:
    """Summarize recorded days by calendar year, without modifying statistics.

    Only confirmed Recorder days are counted. Incomplete years are explicitly
    marked and never represented as a complete year's consumption.
    """
    from datetime import date
    from calendar import isleap
    from math import isfinite

    if first_year > last_year or last_year - first_year > 20:
        raise ValueError("Invalid multi-year summary range")
    if not isfinite(price_per_m3) or price_per_m3 < 0:
        raise ValueError("Invalid price")
    result = {}
    for year in range(first_year, last_year + 1):
        readings = await async_recorder_daily_readings(hass, counter_id, year)
        if not readings:
            continue
        liters = sum(r.liters for r in readings)
        expected_days = 366 if isleap(year) else 365
        days = {r.day for r in readings}
        result[str(year)] = {
            "liters": round(liters, 3),
            "m3": round(liters / 1000, 3),
            "estimated_cost_eur": round(liters / 1000 * price_per_m3, 2)
                if price_per_m3 > 0 else None,
            "recorded_days": len(days),
            "expected_days": expected_days,
            "complete": len(days) == expected_days,
            "first_day": min(days).isoformat(),
            "last_day": max(days).isoformat(),
        }
    return result
