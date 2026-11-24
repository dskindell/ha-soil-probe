"""The calibrated moisture sensor and the probe's device."""

from __future__ import annotations

from typing import Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.soil_probe.calibration import calibrated_moisture
from custom_components.soil_probe.const import DOMAIN

RAW = "sensor.wh51_ad"
MOISTURE = "sensor.wh51_moisture"
OUTPUT = "sensor.backyard_central_moisture"


async def _setup(hass: HomeAssistant, **options: Any) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="Backyard Central", options=options)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.mark.parametrize(
    ("ad", "expected"),
    [(70, 0.0), (500, 100.0), (285, 50.0), (0, 0.0), (511, 100.0)],
)
def test_calibrated_moisture_is_linear_and_clamped(ad: float, expected: float) -> None:
    assert calibrated_moisture(ad, 70, 500) == expected


async def test_raw_source_is_calibrated(hass: HomeAssistant) -> None:
    hass.states.async_set(RAW, "285")
    await _setup(hass, model="wh51", raw_ad_entity=RAW, ad0=70, ad100=500)

    state = hass.states.get(OUTPUT)
    assert state is not None
    assert float(state.state) == 50.0
    assert state.attributes["device_class"] == "moisture"
    assert state.attributes["unit_of_measurement"] == "%"
    assert state.attributes["state_class"] == "measurement"

    hass.states.async_set(RAW, "199")
    await hass.async_block_till_done()
    assert float(hass.states.get(OUTPUT).state) == 30.0  # type: ignore[union-attr]


async def test_calibration_change_applies_on_the_next_reading(hass: HomeAssistant) -> None:
    hass.states.async_set(RAW, "285")
    entry = await _setup(hass, model="wh51", raw_ad_entity=RAW, ad0=70, ad100=500)

    hass.config_entries.async_update_entry(entry, options={**entry.options, "ad100": 400})
    hass.states.async_set(RAW, "235")
    await hass.async_block_till_done()

    assert float(hass.states.get(OUTPUT).state) == 50.0  # type: ignore[union-attr]


async def test_moisture_source_is_corrected(hass: HomeAssistant) -> None:
    hass.states.async_set(MOISTURE, "50")
    await _setup(hass, model="wh51", moisture_entity=MOISTURE, pct0=20, pct100=80)

    assert float(hass.states.get(OUTPUT).state) == 50.0  # type: ignore[union-attr]

    hass.states.async_set(MOISTURE, "35")
    await hass.async_block_till_done()
    assert float(hass.states.get(OUTPUT).state) == 25.0  # type: ignore[union-attr]


async def test_moisture_source_passes_through(hass: HomeAssistant) -> None:
    hass.states.async_set(MOISTURE, "42")
    await _setup(hass, model="generic", moisture_entity=MOISTURE, pct0=0, pct100=100)

    assert float(hass.states.get(OUTPUT).state) == 42.0  # type: ignore[union-attr]


@pytest.mark.parametrize("source_state", [STATE_UNAVAILABLE, STATE_UNKNOWN, "not a number"])
async def test_unusable_source_makes_the_sensor_unavailable(
    hass: HomeAssistant, source_state: str
) -> None:
    hass.states.async_set(RAW, "285")
    await _setup(hass, model="wh51", raw_ad_entity=RAW, ad0=70, ad100=500)

    hass.states.async_set(RAW, source_state)
    await hass.async_block_till_done()
    assert hass.states.get(OUTPUT).state == STATE_UNAVAILABLE  # type: ignore[union-attr]

    hass.states.async_set(RAW, "285")
    await hass.async_block_till_done()
    assert float(hass.states.get(OUTPUT).state) == 50.0  # type: ignore[union-attr]


async def test_missing_source_makes_the_sensor_unavailable(hass: HomeAssistant) -> None:
    await _setup(hass, model="wh51", raw_ad_entity=RAW, ad0=70, ad100=500)

    assert hass.states.get(OUTPUT).state == STATE_UNAVAILABLE  # type: ignore[union-attr]


async def test_probe_gets_its_own_device(
    hass: HomeAssistant, device_registry: dr.DeviceRegistry, entity_registry: er.EntityRegistry
) -> None:
    hass.states.async_set(RAW, "285")
    entry = await _setup(hass, model="wh51l", raw_ad_entity=RAW, ad0=70, ad100=500)

    device = device_registry.async_get_device_by_identifier(
        (DOMAIN, entry.entry_id), entry.entry_id
    )
    assert device is not None
    assert (device.name, device.manufacturer, device.model) == (
        "Backyard Central",
        "Ecowitt",
        "WH51L",
    )
    entity = entity_registry.async_get(OUTPUT)
    assert entity is not None
    assert entity.device_id == device.id
    assert entity.unique_id == f"{entry.entry_id}_moisture"


async def test_generic_probe_device_has_no_manufacturer(
    hass: HomeAssistant, device_registry: dr.DeviceRegistry
) -> None:
    entry = await _setup(hass, model="generic", moisture_entity=MOISTURE, pct0=0, pct100=100)

    device = device_registry.async_get_device_by_identifier(
        (DOMAIN, entry.entry_id), entry.entry_id
    )
    assert device is not None
    assert (device.manufacturer, device.model) == (None, None)
