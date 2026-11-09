"""Bounded, restart-safe forward gap recovery for legacy SUEZ statistics.

Recorder's last committed day is the checkpoint; no separate cursor can
advance ahead of the database. This worker does not prepend older history.
"""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from homeassistant.util import dt as dt_util
from pysuez.suez_client import SuezClient, TelemetryMode

from .const import CONF_COUNTER_ID
from .statistics_sync import async_continue_history, async_last_history_day

_LOGGER = logging.getLogger(__name__)
WINDOW_DAYS = 14
PAUSE_SECONDS = 300


async def async_forward_backfill(hass, entry, lock: asyncio.Lock) -> None:
    """Import one consecutive window per iteration without blocking setup."""
    counter_id = str(entry.data[CONF_COUNTER_ID])
    # Give Home Assistant time to finish initial entity setup.
    await asyncio.sleep(30)
    while True:
        if entry.options.get("history_sync_enabled", True) is not True:
            return
        async with lock:
            last_day = await async_last_history_day(hass, counter_id)
            if last_day is None:
                _LOGGER.warning("SUEZ backfill skipped: no existing legacy history")
                return
            latest = dt_util.now().date() - timedelta(days=2)
            if last_day >= latest:
                return
            start = last_day + timedelta(days=1)
            end = min(start + timedelta(days=WINDOW_DAYS - 1), latest)
            # Include previous day for optional index-delta validation.
            client = SuezClient(
                entry.data["username"], entry.data["password"], entry.data[CONF_COUNTER_ID]
            )
            try:
                await client._connect()
                measures = await client.fetch_telemetry(
                    TelemetryMode.DAILY, start - timedelta(days=1), end
                )
                preview = await async_continue_history(
                    hass, counter_id, measures, write=True
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                _LOGGER.exception("SUEZ backfill paused at %s", start)
                return
            finally:
                await client.close_session()
            if preview["new_days"] == 0:
                _LOGGER.info("SUEZ backfill waiting for missing day %s", start)
                return
            _LOGGER.info(
                "SUEZ background backfill requested %s through %s (%d days)",
                preview["first_new_day"], preview["last_new_day"], preview["new_days"],
            )
        # Allow Recorder to commit the queued statistics before re-reading.
        await asyncio.sleep(PAUSE_SECONDS)
