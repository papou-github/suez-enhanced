"""SUEZ Enhanced integration."""
from datetime import date, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from pysuez.suez_client import SuezClient, TelemetryMode

from .const import DOMAIN, PLATFORMS, CONF_COUNTER_ID
from .statistics_sync import async_continue_history, async_last_history_day
from .consumption import consumption_summary
from .cost_history import cost_history
from .history import DailyReading, daily_readings
from .recorder_history import async_recorder_daily_readings

_LOGGER = logging.getLogger(__name__)
MAX_BACKFILL_DAYS = 365
FETCH_WINDOW_DAYS = 14
YEAR_CACHE_VERSION = 1


class SuezCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(hours=6))
        self.entry = entry
        self._year_cache = {}
        self._year_cache_year = None
        self._year_store = Store(hass, YEAR_CACHE_VERSION, f"{DOMAIN}_year_cache_{entry.entry_id}")

    async def async_load_year_cache(self):
        """Restore validated historical readings before the first API refresh."""
        try:
            saved = await self._year_store.async_load()
            if not isinstance(saved, dict):
                return
            year = dt_util.now().year
            if (saved.get("year") != year
                    or saved.get("counter_id") != str(self.entry.data[CONF_COUNTER_ID])):
                return
            restored = {}
            for item in saved.get("readings", []):
                day = date.fromisoformat(item["day"])
                if day.year != year:
                    raise ValueError("Cached reading belongs to another year")
                reading = DailyReading(
                    day=day,
                    liters=float(item["liters"]),
                    meter_index_liters=(
                        float(item["index"]) if item["index"] is not None else None
                    ),
                )
                restored[day] = reading
            # Reuse the existing validation rules for SUEZ telemetry.
            validated = daily_readings([
                type("CachedMeasure", (), {
                    "date": reading.day,
                    "volume": reading.liters,
                    "index": reading.meter_index_liters,
                })()
                for reading in restored.values()
            ])
            if len(validated) != len(restored):
                raise ValueError("Invalid cached readings")
            self._year_cache = {reading.day: reading for reading in validated}
            self._year_cache_year = year
            _LOGGER.debug("Restored %d SUEZ annual readings from cache", len(validated))
        except (ValueError, TypeError, KeyError, OSError) as exc:
            _LOGGER.warning("SUEZ annual cache ignored: %s", exc)

    async def async_save_year_cache(self):
        """Persist validated older readings without storing account credentials."""
        await self._year_store.async_save({
            "year": self._year_cache_year,
            "counter_id": str(self.entry.data[CONF_COUNTER_ID]),
            "readings": [
                {
                    "day": reading.day.isoformat(),
                    "liters": reading.liters,
                    "index": reading.meter_index_liters,
                }
                for reading in sorted(self._year_cache.values(), key=lambda r: r.day)
            ],
        })

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
        try:
            await client._connect()
            recent = await client.fetch_telemetry(
                TelemetryMode.DAILY, today - timedelta(days=35), today
            )
            valid = [m for m in recent if m.index is not None]
            if not valid:
                raise UpdateFailed("No valid SUEZ meter index returned")
            latest = max(valid, key=lambda m: m.date)
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
                    measures = list(recent)
                    earliest = today - timedelta(days=35)
                    if last_day < earliest:
                        # Fetch older windows chronologically, bounded to a year.
                        cursor = max(
                            last_day - timedelta(days=1),
                            today - timedelta(days=MAX_BACKFILL_DAYS),
                        )
                        while cursor < earliest:
                            end = min(cursor + timedelta(days=FETCH_WINDOW_DAYS), earliest)
                            measures.extend(await client.fetch_telemetry(
                                TelemetryMode.DAILY, cursor, end
                            ))
                            cursor = end
                    write = self.entry.options.get("history_sync_enabled", True) is True
                    preview = await async_continue_history(
                        self.hass, str(data[CONF_COUNTER_ID]), measures, write=write
                    )
                    diagnostics["history_status"] = (
                        "import_requested" if write and preview["new_days"]
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
                # Fresh API values take precedence over recorded values for the
                # overlapping recent period, without rewriting old statistics.
                year_measures = [
                    type("Measure", (), {
                        "date": reading.day,
                        "volume": reading.liters,
                        "index": reading.meter_index_liters,
                    })()
                    for reading in recorded
                    if reading.day < today - timedelta(days=35)
                ]
                year_measures.extend(recent)
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
            await client.close_session()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = SuezCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return ok
