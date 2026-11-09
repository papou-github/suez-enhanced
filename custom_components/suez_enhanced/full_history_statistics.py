"""Independent Recorder series for verified SUEZ history.

The legacy suez_water series is never modified by this module. Historical
backfill can start at the oldest known day and advance only through a
contiguous prefix. Missing days are never invented.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from math import isfinite
from zoneinfo import ZoneInfo

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMeanType, StatisticMetaData
from homeassistant.components.recorder.statistics import async_add_external_statistics, get_last_statistics
from homeassistant.const import UnitOfVolume
from homeassistant.util.unit_conversion import VolumeConverter

from .history import local_midnight_utc

PARIS = ZoneInfo("Europe/Paris")
SOURCE = "suez_enhanced"
BATCH_DAYS = 14


def full_history_statistic_id(counter_id: str) -> str:
    if not str(counter_id).isdecimal():
        raise ValueError("Invalid meter ID")
    return f"{SOURCE}:{counter_id}_full_history"


def select_new_statistics(
    readings: dict[date, float], last_day: date | None, last_sum: float,
    *, batch_days: int = BATCH_DAYS,
) -> list[StatisticData]:
    """Produce a strictly contiguous, cumulative, bounded append batch."""
    if not isfinite(last_sum) or last_sum < 0:
        raise ValueError("Invalid last sum")
    if not 1 <= batch_days <= BATCH_DAYS:
        raise ValueError("Invalid batch size")
    if not readings:
        return []
    for day, liters in readings.items():
        if not isinstance(day, date) or not isinstance(liters, (int, float)) or not isfinite(liters) or liters < 0:
            raise ValueError("Invalid historical reading")
    day = min(readings) if last_day is None else last_day + timedelta(days=1)
    total = float(last_sum)
    batch = []
    while day in readings and len(batch) < batch_days:
        total += readings[day]
        batch.append(StatisticData(start=local_midnight_utc(day), state=readings[day], sum=total))
        day += timedelta(days=1)
    return batch


async def async_append_full_history(hass, counter_id: str, readings: dict[date, float]) -> int:
    """Append a batch to a distinct Recorder statistic, never to legacy."""
    statistic_id = full_history_statistic_id(counter_id)
    existing = await get_instance(hass).async_add_executor_job(
        get_last_statistics, hass, 1, statistic_id, False, {"sum", "state"}
    )
    last_day = None
    last_sum = 0.0
    if existing and existing.get(statistic_id):
        last = existing[statistic_id][0]
        if last.get("start") is None or last.get("sum") is None:
            raise ValueError("Incomplete full-history Recorder checkpoint")
        local = datetime.fromtimestamp(last["start"], timezone.utc).astimezone(PARIS)
        if local.time() != datetime.min.time():
            raise ValueError("Unaligned full-history Recorder checkpoint")
        last_day = local.date() - timedelta(days=1)
        last_sum = float(last["sum"])
    batch = select_new_statistics(readings, last_day, last_sum)
    if not batch:
        return 0
    metadata = StatisticMetaData(
        mean_type=StatisticMeanType.NONE,
        has_sum=True,
        name=f"SUEZ full history {counter_id}",
        source=SOURCE,
        statistic_id=statistic_id,
        unit_class=VolumeConverter.UNIT_CLASS,
        unit_of_measurement=UnitOfVolume.LITERS,
    )
    async_add_external_statistics(hass, metadata, batch)
    return len(batch)

async def async_sync_full_history(hass, entry, history_lock, *, pause_seconds: int = 300) -> None:
    """Copy discovered archive + existing legacy readings to a new series.

    Wait for the older-history scanner to finish before creating the first
    statistic. Once created, the starting day cannot safely move backwards.
    """
    import asyncio
    import logging

    from .const import CONF_COUNTER_ID
    from .historical_archive import HistoricalArchive
    from .recorder_history import async_recorder_daily_readings
    from homeassistant.util import dt as dt_util

    logger = logging.getLogger(__name__)
    counter = str(entry.data[CONF_COUNTER_ID])
    archive = HistoricalArchive(hass, entry.entry_id, counter)
    while True:
        if entry.options.get("older_history_import_enabled", False) is not True:
            return
        async with history_lock:
            payload = await archive.load()
            today = dt_util.now().date()
            days = {
                date.fromisoformat(key): float(value)
                for key, value in payload["days"].items()
            }
            for year in range(today.year - 5, today.year + 1):
                for reading in await async_recorder_daily_readings(hass, counter, year):
                    days[reading.day] = reading.liters
            try:
                count = await async_append_full_history(hass, counter, days)
            except Exception:
                logger.exception("SUEZ full-history Recorder sync paused")
                count = 0
        if count:
            logger.info("SUEZ full-history Recorder queued %d daily statistics", count)
        await asyncio.sleep(pause_seconds if count else 3600)
