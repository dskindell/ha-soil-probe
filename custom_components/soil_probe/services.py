"""The set_sources action: change a probe's sensors, for example after replacing the probe."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_get_device_and_config_entry
import probatio

from .calibration import check_points
from .const import (
    CONF_AD0,
    CONF_AD100,
    CONF_BATTERY_SOURCE,
    CONF_MOISTURE_SOURCE,
    CONF_RAW_SOURCE,
    DOMAIN,
)
from .sources import (
    has_one_source,
    needs_calibration,
    with_defaults,
    with_sources,
    without_calibration,
)

SERVICE_SET_SOURCES = "set_sources"
ATTR_RESET_CALIBRATION = "reset_calibration"

_AD = probatio.All(probatio.Coerce(int), probatio.Range(min=0))

SET_SOURCES_SCHEMA = probatio.Schema(
    {
        probatio.Required(ATTR_DEVICE_ID): probatio.All(
            probatio.EnsureList(), probatio.Length(min=1), [cv.string]
        ),
        probatio.Optional(CONF_RAW_SOURCE): cv.entity_id,
        probatio.Optional(CONF_MOISTURE_SOURCE): cv.entity_id,
        probatio.Optional(CONF_BATTERY_SOURCE): cv.entity_id,
        probatio.Optional(ATTR_RESET_CALIBRATION, default=False): cv.boolean,
        probatio.Optional(CONF_AD0): _AD,
        probatio.Optional(CONF_AD100): _AD,
    }
)


def async_setup_services(hass: HomeAssistant) -> None:
    """Register the integration's actions."""

    async def set_sources(call: ServiceCall) -> None:
        entries = [
            async_get_device_and_config_entry(hass, DOMAIN, device_id, include_child_devices=False)[
                1
            ]
            for device_id in call.data[ATTR_DEVICE_ID]
        ]
        # Check every probe before changing any, so a refused call changes nothing.
        changes = [(entry, _new_options(entry, call.data)) for entry in entries]
        for entry, options in changes:
            hass.config_entries.async_update_entry(entry, options=options)
            await hass.config_entries.async_reload(entry.entry_id)

    hass.services.async_register(DOMAIN, SERVICE_SET_SOURCES, set_sources, SET_SOURCES_SCHEMA)


def _error(key: str, **placeholders: str) -> ServiceValidationError:
    return ServiceValidationError(
        translation_domain=DOMAIN, translation_key=key, translation_placeholders=placeholders
    )


def _new_options(entry: ConfigEntry, data: Mapping[str, Any]) -> dict[str, Any]:
    if not has_one_source(data):
        raise _error("one_source")
    given_ad = {key: data[key] for key in (CONF_AD0, CONF_AD100) if key in data}
    if given_ad and CONF_RAW_SOURCE not in data:
        raise _error("ad_needs_raw")
    options = with_sources(entry.options, data)
    if data[ATTR_RESET_CALIBRATION]:
        options = without_calibration(options)
    options = with_defaults(options | given_ad)
    if needs_calibration(options):
        raise _error("calibration_needed", probe=entry.title)
    check_points(options)
    return options
