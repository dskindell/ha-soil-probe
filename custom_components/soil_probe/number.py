"""The probe's calibration numbers."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .calibration import calibration_keys
from .const import (
    CONF_AD0,
    CONF_AD100,
    CONF_MODEL,
    CONF_PCT0,
    CONF_PCT100,
    CONF_RAW_SOURCE,
    DOMAIN,
    calibration_signal,
)
from .device import probe_device_info
from .models import MIN_SPAN, MODELS


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the numbers for the source's readings at 0 % and 100 %."""
    low, high = calibration_keys(entry.options)
    if CONF_RAW_SOURCE in entry.options:
        model = MODELS[entry.options[CONF_MODEL]]
        limits = {low: (0, model.ad0_max), high: (MIN_SPAN, model.ad100_max)}
        unit = None
    else:
        limits = {low: (0, 100 - MIN_SPAN), high: (MIN_SPAN, 100)}
        unit = PERCENTAGE
    _remove_other_source_numbers(hass, entry, (low, high))
    async_add_entities(
        CalibrationNumber(entry, key, low, high, *limits[key], unit) for key in (low, high)
    )


def _remove_other_source_numbers(
    hass: HomeAssistant, entry: ConfigEntry, keep: tuple[str, str]
) -> None:
    """Drop the numbers left from the other source type after the source was swapped."""
    registry = er.async_get(hass)
    for key in {CONF_AD0, CONF_AD100, CONF_PCT0, CONF_PCT100} - set(keep):
        if entity_id := registry.async_get_entity_id("number", DOMAIN, f"{entry.entry_id}_{key}"):
            registry.async_remove(entity_id)


class CalibrationNumber(NumberEntity):
    """One of the two calibration points, stored in the entry's options."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_step = 1
    _attr_should_poll = False

    def __init__(
        self,
        entry: ConfigEntry,
        key: str,
        low: str,
        high: str,
        minimum: float,
        maximum: float,
        unit: str | None,
    ) -> None:
        self._entry = entry
        self._key = key
        self._low = low
        self._high = high
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = probe_device_info(entry)
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self) -> float:
        return float(self._entry.options[self._key])

    async def async_set_native_value(self, value: float) -> None:
        options = {**self._entry.options, self._key: int(value)}
        if options[self._high] - options[self._low] < MIN_SPAN:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="span_too_small",
                translation_placeholders={"min_span": str(MIN_SPAN)},
            )
        self.hass.config_entries.async_update_entry(self._entry, options=options)
        self.async_write_ha_state()
        async_dispatcher_send(self.hass, calibration_signal(self._entry.entry_id))
