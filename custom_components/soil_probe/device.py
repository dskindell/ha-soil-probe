"""The probe's device."""

from __future__ import annotations

from collections.abc import Iterable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo

from .const import CONF_MODEL, DOMAIN
from .models import MODELS


def probe_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Device info shared by all of a probe's entities."""
    model = MODELS[entry.options[CONF_MODEL]]
    # Keyed on the entry, not a source, so swapping a source keeps the same device.
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer=model.manufacturer,
        model=model.model,
    )


def remove_unused_entities(
    hass: HomeAssistant, entry: ConfigEntry, platform: str, unused_keys: Iterable[str]
) -> None:
    """Drop entities a source swap left without a source."""
    registry = er.async_get(hass)
    for key in unused_keys:
        if entity_id := registry.async_get_entity_id(platform, DOMAIN, f"{entry.entry_id}_{key}"):
            registry.async_remove(entity_id)
