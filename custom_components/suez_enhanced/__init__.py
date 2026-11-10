"""SUEZ Enhanced integration."""
from datetime import timedelta
import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from pysuez.suez_client import SuezClient, TelemetryMode

from .const import DOMAIN, PLATFORMS, CONF_COUNTER_ID
from .statistics_sync import async_continue_history, async_last_history_day
from .consumption import consumption_summary
from .cost_history import cost_history
from .recorder_history import async_recorder_daily_readings, async_recorder_multi_year_summary
from .history import daily_readings
from .year_merge import merge_year_readings
from .daily_cache import DailyTelemetryCache
from .backfill import async_forward_backfill
from .older_history import async_discover_older_history
from .historical_archive import HistoricalArchive
from .full_history_statistics import async_sync_full_history

_LOGGER = logging.getLogger(__name__)
MAX_BACKFILL_DAYS = 365
FETCH_WINDOW_DAYS = 14


class SuezCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(hours=6))
        self.entry = entry
        self.history_lock = asyncio.Lock()
        self.backfill_task = None
        self.older_history_task = None
        self.full_history_task = None
        self._multi_year_cache_day = None
        self._multi_year_cache = {}
        self._multi_year_archive_cursor = None
        self._multi_year_price = None
        self._archive = HistoricalArchive(hass, entry.entry_id, entry.data[CONF_COUNTER_ID])
        self._recent_cache_day = None
        self._recent_cache = None
        self._persistent_cache = DailyTelemetryCache(hass, entry.entry_id, entry.data[CONF_COUNTER_ID])
    async def _async_update_data(self):
        data = self.entry.data
        client = SuezClient(data["username"], data["password"], data[CONF_COUNTER_ID])
        today = dt_util.now().date()
        diagnostics = {
            "last_sync": None,
            "last_reading_day": None,
            "history_last_day": None,
            "history_pending_days": None,
            "history_status": "not_checked",
        }
        connected = False
        try:
            # Avoid repeat downloads once yesterday is available.
            # Missing yesterday is retried every polling interval.
            # Prefer yesterday when published; otherwise retry until it appears.
            target_day = today - timedelta(days=1)
            if self._recent_cache_day != today:
                try:
                    self._recent_cache = await self._persistent_cache.async_load(today)
                except Exception as exc:
                    self._recent_cache = None
                    _LOGGER.warning("SUEZ daily cache load failed: %s: %s", type(exc).__name__, exc)
                self._recent_cache_day = today
            if (
                self._recent_cache_day == today
                and self._recent_cache is not None
                and any(
                    m.date == target_day and m.volume is not None
                    for m in self._recent_cache
                )
            ):
                recent = self._recent_cache
            else:
                await client._connect()
                connected = True
                recent = await client.fetch_telemetry(
                    TelemetryMode.DAILY, today - timedelta(days=35), today
                )
                self._recent_cache_day = today
                self._recent_cache = recent
            valid = [m for m in recent if m.index is not None]
            if not valid:
                raise UpdateFailed("No valid SUEZ meter index returned")
            latest = max(valid, key=lambda m: m.date)
            if connected:
                try:
                    await self._persistent_cache.async_save(today, recent)
                except Exception as exc:
                    _LOGGER.warning("SUEZ daily cache save failed: %s: %s", type(exc).__name__, exc)
            yesterday = next(
                (m for m in recent if m.date == today - timedelta(days=1)), None
            )
            diagnostics["last_reading_day"] = latest.date.isoformat()
            diagnostics["last_sync"] = dt_util.utcnow().isoformat()

            try:
                last_day = await async_last_history_day(
                    self.hass, str(data[CONF_COUNTER_ID])
                )
                if last_day is None:
                    diagnostics["history_status"] = "no_legacy_history"
                else:
                    diagnostics["history_last_day"] = last_day.isoformat()
                    diagnostics["history_pending_days"] = max(
                        0, (today - timedelta(days=2) - last_day).days
                    )
                    # Long gaps are recovered by the bounded background worker.
                    # Never block coordinator startup with many API windows.
                    earliest = today - timedelta(days=35)
                    write = self.entry.options.get("history_sync_enabled", True) is True
                    if last_day < earliest - timedelta(days=1):
                        diagnostics["history_status"] = (
                            "backfill_pending" if write else "disabled"
                        )
                        preview = {"new_days": 0}
                    else:
                        async with self.history_lock:
                            preview = await async_continue_history(
                                self.hass, str(data[CONF_COUNTER_ID]), recent, write=write
                            )
                    diagnostics["history_status"] = (
                        "backfill_pending" if last_day < earliest - timedelta(days=1) and write
                        else "import_requested" if write and preview["new_days"]
                        else "disabled" if not write else "up_to_date"
                    )
                    diagnostics["history_pending_days"] = max(
                        0, diagnostics["history_pending_days"] - preview["new_days"]
                    )
                    _LOGGER.info("SUEZ historical continuity result: %s", preview)
            except Exception as exc:
                diagnostics["history_status"] = "error"
                _LOGGER.warning(
                    "SUEZ historical continuity unavailable: %s: %s",
                    type(exc).__name__, exc,
                )
            try:
                summary = consumption_summary(
                    recent, today, float(self.entry.options.get("price_per_m3", 0.0))
                )
            except (ValueError, TypeError) as exc:
                _LOGGER.warning("SUEZ consumption summary unavailable: %s", exc)
                summary = {
                    "consumption_7d_liters": None,
                    "consumption_month_liters": None,
                    "average_daily_liters": None,
                    "estimated_yesterday_cost_eur": None,
                    "estimated_7d_cost_eur": None,
                    "estimated_month_cost_eur": None,
                    "estimated_annual_cost_eur": None,
                    "consumption_period_end": None,
                    "consumption_month_start": None,
                }
            # Recorder is the canonical local source for imported daily history.
            # Never re-download the entire year on normal refresh.
            year_start = today.replace(month=1, day=1)
            try:
                recorded = await async_recorder_daily_readings(
                    self.hass, str(data[CONF_COUNTER_ID]), today.year
                )
                # Recorder is canonical for days already imported.
                # Recent API telemetry only fills missing Recorder dates;
                # never silently replace historical daily values.
                year_measures = merge_year_readings(recorded, daily_readings(recent))
                year_summary = consumption_summary(
                    year_measures, today,
                    float(self.entry.options.get("price_per_m3", 0.0)),
                )
                summary["estimated_year_to_date_cost_eur"] = year_summary["estimated_year_to_date_cost_eur"]
                summary["consumption_year_start"] = year_summary["consumption_year_start"]
                summary.update(cost_history(
                    year_measures, today,
                    float(self.entry.options.get("price_per_m3", 0.0)),
                ))
                _LOGGER.debug(
                    "SUEZ year history: %d days read from Recorder",
                    len(recorded),
                )
            except Exception as exc:
                _LOGGER.warning(
                    "SUEZ Recorder year history unavailable: %s: %s",
                    type(exc).__name__, exc,
                )
                summary["estimated_year_to_date_cost_eur"] = None
                summary["consumption_year_start"] = year_start.isoformat()
                summary.update({"daily_cost_history": [], "cumulative_cost_history": []})
            # Read-only multi-year summaries, refreshed at most once per day.
            # Do not expose thousands of daily points as sensor attributes.
            try:
                archive_data = await self._archive.load()
                archive_cursor = archive_data["cursor"]
            except Exception as exc:
                archive_data = {"days": {}, "cursor": None}
                archive_cursor = None
                _LOGGER.warning("SUEZ historical archive unavailable: %s: %s", type(exc).__name__, exc)
            annual_price = float(self.entry.options.get("price_per_m3", 0.0))
            if (self._multi_year_cache_day != today
                    or self._multi_year_archive_cursor != archive_cursor
                    or self._multi_year_price != annual_price):
                try:
                    self._multi_year_cache = await async_recorder_multi_year_summary(
                        self.hass, str(data[CONF_COUNTER_ID]),
                        max(2000, today.year - 5), today.year,
                        annual_price,
                        archive_days=archive_data["days"],
                    )
                    self._multi_year_cache_day = today
                    self._multi_year_archive_cursor = archive_cursor
                    self._multi_year_price = annual_price
                except Exception as exc:
                    _LOGGER.warning(
                        "SUEZ multi-year Recorder summary unavailable: %s: %s",
                        type(exc).__name__, exc,
                    )
            summary["multi_year_summary"] = self._multi_year_cache
            diagnostics["archive_oldest_day"] = min(archive_data["days"], default=None)
            diagnostics["archive_reading_days"] = len(archive_data["days"])
            diagnostics["archive_scan_cursor"] = archive_cursor
            diagnostics["archive_empty_windows"] = archive_data.get("empty_windows", 0)
            return {
                **summary,
                "index": latest.index / 1000,
                "index_date": latest.date.isoformat(),
                "yesterday": yesterday.volume if yesterday and yesterday.volume is not None else None,
                **diagnostics,
            }
        except Exception as exc:
            raise UpdateFailed(f"SUEZ API request failed: {type(exc).__name__}") from exc
        finally:
            if connected:
                await client.close_session()


