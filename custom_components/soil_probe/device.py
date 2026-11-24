"""The probe's device."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
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
