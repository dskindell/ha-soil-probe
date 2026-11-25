"""The probe's calibration numbers."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .calibration import check_points, point_limits
from .const import (
    CONF_AD0,
    CONF_AD100,
    CONF_DRY_TARGET,
    CONF_LOW_THRESHOLD,
    CONF_PCT0,
    CONF_PCT100,
    CONF_RAW_SOURCE,
    CONF_STALE_MINUTES,
    CONF_THRESHOLD_MARGIN,
    CONF_WET_TARGET,
    DEFAULT_DRY_TARGET,
    DEFAULT_LOW_THRESHOLD,
    DEFAULT_THRESHOLD_MARGIN,
    DEFAULT_WET_TARGET,
    calibration_signal,
)
from .device import probe_device_info, remove_unused_entities

# Targets of exactly 100 % dry or 0 % wet can't be solved for.
_TARGETS = {
    CONF_DRY_TARGET: (0, 90, DEFAULT_DRY_TARGET),
    CONF_WET_TARGET: (10, 100, DEFAULT_WET_TARGET),
}
# 0 turns the timeout off; a day is far beyond any probe's reporting interval.
_STALE_LIMITS = (0, 1440, 0)
_THRESHOLDS = {
    CONF_LOW_THRESHOLD: (0, 100, DEFAULT_LOW_THRESHOLD),
    CONF_THRESHOLD_MARGIN: (0, 20, DEFAULT_THRESHOLD_MARGIN),
}
_ALL_KEYS = {
    CONF_AD0,
    CONF_AD100,
    CONF_PCT0,
    CONF_PCT100,
    CONF_STALE_MINUTES,
    *_TARGETS,
    *_THRESHOLDS,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the calibration points, and with a raw source the capture targets."""
    raw = CONF_RAW_SOURCE in entry.options
    unit = None if raw else PERCENTAGE
    entities: list[_OptionNumber] = [
        PointNumber(entry, key, minimum, maximum, unit)
        for key, (minimum, maximum) in point_limits(entry.options).items()
    ]
    if raw:
        entities += [
            DefaultedNumber(entry, key, minimum, maximum, default, PERCENTAGE)
            for key, (minimum, maximum, default) in _TARGETS.items()
        ]
    entities.append(DefaultedNumber(entry, CONF_STALE_MINUTES, *_STALE_LIMITS, UnitOfTime.MINUTES))
    entities += [
        DefaultedNumber(entry, key, minimum, maximum, default, PERCENTAGE)
        for key, (minimum, maximum, default) in _THRESHOLDS.items()
    ]
    remove_unused_entities(hass, entry, "number", _ALL_KEYS - {entity.key for entity in entities})
    async_add_entities(entities)


class _OptionNumber(NumberEntity):
    """A number stored in the entry's options."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_step = 1
    _attr_should_poll = False

    def __init__(
        self, entry: ConfigEntry, key: str, minimum: float, maximum: float, unit: str | None
    ) -> None:
        self._entry = entry
        self.key = key
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = probe_device_info(entry)
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_unit_of_measurement = unit

    async def async_added_to_hass(self) -> None:
        # Captures and resets change the points from a button.
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, calibration_signal(self._entry.entry_id), self.async_write_ha_state
            )
        )

    def _store(self, value: float) -> None:
        options = {**self._entry.options, self.key: int(value)}
        self._check(options)
        self.hass.config_entries.async_update_entry(self._entry, options=options)
        async_dispatcher_send(self.hass, calibration_signal(self._entry.entry_id))

    def _check(self, options: dict[str, int]) -> None:
        """Raise if the new options are invalid."""

    async def async_set_native_value(self, value: float) -> None:
        self._store(value)


class PointNumber(_OptionNumber):
    """The source's reading at 0 % or at 100 % moisture."""

    @property
    def native_value(self) -> float:
        return float(self._entry.options[self.key])

    def _check(self, options: dict[str, int]) -> None:
        check_points(options)


class DefaultedNumber(_OptionNumber):
    """A setting that has a default until it is first changed."""

    def __init__(
        self,
        entry: ConfigEntry,
        key: str,
        minimum: float,
        maximum: float,
        default: int,
        unit: str,
    ) -> None:
        super().__init__(entry, key, minimum, maximum, unit)
        self._default = default

    @property
    def native_value(self) -> float:
        return float(self._entry.options.get(self.key, self._default))
