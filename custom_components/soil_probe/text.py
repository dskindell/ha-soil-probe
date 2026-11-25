"""The probe's label: a name the user sets without renaming the device."""

from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MAX_LENGTH_STATE_STATE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_LABEL
from .device import probe_device_info


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the probe's label."""
    async_add_entities([LabelText(entry)])


class LabelText(TextEntity):
    """The label the user set; without one, the device's current name."""

    _attr_has_entity_name = True
    _attr_translation_key = "label"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_max = MAX_LENGTH_STATE_STATE
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_label"
        self._attr_device_info = probe_device_info(entry)

    @property
    def native_value(self) -> str:
        # Entity already rewrites the state when the device is renamed.
        device = self.device_entry
        return str(
            self._entry.options.get(CONF_LABEL)
            or (device and (device.name_by_user or device.name))
            or self._entry.title
        )

    async def async_set_value(self, value: str) -> None:
        options = {key: val for key, val in self._entry.options.items() if key != CONF_LABEL}
        if label := value.strip():
            options[CONF_LABEL] = label
        self.hass.config_entries.async_update_entry(self._entry, options=options)
        self.async_write_ha_state()
