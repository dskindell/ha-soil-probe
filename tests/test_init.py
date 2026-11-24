"""Setting up and unloading a probe, and following its source entities."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.soil_probe.const import DOMAIN


def _entry(hass: HomeAssistant, entity_registry: er.EntityRegistry) -> MockConfigEntry:
    raw = entity_registry.async_get_or_create("sensor", "mqtt", "wh51_ad", suggested_object_id="ad")
    battery = entity_registry.async_get_or_create(
        "sensor", "mqtt", "wh51_battery", suggested_object_id="battery"
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Backyard Central",
        options={
            "model": "wh51",
            "raw_ad_entity": raw.entity_id,
            "battery_entity": battery.entity_id,
            "ad0": 70,
            "ad100": 500,
        },
    )
    entry.add_to_hass(hass)
    return entry


async def test_entry_loads_and_unloads(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    entry = _entry(hass, entity_registry)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_renamed_source_is_followed(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    entry = _entry(hass, entity_registry)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_registry.async_update_entity("sensor.ad", new_entity_id="sensor.backyard_ad")
    await hass.async_block_till_done()

    assert entry.options["raw_ad_entity"] == "sensor.backyard_ad"
    assert entry.options["battery_entity"] == "sensor.battery"
    assert entry.state is ConfigEntryState.LOADED


async def test_removed_source_is_logged(
    hass: HomeAssistant, entity_registry: er.EntityRegistry, caplog: pytest.LogCaptureFixture
) -> None:
    entry = _entry(hass, entity_registry)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with caplog.at_level(logging.WARNING):
        entity_registry.async_remove("sensor.battery")
        await hass.async_block_till_done()

    assert "Backyard Central: source entity sensor.battery was removed" in caplog.text
    assert entry.options["battery_entity"] == "sensor.battery"


async def test_entry_without_optional_sources_loads(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Planter",
        options={"model": "generic", "moisture_entity": "sensor.m", "pct0": 0, "pct100": 100},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
