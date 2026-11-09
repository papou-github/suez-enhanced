"""Persistent, date-scoped cache for SUEZ daily API telemetry.

Only primitive, validated data is stored. No credentials or API sessions.
"""
from __future__ import annotations

from datetime import date, datetime
from math import isfinite
from types import SimpleNamespace

from homeassistant.helpers.storage import Store

from .history import daily_readings

STORAGE_VERSION = 1


class DailyTelemetryCache:
    def __init__(self, hass, entry_id: str, counter_id: str):
        self._store = Store(hass, STORAGE_VERSION, f"suez_enhanced_daily_{entry_id}")
        self._counter_id = str(counter_id)

    async def async_load(self, today: date):
        payload = await self._store.async_load()
        if not isinstance(payload, dict):
            return None
        if payload.get("counter_id") != self._counter_id or payload.get("day") != today.isoformat():
            return None
        rows = payload.get("readings")
        if not isinstance(rows, list) or len(rows) > 40:
            return None
        measures = []
        try:
            for row in rows:
                if not isinstance(row, dict):
                    return None
                day = date.fromisoformat(row["date"])
                volume = row["volume"]
                index = row["index"]
                if volume is not None and (not isinstance(volume, (int, float)) or not isfinite(volume) or volume < 0):
                    return None
                if index is not None and (not isinstance(index, (int, float)) or not isfinite(index) or index < 0):
                    return None
                measures.append(SimpleNamespace(date=day, volume=volume, index=index))
            daily_readings(measures)
        except (ValueError, TypeError, KeyError, OverflowError):
            return None
        return measures

    async def async_save(self, today: date, measures) -> None:
        rows = []
        for measure in measures:
            day = measure.date
            if isinstance(day, datetime):
                day = day.date()
            if not isinstance(day, date):
                raise ValueError("Invalid SUEZ date in cache")
            rows.append({"date": day.isoformat(), "volume": measure.volume, "index": measure.index})
        if len(rows) > 40:
            raise ValueError("Unexpectedly large SUEZ daily cache")
        # Validate non-negative, finite values before persisting.
        daily_readings(measures)
        await self._store.async_save({
            "counter_id": self._counter_id,
            "day": today.isoformat(),
            "readings": rows,
        })
