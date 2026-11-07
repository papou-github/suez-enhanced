"""Read existing SUEZ daily readings from Home Assistant long-term statistics."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import isfinite
from zoneinfo import ZoneInfo

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import get_statistics

from .history import DailyReading
from .statistics_sync import legacy_statistic_id

PARIS = ZoneInfo("Europe/Paris")


async def async_recorder_daily_readings(hass, counter_id: str, year: int) -> list[DailyReading]:
    """Read the already-imported daily states without changing Recorder."""
    start = datetime(year, 1, 1, tzinfo=PARIS).astimezone(timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=PARIS).astimezone(timezone.utc)
    statistic_id = legacy_statistic_id(counter_id)
    result = await get_instance(hass).async_add_executor_job(
        get_statistics, hass, start, end, [statistic_id], "day", None, {"state"}
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
