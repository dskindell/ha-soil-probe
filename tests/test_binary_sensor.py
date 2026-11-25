"""The Needs water sensor."""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import ATTR_VALUE, DOMAIN as NUMBER_DOMAIN, SERVICE_SET_VALUE
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.soil_probe.const import DOMAIN

MOISTURE = "sensor.wh51_moisture"
RAW = "sensor.wh51_ad"
NEEDS_WATER = "binary_sensor.backyard_central_needs_water"
THRESHOLD = "number.backyard_central_low_moisture_threshold"
MARGIN = "number.backyard_central_low_moisture_margin"


async def _setup(hass: HomeAssistant, **options: Any) -> MockConfigEntry:
    # A moisture % source with an unchanged correction, so moisture equals the source's value.
    defaults = {"model": "generic", "moisture_entity": MOISTURE, "pct0": 0, "pct100": 100}
    options = {key: value for key, value in (defaults | options).items() if value is not None}
    entry = MockConfigEntry(domain=DOMAIN, title="Backyard Central", options=options)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _state(hass: HomeAssistant, entity_id: str = NEEDS_WATER) -> str:
    state = hass.states.get(entity_id)
    assert state is not None, entity_id
    return state.state


async def _reading(hass: HomeAssistant, value: str, entity_id: str = MOISTURE) -> None:
    hass.states.async_set(entity_id, value)
    await hass.async_block_till_done()


async def _set(hass: HomeAssistant, entity_id: str, value: float) -> None:
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: value},
        blocking=True,
    )


async def test_off_threshold_keeps_the_sensor_off(hass: HomeAssistant) -> None:
    hass.states.async_set(MOISTURE, "5")
    await _setup(hass)

    assert float(_state(hass, THRESHOLD)) == 0
    assert float(_state(hass, MARGIN)) == 2
    assert _state(hass) == STATE_OFF
    state = hass.states.get(NEEDS_WATER)
    assert state is not None
    assert state.attributes["device_class"] == "problem"


async def test_on_below_the_threshold_and_off_only_past_the_margin(hass: HomeAssistant) -> None:
    hass.states.async_set(MOISTURE, "50")
    await _setup(hass, low_threshold=30)
    assert _state(hass) == STATE_OFF

    await _reading(hass, "29")
    assert _state(hass) == STATE_ON
    await _reading(hass, "30")  # at the threshold, inside the margin: holds
    assert _state(hass) == STATE_ON
    await _reading(hass, "31.9")
    assert _state(hass) == STATE_ON
    await _reading(hass, "32")
    assert _state(hass) == STATE_OFF
    await _reading(hass, "30")  # back inside the margin from above: holds
    assert _state(hass) == STATE_OFF


@pytest.mark.parametrize(("moisture", "expected"), [("20", STATE_ON), ("31", STATE_OFF)])
async def test_startup_is_on_only_below_the_threshold(
    hass: HomeAssistant, moisture: str, expected: str
) -> None:
    hass.states.async_set(MOISTURE, moisture)
    await _setup(hass, low_threshold=30)

    assert _state(hass) == expected


async def test_changing_threshold_or_margin_applies_at_once(hass: HomeAssistant) -> None:
    hass.states.async_set(MOISTURE, "25")
    entry = await _setup(hass)

    await _set(hass, THRESHOLD, 30)
    assert entry.options["low_threshold"] == 30
    assert _state(hass) == STATE_ON

    await _set(hass, MARGIN, 0)
    await _reading(hass, "30")
    assert _state(hass) == STATE_OFF

    await _set(hass, THRESHOLD, 30)
    await _reading(hass, "20")
    assert _state(hass) == STATE_ON
    await _set(hass, THRESHOLD, 0)
    assert _state(hass) == STATE_OFF


@pytest.mark.parametrize("threshold", [30, 0])
async def test_unavailable_moisture_makes_it_unavailable(
    hass: HomeAssistant, threshold: int
) -> None:
    hass.states.async_set(MOISTURE, "20")
    await _setup(hass, low_threshold=threshold)
    assert _state(hass) == (STATE_ON if threshold else STATE_OFF)

    await _reading(hass, STATE_UNAVAILABLE)
    assert _state(hass) == STATE_UNAVAILABLE

    await _reading(hass, "31")
    assert _state(hass) == STATE_OFF


async def test_follows_the_calibrated_moisture_of_a_raw_source(hass: HomeAssistant) -> None:
    hass.states.async_set(RAW, "199")  # 30 % with 70/500
    await _setup(
        hass,
        model="wh51",
        moisture_entity=None,
        raw_ad_entity=RAW,
        ad0=70,
        ad100=500,
        low_threshold=25,
    )
    assert _state(hass) == STATE_OFF

    # A recalibration that lowers this reading to 20 % turns it on without a new reading.
    await _set(hass, "number.backyard_central_raw_ad_at_100", 715)
    assert _state(hass) == STATE_ON
