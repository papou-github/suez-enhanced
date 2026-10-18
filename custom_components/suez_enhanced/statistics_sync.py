"""Opt-in continuation of the existing SUEZ external statistics.

IMPORTANT: No write is performed unless explicitly called with write=True.
The historic statistic ID is intentionally kept unchanged so Energy retains
the existing daily series. Requires confirmation of SUEZ date semantics.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
import logging
from zoneinfo import ZoneInfo

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
)
from homeassistant.const import UnitOfVolume
from homeassistant.util.unit_conversion import VolumeConverter

from .history import daily_readings, local_midnight_utc

_LOGGER = logging.getLogger(__name__)
PARIS = ZoneInfo("Europe/Paris")
LEGACY_SOURCE = "suez_water"


def legacy_statistic_id(counter_id: str) -> str:
    """Existing historical ID (not the live meter index sensor ID)."""
    if not counter_id.isdecimal():
        raise ValueError("Invalid counter ID")
    return f"{LEGACY_SOURCE}:{counter_id}_water_consumption_statistics"


async def async_continue_history(hass, counter_id: str, measures: list, *,
                                 write: bool = False) -> dict:
    """Preview or append *complete, consecutive* SUEZ daily statistics.

    A dry-run is the default. Never overwrite an existing timestamp, never
    fill a missing reading with a guessed zero, and never create a new series
    when the expected historical series cannot be found.
    """
    statistic_id = legacy_statistic_id(counter_id)
    existing = await get_instance(hass).async_add_executor_job(
        get_last_statistics, hass, 1, statistic_id, True, set()
    )
    if not existing or not existing.get(statistic_id):
        raise ValueError("Historical SUEZ statistics not found; refusing to create")
    last = existing[statistic_id][0]
    if last.get("sum") is None or last.get("start") is None:
        raise ValueError("Historical SUEZ statistics have no usable sum/start")
    last_start = datetime.fromtimestamp(last["start"], tz=ZoneInfo("UTC"))
    if last_start != last_start.replace(minute=0, second=0, microsecond=0):
        raise ValueError("Last statistic is not on an hour boundary")
    if last_start.astimezone(PARIS).time() != datetime.min.time():
        raise ValueError("Last statistic is not aligned to local midnight")

    # The existing series stores each day's consumption at the *next*
    # Europe/Paris midnight, e.g. 2026-10-16 22:00Z = Oct 17 midnight.
    last_day = last_start.astimezone(PARIS).date() - timedelta(days=1)
    today = datetime.now(PARIS).date()
    readings = daily_readings(measures)
    expected = last_day + timedelta(days=1)
    selected = []
    for reading in readings:
        if reading.day < expected or reading.day >= today:
            continue
        if reading.day != expected:
            break
        selected.append(reading)
        expected += timedelta(days=1)

    cumulative = float(last["sum"])
    statistics: list[StatisticData] = []
    for reading in selected:
        cumulative += reading.liters
        statistics.append(StatisticData(
            start=local_midnight_utc(reading.day),
            state=reading.liters,
            sum=cumulative,
        ))

    preview = {
        "statistic_id": statistic_id,
        "last_recorded_day": last_day.isoformat(),
        "last_sum_liters": float(last["sum"]),
        "new_days": len(statistics),
        "first_new_day": selected[0].day.isoformat() if selected else None,
        "last_new_day": selected[-1].day.isoformat() if selected else None,
        "new_sum_liters": cumulative,
        "write_enabled": write,
    }
    _LOGGER.info("SUEZ statistics continuity preview: %s", preview)

    if write and statistics:
        metadata = StatisticMetaData(
            mean_type=StatisticMeanType.NONE,
            has_sum=True,
            name=f"Suez water Consumption {counter_id}",
            source=LEGACY_SOURCE,
            statistic_id=statistic_id,
            unit_class=VolumeConverter.UNIT_CLASS,
            unit_of_measurement=UnitOfVolume.LITERS,
        )
        async_add_external_statistics(hass, metadata, statistics)
    return preview
