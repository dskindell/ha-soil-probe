"""Capture and reset buttons for a probe with a raw AD source."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .calibration import check_points, reading_of, solve_at0, solve_at100
from .const import (
    CONF_AD0,
    CONF_AD100,
    CONF_DRY_TARGET,
    CONF_MODEL,
    CONF_RAW_SOURCE,
    CONF_WET_TARGET,
    DEFAULT_DRY_TARGET,
    DEFAULT_WET_TARGET,
    DOMAIN,
    calibration_signal,
)
from .device import probe_device_info
from .models import MODELS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add capture dry, capture wet and, when the model has defaults, reset."""
    if CONF_RAW_SOURCE not in entry.options:
        return
    entities: list[_CalibrationButton] = [
        CaptureButton(entry, "capture_dry", CONF_AD0, CONF_DRY_TARGET, DEFAULT_DRY_TARGET),
        CaptureButton(entry, "capture_wet", CONF_AD100, CONF_WET_TARGET, DEFAULT_WET_TARGET),
    ]
    model = MODELS[entry.options[CONF_MODEL]]
    if model.ad0 is not None and model.ad100 is not None:
        entities.append(ResetButton(entry, "reset_calibration", model.ad0, model.ad100))
    async_add_entities(entities)


class _CalibrationButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: ConfigEntry, key: str) -> None:
        self._entry = entry
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = probe_device_info(entry)

    def _store(self, changes: dict[str, int], describe: Callable[[Mapping[str, Any]], str]) -> None:
        old = self._entry.options
        options = {**old, **changes}
        check_points(options)
        self.hass.config_entries.async_update_entry(self._entry, options=options)
        async_dispatcher_send(self.hass, calibration_signal(self._entry.entry_id))
        _LOGGER.info("%s: %s", self._entry.title, describe(old))


class CaptureButton(_CalibrationButton):
    """Solve one calibration point so the current reading equals the target."""

    def __init__(
        self, entry: ConfigEntry, key: str, point: str, target_key: str, default: int
    ) -> None:
        super().__init__(entry, key)
        self._point = point
        self._target_key = target_key
        self._default = default

    async def async_press(self) -> None:
        options = self._entry.options
        source = options[CONF_RAW_SOURCE]
        if (reading := reading_of(self.hass.states.get(source))) is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="no_reading",
                translation_placeholders={"entity_id": source},
            )
        target = options.get(self._target_key, self._default)
        if self._point == CONF_AD0:
            solved = solve_at0(reading, options[CONF_AD100], target)
        else:
            solved = solve_at100(reading, options[CONF_AD0], target)
        value = round(solved)
        self._store(
            {self._point: value},
            lambda old: (
                f"{self._point} {old[self._point]} -> {value} "
                f"(raw AD {reading:g}, target {target} %)"
            ),
        )


class ResetButton(_CalibrationButton):
    """Put both calibration points back to the model's defaults."""

    def __init__(self, entry: ConfigEntry, key: str, ad0: int, ad100: int) -> None:
        super().__init__(entry, key)
        self._ad0 = ad0
        self._ad100 = ad100

    async def async_press(self) -> None:
        ad0, ad100 = self._ad0, self._ad100
        self._store(
            {CONF_AD0: ad0, CONF_AD100: ad100},
            lambda old: (
                f"calibration reset: {CONF_AD0} {old[CONF_AD0]} -> {ad0}, "
                f"{CONF_AD100} {old[CONF_AD100]} -> {ad100}"
            ),
        )