async def _async_full_history_after_discovery(hass, entry, lock):
    """Only start new Recorder series after bounded discovery completes."""
    from datetime import date
    try:
        await async_discover_older_history(hass, entry)
        archive = await HistoricalArchive(
            hass, entry.entry_id, entry.data[CONF_COUNTER_ID]
        ).load()
        today = dt_util.now().date()
        floor = today - timedelta(days=365 * 5)
        cursor = archive.get("cursor")
        exhausted = archive.get("empty_windows", 0) >= 4
        reached_floor = cursor is not None and date.fromisoformat(cursor) <= floor
        if not (exhausted or reached_floor):
            _LOGGER.warning(
                "SUEZ full-history Recorder import postponed: older API scan incomplete"
            )
            return
        await async_sync_full_history(hass, entry, lock)
    except asyncio.CancelledError:
        raise
    except Exception:
        _LOGGER.exception("SUEZ full-history background worker failed")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = SuezCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.backfill_task = hass.async_create_background_task(
        async_forward_backfill(hass, entry, coordinator.history_lock),
        f"suez_enhanced_backfill_{entry.entry_id}",
    )
    if entry.options.get("older_history_import_enabled", False) is True:
        coordinator.older_history_task = hass.async_create_background_task(
            _async_full_history_after_discovery(hass, entry, coordinator.history_lock),
            f"suez_enhanced_older_history_{entry.entry_id}",
        )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        coordinator = hass.data[DOMAIN][entry.entry_id]
        if coordinator.backfill_task is not None:
            coordinator.backfill_task.cancel()
        if coordinator.older_history_task is not None:
            coordinator.older_history_task.cancel()
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return ok
