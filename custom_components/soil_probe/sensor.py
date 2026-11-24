"""The probe's calibrated moisture sensor."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .calibration import calibrated_moisture, calibration_keys, reading_of
from .const import CONF_MOISTURE_SOURCE, CONF_RAW_SOURCE, calibration_signal
from .device import probe_device_info


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the probe's moisture sensor."""
    async_add_entities([MoistureSensor(entry)])


class MoistureSensor(SensorEntity):
    """Soil moisture from the source reading and the probe's calibration."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.MOISTURE
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_moisture"
        self._attr_device_info = probe_device_info(entry)
        options = entry.options
        self._source: str = options.get(CONF_RAW_SOURCE) or options[CONF_MOISTURE_SOURCE]

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_track_state_change_event(self.hass, self._source, self._source_changed)
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, calibration_signal(self._entry.entry_id), self._calibration_changed
            )
        )
        self._update(self.hass.states.get(self._source))

    @callback
    def _source_changed(self, event: Event[EventStateChangedData]) -> None:
        self._update(event.data["new_state"])
        self.async_write_ha_state()

    @callback
    def _calibration_changed(self) -> None:
        self._update(self.hass.states.get(self._source))
        self.async_write_ha_state()

    def _update(self, state: State | None) -> None:
        reading = reading_of(state)
        self._attr_available = reading is not None
        if reading is None:
            self._attr_native_value = None
            return
        low, high = calibration_keys(self._entry.options)
        self._attr_native_value = calibrated_moisture(
            reading, self._entry.options[low], self._entry.options[high]
        )
