"""Isolated archive for SUEZ readings older than existing Recorder statistics.

Never prepend to an external Recorder series: its cumulative sum would be
incorrect. Archive rows can later be merged for read-only charts.
"""
from __future__ import annotations

from datetime import date
from math import isfinite

from homeassistant.helpers.storage import Store

from .history import daily_readings

VERSION = 1


class HistoricalArchive:
    def __init__(self, hass, entry_id: str, counter_id: str):
        self._counter_id = str(counter_id)
        self._store = Store(hass, VERSION, f"suez_enhanced_archive_{entry_id}")

    async def load(self) -> dict:
        data = await self._store.async_load()
        if not isinstance(data, dict) or data.get("counter_id") != self._counter_id:
            return {"counter_id": self._counter_id, "days": {}, "cursor": None, "empty_windows": 0}
        days = data.get("days")
        if not isinstance(days, dict) or len(days) > 7500:
            raise ValueError("Invalid historical archive")
        for day, liters in days.items():
            date.fromisoformat(day)
            if not isinstance(liters, (int, float)) or not isfinite(liters) or liters < 0:
                raise ValueError("Invalid historical volume")
        cursor = data.get("cursor")
        if cursor is not None:
            date.fromisoformat(cursor)
        empty_windows = data.get("empty_windows", 0)
        if not isinstance(empty_windows, int) or not 0 <= empty_windows <= 100:
            raise ValueError("Invalid consecutive-empty-window counter")
        data["empty_windows"] = empty_windows
        return data

    async def save_window(self, start: date, end: date, measures) -> dict:
        """Commit one scanned window, even when it contains no valid readings."""
        if end < start or (end - start).days >= 14:
            raise ValueError("Archive window must be at most 14 calendar days")
        data = await self.load()
        # Historical values are immutable in this first implementation.
        # Conflicts are logged by the caller and never silently overwritten.
        valid_readings = [reading for reading in daily_readings(measures) if start <= reading.day <= end]
        for reading in valid_readings:
            if not start <= reading.day <= end:
                continue
            key = reading.day.isoformat()
            old = data["days"].get(key)
            if old is not None and abs(old - reading.liters) > 0.001:
                raise ValueError(f"Conflicting historical reading for {key}")
            data["days"][key] = reading.liters
        data["cursor"] = start.isoformat()
        data["empty_windows"] = 0 if valid_readings else data["empty_windows"] + 1
        await self._store.async_save(data)
        return data
