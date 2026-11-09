"""Opt-in, rate-limited discovery of SUEZ history before Recorder's first day."""
from __future__ import annotations

import asyncio
from datetime import date, timedelta
from homeassistant.util import dt as dt_util
import logging

from pysuez.suez_client import SuezClient, TelemetryMode

from .const import CONF_COUNTER_ID
from .historical_archive import HistoricalArchive
from .recorder_history import async_recorder_daily_readings

_LOGGER = logging.getLogger(__name__)
WINDOW = 14
PAUSE = 300
MAX_YEARS = 5
EMPTY_LIMIT = 4
RETRY_SECONDS = 3600


async def async_discover_older_history(hass, entry) -> None:
    """Archive older API readings without ever changing legacy Recorder statistics.

    Disabled by default until integration testing confirms SUEZ API behavior.
    """
    if entry.options.get("older_history_import_enabled", False) is not True:
        return
    await asyncio.sleep(60)
    counter = str(entry.data[CONF_COUNTER_ID])
    archive = HistoricalArchive(hass, entry.entry_id, counter)
    today = dt_util.now().date()
    first = None
    for year in range(today.year - MAX_YEARS, today.year + 1):
        readings = await async_recorder_daily_readings(hass, counter, year)
        if readings:
            candidate = min(r.day for r in readings)
            first = min(first, candidate) if first is not None else candidate
    if first is None:
        _LOGGER.warning("SUEZ older-history discovery skipped: no Recorder anchor")
        return
    floor = today - timedelta(days=365 * MAX_YEARS)
    stored = await archive.load()
    end = date.fromisoformat(stored["cursor"]) - timedelta(days=1) if stored["cursor"] else first - timedelta(days=1)
    empty = stored["empty_windows"]
    while end >= floor and empty < EMPTY_LIMIT:
        if entry.options.get("older_history_import_enabled", False) is not True:
            return
        start = max(floor, end - timedelta(days=WINDOW - 1))
        client = SuezClient(entry.data["username"], entry.data["password"], entry.data[CONF_COUNTER_ID])
        try:
            await client._connect()
            measures = await client.fetch_telemetry(TelemetryMode.DAILY, start - timedelta(days=1), end)
            if measures is None or not isinstance(measures, (list, tuple)):
                raise ValueError("Invalid SUEZ historical API response")
            # Only commit after a successful API response. An empty response
            # advances the checkpoint but never means 'all history exhausted'.
            valid = [m for m in measures if getattr(m, "volume", None) is not None and start <= m.date <= end]
            stored = await archive.save_window(start, end, valid)
            empty = stored["empty_windows"]
            _LOGGER.info("SUEZ historical archive scanned %s..%s: %d readings", start, end, len(valid))
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("SUEZ older-history discovery retry scheduled at %s", start)
            await asyncio.sleep(RETRY_SECONDS)
            continue
        finally:
            await client.close_session()
        end = start - timedelta(days=1)
        await asyncio.sleep(PAUSE)
    if empty >= EMPTY_LIMIT:
        _LOGGER.info("SUEZ older-history discovery stopped after %d empty windows; availability unconfirmed", empty)
