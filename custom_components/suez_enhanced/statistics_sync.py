"""Append-only continuity of legacy SUEZ external statistics."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
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

from .history import daily_readings, local_midnight_utc, select_consecutive, validate_index_deltas

_LOGGER = logging.getLogger(__name__)
PARIS = ZoneInfo("Europe/Paris")
LEGACY_SOURCE = "suez_water"


def legacy_statistic_id(counter_id: str) -> str:
    if not counter_id.isdecimal():
        raise ValueError("Invalid counter ID")
    return f"{LEGACY_SOURCE}:{counter_id}_water_consumption_statistics"


async def async_last_history_day(hass, counter_id: str):
    """Return the last imported day, or None if no legacy history exists."""
    statistic_id = legacy_statistic_id(counter_id)
    existing = await get_instance(hass).async_add_executor_job(
        get_last_statistics, hass, 1, statistic_id, False, {"sum", "state"}
    )
    if not existing or not existing.get(statistic_id):
        return None
    last = existing[statistic_id][0]
    if last.get("start") is None:
        return None
    timestamp = datetime.fromtimestamp(last["start"], tz=timezone.utc)
    if timestamp.astimezone(PARIS).time() != datetime.min.time():
        raise ValueError("Legacy history is not aligned to Paris midnight")
    return timestamp.astimezone(PARIS).date() - timedelta(days=1)


async def async_continue_history(hass, counter_id: str, measures: list, *, write: bool = False) -> dict:
    """Append complete consecutive days to an existing compatible legacy series."""
    statistic_id = legacy_statistic_id(counter_id)
    existing = await get_instance(hass).async_add_executor_job(
        get_last_statistics, hass, 1, statistic_id, False, {"sum", "state"}
    )
    if not existing or not existing.get(statistic_id):
        raise ValueError("Historical SUEZ statistics not found; refusing to create")
    last = existing[statistic_id][0]
    if last.get("sum") is None or last.get("start") is None:
        raise ValueError("Historical SUEZ statistics have no usable sum/start")
    last_start = datetime.fromtimestamp(last["start"], tz=timezone.utc)
    if last_start.astimezone(PARIS).time() != datetime.min.time():
        raise ValueError("Last statistic is not aligned to Europe/Paris midnight")
    if float(last["sum"]) < 0:
        raise ValueError("Invalid historical cumulative sum")

    last_day = last_start.astimezone(PARIS).date() - timedelta(days=1)
    today = datetime.now(PARIS).date()
    latest_eligible_day = today - timedelta(days=2)
    readings = daily_readings(measures)
    selected = select_consecutive(readings, last_day, latest_eligible_day)
    # Validate available index deltas including the day immediately preceding the import.
    context = [r for r in readings if last_day <= r.day <= latest_eligible_day]
    validate_index_deltas(context)

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
        "latest_eligible_day": latest_eligible_day.isoformat(),
        "first_new_day": selected[0].day.isoformat() if selected else None,
        "last_new_day": selected[-1].day.isoformat() if selected else None,
        "new_sum_liters": cumulative,
        "missing_day": (last_day + timedelta(days=1)).isoformat()
            if not selected and last_day < latest_eligible_day else None,
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
