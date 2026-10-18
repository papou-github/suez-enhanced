"""SUEZ Enhanced integration."""
from datetime import timedelta
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pysuez.suez_client import SuezClient, TelemetryMode
from datetime import date, timedelta as td
from .const import DOMAIN, PLATFORMS, CONF_COUNTER_ID
from .statistics_sync import async_continue_history

_LOGGER = logging.getLogger(__name__)

class SuezCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(hours=6))
        self.entry = entry

    async def _async_update_data(self):
        data = self.entry.data
        client = SuezClient(data["username"], data["password"], data[CONF_COUNTER_ID])
        try:
            await client._connect()
            today = date.today()
            measures = await client.fetch_telemetry(TelemetryMode.DAILY, today - td(days=14), today)
            valid = [m for m in measures if m.index is not None]
            if not valid:
                raise UpdateFailed("No valid SUEZ meter index returned")
            latest = max(valid, key=lambda m: m.date)
            yesterday = next((m for m in measures if m.date == today - td(days=1)), None)
            # Safe default: diagnostic only. Write mode must be explicitly
            # enabled in entry options after a verified HA backup.
            # Any continuity error must not interrupt the meter sensors.
            try:
                write_enabled = self.entry.options.get("history_sync_enabled", False) is True
                preview = await async_continue_history(
                    self.hass, str(data[CONF_COUNTER_ID]), measures,
                    write=write_enabled,
                )
                _LOGGER.info("SUEZ historical continuity result: %s", preview)
            except Exception as exc:
                _LOGGER.warning(
                    "SUEZ historical continuity unavailable: %s: %s",
                    type(exc).__name__, exc,
                )
            return {"index": latest.index / 1000, "index_date": latest.date.isoformat(), "yesterday": yesterday.volume if yesterday and yesterday.volume is not None else None}
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
