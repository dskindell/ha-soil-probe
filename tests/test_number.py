"""The calibration numbers on the probe's device."""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import ATTR_VALUE, DOMAIN as NUMBER_DOMAIN, SERVICE_SET_VALUE
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.soil_probe.const import DOMAIN

RAW = "sensor.wh51_ad"
MOISTURE = "sensor.wh51_moisture"
OUTPUT = "sensor.backyard_central_moisture"
AD0 = "number.backyard_central_raw_ad_at_0"
AD100 = "number.backyard_central_raw_ad_at_100"
PCT0 = "number.backyard_central_source_at_0"
PCT100 = "number.backyard_central_source_at_100"


async def _setup(hass: HomeAssistant, **options: Any) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="Backyard Central", options=options)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _set(hass: HomeAssistant, entity_id: str, value: float) -> None:
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: value},
        blocking=True,
    )


def _value(hass: HomeAssistant, entity_id: str) -> float:
    state = hass.states.get(entity_id)
    assert state is not None, entity_id
    return float(state.state)


async def test_raw_source_gets_ad_numbers_with_model_limits(hass: HomeAssistant) -> None:
    await _setup(hass, model="wh51", raw_ad_entity=RAW, ad0=70, ad100=500)

    assert _value(hass, AD0) == 70
    assert _value(hass, AD100) == 500
    ad0 = hass.states.get(AD0)
    ad100 = hass.states.get(AD100)
    assert ad0 is not None
    assert ad100 is not None
    assert (ad0.attributes["min"], ad0.attributes["max"]) == (0, 200)
    assert (ad100.attributes["min"], ad100.attributes["max"]) == (10, 1000)
    assert hass.states.get(PCT0) is None


async def test_moisture_source_gets_percent_numbers(hass: HomeAssistant) -> None:
    await _setup(hass, model="generic", moisture_entity=MOISTURE, pct0=0, pct100=100)

    assert _value(hass, PCT0) == 0
    assert _value(hass, PCT100) == 100
    pct100 = hass.states.get(PCT100)
    assert pct100 is not None
    assert pct100.attributes["unit_of_measurement"] == "%"
    assert hass.states.get(AD0) is None


async def test_setting_a_number_stores_it_and_recalculates_at_once(hass: HomeAssistant) -> None:
    hass.states.async_set(RAW, "235")
    entry = await _setup(hass, model="wh51", raw_ad_entity=RAW, ad0=70, ad100=500)
    assert _value(hass, OUTPUT) == pytest.approx(38.37, abs=0.01)

    await _set(hass, AD100, 400)

    assert entry.options["ad100"] == 400
    assert _value(hass, AD100) == 400
    assert _value(hass, OUTPUT) == 50.0


async def test_setting_the_moisture_correction(hass: HomeAssistant) -> None:
    hass.states.async_set(MOISTURE, "50")
    entry = await _setup(hass, model="generic", moisture_entity=MOISTURE, pct0=0, pct100=100)

    await _set(hass, PCT0, 20)
    await _set(hass, PCT100, 80)

    assert (entry.options["pct0"], entry.options["pct100"]) == (20, 80)
    assert _value(hass, OUTPUT) == 50.0
    hass.states.async_set(MOISTURE, "35")
    await hass.async_block_till_done()
    assert _value(hass, OUTPUT) == 25.0


@pytest.mark.parametrize(("entity_id", "value"), [(AD0, 495), (AD100, 75)])
async def test_points_closer_than_the_minimum_span_are_rejected(
    hass: HomeAssistant, entity_id: str, value: float
) -> None:
    entry = await _setup(hass, model="generic", raw_ad_entity=RAW, ad0=70, ad100=500)

    with pytest.raises(ServiceValidationError) as err:
        await _set(hass, entity_id, value)

    assert err.value.translation_key == "span_too_small"
    assert (entry.options["ad0"], entry.options["ad100"]) == (70, 500)


async def test_swapping_the_source_type_removes_the_old_numbers(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    entry = await _setup(hass, model="wh51", raw_ad_entity=RAW, ad0=70, ad100=500)
    assert entity_registry.async_get(AD0) is not None

    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"], {"moisture_entity": MOISTURE}
    )
    await hass.async_block_till_done()

    assert entity_registry.async_get(AD0) is None
    assert entity_registry.async_get(AD100) is None
    assert entity_registry.async_get(PCT0) is not None
    assert entry.options["pct0"] == 0
