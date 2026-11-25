"""The probe's calibrated moisture sensor, and its battery and raw AD readings."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .calibration import moisture_of, moisture_source
from .const import CONF_BATTERY_SOURCE, CONF_RAW_SOURCE
from .device import remove_unused_entities
from .source_entity import SourceEntity


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


class _SourceSensor(SourceEntity, SensorEntity):
    """A sensor whose value is computed from the source reading."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def _apply(self, reading: float | None) -> None:
        self._attr_available = reading is not None
        self._attr_native_value = None if reading is None else self._value(reading)

    def _value(self, reading: float) -> float:
        return reading


class MoistureSensor(_SourceSensor):
    """Soil moisture from the source reading and the probe's calibration."""

    _attr_device_class = SensorDeviceClass.MOISTURE
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 0

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry, "moisture", moisture_source(entry.options))

    def _value(self, reading: float) -> float:
        return moisture_of(self._entry.options, reading)


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
