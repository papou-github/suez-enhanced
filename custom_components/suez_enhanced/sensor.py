"""Sensors for SUEZ Enhanced."""
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.helpers.entity import EntityCategory
from homeassistant.const import UnitOfVolume, UnitOfCurrency
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = [SuezIndexSensor(coordinator, entry), SuezYesterdaySensor(coordinator, entry)]
    sensors.extend(
        SuezDiagnosticSensor(coordinator, entry, key, name)
        for key, name in (
            ("last_sync", "Last successful sync"),
            ("last_reading_day", "Last reading day"),
            ("history_last_day", "Last historical day"),
            ("history_pending_days", "Historical days pending"),
            ("history_status", "History sync status"),
        )
    )
    sensors.extend(
        SuezConsumptionSensor(coordinator, entry, key, name, unit)
        for key, name, unit in (
            ("consumption_7d_liters", "Consumption last 7 days", UnitOfVolume.LITERS),
            ("consumption_month_liters", "Consumption this month", UnitOfVolume.LITERS),
            ("average_daily_liters", "Daily average (7 days)", UnitOfVolume.LITERS),
            ("estimated_month_cost_eur", "Estimated month cost", UnitOfCurrency.EUR),
        )
    )
    async_add_entities(sensors)

class SuezBaseSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.data["counter_id"])}, "name": f"SUEZ {entry.data['counter_id']}", "manufacturer": "SUEZ"}

class SuezIndexSensor(SuezBaseSensor):
    _attr_name = "Meter index"
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.data['counter_id']}_index"
    @property
    def native_value(self):
        return self.coordinator.data["index"]
    @property
    def extra_state_attributes(self):
        return {"index_date": self.coordinator.data["index_date"]}

class SuezYesterdaySensor(SuezBaseSensor):
    _attr_name = "Water usage yesterday"
    _attr_device_class = SensorDeviceClass.WATER
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.data['counter_id']}_yesterday"
    @property
    def native_value(self):
        return self.coordinator.data["yesterday"]


class SuezDiagnosticSensor(SuezBaseSensor):
    """Read-only coordinator diagnostic, disabled by default to avoid clutter."""
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, entry, key, name):
        super().__init__(coordinator, entry)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{entry.data['counter_id']}_diagnostic_{key}"

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)


class SuezConsumptionSensor(SuezBaseSensor):
    """Read-only consumption summaries; never contributes to Energy statistics."""
    _attr_icon = "mdi:water"

    def __init__(self, coordinator, entry, key, name, unit):
        super().__init__(coordinator, entry)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{entry.data['counter_id']}_{key}"
        self._attr_native_unit_of_measurement = unit
        if key != "estimated_month_cost_eur":
            self._attr_device_class = SensorDeviceClass.WATER
        else:
            self._attr_icon = "mdi:currency-eur"

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)

    @property
    def extra_state_attributes(self):
        return {
            "period_end": self.coordinator.data.get("consumption_period_end"),
            "month_start": self.coordinator.data.get("consumption_month_start"),
        }
