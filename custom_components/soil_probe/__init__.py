"""Soil Probe: one device per soil probe, with a calibrated moisture sensor."""

from __future__ import annotations

from functools import partial
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.helper_integration import async_handle_source_entity_changes
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, SOURCE_KEYS
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SENSOR,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the actions, which work on any probe."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Set up a probe."""
    for key in SOURCE_KEYS:
        if (entity_id := entry.options.get(key)) is None:
            continue
        entry.async_on_unload(
            async_handle_source_entity_changes(
                hass,
                helper_config_entry_id=entry.entry_id,
                set_source_entity_id_or_uuid=partial(_source_renamed, hass, entry, key),
                # The probe has its own device, so the source's device must never be relinked.
                source_device_id=None,
                source_entity_id_or_uuid=entity_id,
                source_entity_removed=partial(_source_removed, entry, entity_id),
            )
        )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Unload a probe."""
    await hass.config_entries.async_unload_platforms_or_raise(entry, PLATFORMS)


def _source_renamed(hass: HomeAssistant, entry: ConfigEntry, key: str, entity_id: str) -> None:
    hass.config_entries.async_update_entry(entry, options={**entry.options, key: entity_id})
    hass.config_entries.async_schedule_reload(entry.entry_id)


async def _source_removed(entry: ConfigEntry, entity_id: str) -> None:
    _LOGGER.warning(
        "%s: source entity %s was removed; choose a new one under Configure",
        entry.title,
        entity_id,
    )
