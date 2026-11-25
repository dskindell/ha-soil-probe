"""The probe's Label."""

from __future__ import annotations

from typing import Any

from homeassistant.components.text import ATTR_VALUE, DOMAIN as TEXT_DOMAIN, SERVICE_SET_VALUE
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant.common import MockConfigEntry

from custom_components.soil_probe.const import DOMAIN

LABEL = "text.backyard_central_label"


async def _setup(hass: HomeAssistant, **options: Any) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Backyard Central",
        options={"model": "wh51", "raw_ad_entity": "sensor.wh51_ad", "ad0": 70, "ad100": 500}
        | options,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _label(hass: HomeAssistant) -> str:
    state = hass.states.get(LABEL)
    assert state is not None
    return state.state


async def _set(hass: HomeAssistant, value: str) -> None:
    await hass.services.async_call(
        TEXT_DOMAIN, SERVICE_SET_VALUE, {ATTR_ENTITY_ID: LABEL, ATTR_VALUE: value}, blocking=True
    )


def _rename_device(hass: HomeAssistant, entry: MockConfigEntry, name: str) -> None:
    registry = dr.async_get(hass)
    device = registry.async_get_device_by_identifier((DOMAIN, entry.entry_id), entry.entry_id)
    assert device is not None
    registry.async_update_device(device.id, name_by_user=name)


async def test_label_is_a_config_entity(hass: HomeAssistant) -> None:
    await _setup(hass, label="Tomato bed")

    assert _label(hass) == "Tomato bed"
    registry_entry = er.async_get(hass).async_get(LABEL)
    assert registry_entry is not None
    assert registry_entry.entity_category is er.EntityCategory.CONFIG
    state = hass.states.get(LABEL)
    assert state is not None
    assert state.attributes["max"] == 255


async def test_without_a_label_it_follows_the_device_name(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    assert _label(hass) == "Backyard Central"

    _rename_device(hass, entry, "Raised bed probe")
    await hass.async_block_till_done()

    assert _label(hass) == "Raised bed probe"


async def test_a_set_label_stays_until_cleared(hass: HomeAssistant) -> None:
    entry = await _setup(hass)

    await _set(hass, "  Tomato bed ")
    assert entry.options["label"] == "Tomato bed"
    assert _label(hass) == "Tomato bed"

    _rename_device(hass, entry, "Raised bed probe")
    await hass.async_block_till_done()
    assert _label(hass) == "Tomato bed"

    await _set(hass, "")
    assert "label" not in entry.options
    assert _label(hass) == "Raised bed probe"
