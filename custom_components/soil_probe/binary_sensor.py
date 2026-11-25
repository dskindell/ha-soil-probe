"""Needs water: on when the probe's moisture drops below its low threshold."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .calibration import moisture_of, moisture_source
from .const import (
    CONF_LOW_THRESHOLD,
    CONF_THRESHOLD_MARGIN,
    DEFAULT_LOW_THRESHOLD,
    DEFAULT_THRESHOLD_MARGIN,
)
from .source_entity import SourceEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the probe's Needs water sensor."""
    async_add_entities([NeedsWaterSensor(entry)])


class NeedsWaterSensor(SourceEntity, BinarySensorEntity):
    """On below the threshold; off again only at threshold + margin, so a wobble doesn't flap."""

    _attr_translation_key = "needs_water"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry, "needs_water", moisture_source(entry.options))

    def _apply(self, reading: float | None) -> None:
        options = self._entry.options
        if reading is None:
            self._attr_available = False
            self._attr_is_on = None
            return
        self._attr_available = True
        threshold = options.get(CONF_LOW_THRESHOLD, DEFAULT_LOW_THRESHOLD)
        if threshold == 0:
            self._attr_is_on = False
            return
        moisture = moisture_of(options, reading)
        if moisture < threshold:
            self._attr_is_on = True
        # Inside the margin the state holds; at startup there is none to hold, so off.
        elif (
            moisture >= threshold + options.get(CONF_THRESHOLD_MARGIN, DEFAULT_THRESHOLD_MARGIN)
            or self._attr_is_on is None
        ):
            self._attr_is_on = False
