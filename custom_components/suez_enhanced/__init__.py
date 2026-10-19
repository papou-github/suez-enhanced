"""SUEZ Enhanced integration."""
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from pysuez.suez_client import SuezClient, TelemetryMode

from .const import DOMAIN, PLATFORMS, CONF_COUNTER_ID
from .statistics_sync import async_continue_history, async_last_history_day

_LOGGER = logging.getLogger(__name__)
MAX_BACKFILL_DAYS = 365
FETCH_WINDOW_DAYS = 14


class SuezCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(hours=6))
        self.entry = entry

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
                TelemetryMode.DAILY, today - timedelta(days=14), today
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
                    earliest = today - timedelta(days=14)
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
            return {
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
