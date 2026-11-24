"""The probe's calibrated moisture sensor, and its battery and raw AD readings."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import (
    Event,
    EventStateChangedData,
    EventStateReportedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_state_report_event,
    async_track_time_interval,
)
from homeassistant.util import dt as dt_util

from .calibration import calibrated_moisture, calibration_keys, reading_of
from .const import (
    CONF_BATTERY_SOURCE,
    CONF_MOISTURE_SOURCE,
    CONF_RAW_SOURCE,
    CONF_STALE_MINUTES,
    calibration_signal,
)
from .device import probe_device_info, remove_unused_entities


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the moisture sensor, and a copy of each optional source on the probe's device."""
    entities: list[SensorEntity] = [MoistureSensor(entry)]
    if CONF_RAW_SOURCE in entry.options:
        entities.append(RawSensor(entry))
    if CONF_BATTERY_SOURCE in entry.options:
        entities.append(BatterySensor(entry))
    remove_unused_entities(
        hass,
        entry,
        "sensor",
        [key for key, source in _COPIES.items() if source not in entry.options],
    )
    async_add_entities(entities)


_STALE_CHECK = timedelta(seconds=30)


class _SourceSensor(SensorEntity):
    """A sensor computed from one source entity's state."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, key: str, source: str) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = probe_device_info(entry)
        self._source = source

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_track_state_change_event(self.hass, self._source, self._source_changed)
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, calibration_signal(self._entry.entry_id), self._refresh
            )
        )
        # A repeated value is reported, not changed; it still counts against the timeout.
        self.async_on_remove(
            async_track_state_report_event(self.hass, self._source, self._source_reported)
        )
        self.async_on_remove(async_track_time_interval(self.hass, self._check_stale, _STALE_CHECK))
        self._update(self.hass.states.get(self._source))

    @callback
    def _source_changed(self, event: Event[EventStateChangedData]) -> None:
        self._update(event.data["new_state"])
        self.async_write_ha_state()

    @callback
    def _refresh(self) -> None:
        self._update(self.hass.states.get(self._source))
        self.async_write_ha_state()

    @callback
    def _source_reported(self, _event: Event[EventStateReportedData]) -> None:
        self._check_stale()

    @callback
    def _check_stale(self, _now: datetime | None = None) -> None:
        was_available = self._attr_available
        self._update(self.hass.states.get(self._source))
        if self._attr_available != was_available:
            self.async_write_ha_state()

    @callback
    def _update(self, state: State | None) -> None:
        reading = reading_of(state)
        self._attr_available = reading is not None and not self._stale(state)
        self._attr_native_value = None if reading is None else self._value(reading)

    def _stale(self, state: State | None) -> bool:
        minutes = self._entry.options.get(CONF_STALE_MINUTES, 0)
        # last_reported also moves when a source repeats the same value.
        return (
            state is not None
            and minutes > 0
            and dt_util.utcnow() - state.last_reported > timedelta(minutes=minutes)
        )

    def _value(self, reading: float) -> float:
        return reading


class MoistureSensor(_SourceSensor):
    """Soil moisture from the source reading and the probe's calibration."""

    _attr_device_class = SensorDeviceClass.MOISTURE
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 0

    def __init__(self, entry: ConfigEntry) -> None:
        options = entry.options
        super().__init__(
            entry, "moisture", options.get(CONF_RAW_SOURCE) or options[CONF_MOISTURE_SOURCE]
        )

    def _value(self, reading: float) -> float:
        low, high = calibration_keys(self._entry.options)
        return calibrated_moisture(reading, self._entry.options[low], self._entry.options[high])


class RawSensor(_SourceSensor):
    """The raw AD reading, so it sits on the probe's device next to the moisture it feeds."""

    _attr_translation_key = "raw_ad"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry, "raw_ad", entry.options[CONF_RAW_SOURCE])


class BatterySensor(_SourceSensor):
    """The probe's battery, as reported by the battery source."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry, "battery", entry.options[CONF_BATTERY_SOURCE])


_COPIES = {"raw_ad": CONF_RAW_SOURCE, "battery": CONF_BATTERY_SOURCE}
