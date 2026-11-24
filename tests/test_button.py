"""Capture and reset buttons."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.components.number import ATTR_VALUE, DOMAIN as NUMBER_DOMAIN, SERVICE_SET_VALUE
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.soil_probe.calibration import calibrated_moisture, solve_at0, solve_at100
from custom_components.soil_probe.const import DOMAIN

RAW = "sensor.wh51_ad"
OUTPUT = "sensor.backyard_central_moisture"
DRY = "button.backyard_central_capture_dry"
WET = "button.backyard_central_capture_wet"
RESET = "button.backyard_central_reset_calibration"
DRY_TARGET = "number.backyard_central_dry_capture_target"
WET_TARGET = "number.backyard_central_wet_capture_target"
AD0 = "number.backyard_central_raw_ad_at_0"


async def _setup(hass: HomeAssistant, **options: Any) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="Backyard Central", options=options)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _wh51(hass: HomeAssistant) -> MockConfigEntry:
    return await _setup(hass, model="wh51", raw_ad_entity=RAW, ad0=70, ad100=500)


async def _press(hass: HomeAssistant, entity_id: str) -> None:
    await hass.services.async_call(
        BUTTON_DOMAIN, SERVICE_PRESS, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )


def _value(hass: HomeAssistant, entity_id: str) -> float:
    state = hass.states.get(entity_id)
    assert state is not None, entity_id
    return float(state.state)


@pytest.mark.parametrize(("reading", "target"), [(120, 10), (300, 0), (90, 50)])
def test_solved_zero_point_gives_the_target(reading: float, target: float) -> None:
    ad0 = solve_at0(reading, 500, target)
    assert calibrated_moisture(reading, ad0, 500) == pytest.approx(target)


@pytest.mark.parametrize(("reading", "target"), [(400, 95), (450, 100), (300, 10)])
def test_solved_full_point_gives_the_target(reading: float, target: float) -> None:
    ad100 = solve_at100(reading, 70, target)
    assert calibrated_moisture(reading, 70, ad100) == pytest.approx(target)


async def test_capture_dry_solves_ad0_for_the_dry_target(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    hass.states.async_set(RAW, "120")
    entry = await _wh51(hass)
    assert _value(hass, DRY_TARGET) == 10

    with caplog.at_level(logging.INFO, logger="custom_components.soil_probe"):
        await _press(hass, DRY)

    assert entry.options["ad0"] == 78
    assert entry.options["ad100"] == 500
    assert _value(hass, AD0) == 78
    assert _value(hass, OUTPUT) == pytest.approx(10, abs=0.5)
    assert "Backyard Central: ad0 70 -> 78 (raw AD 120, target 10 %)" in caplog.text


async def test_capture_wet_uses_a_changed_target(hass: HomeAssistant) -> None:
    hass.states.async_set(RAW, "400")
    entry = await _wh51(hass)
    assert _value(hass, WET_TARGET) == 95

    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: WET_TARGET, ATTR_VALUE: 100},
        blocking=True,
    )
    await _press(hass, WET)

    assert entry.options["wet_target"] == 100
    assert entry.options["ad100"] == 400
    assert _value(hass, OUTPUT) == 100


async def test_reset_restores_the_model_defaults(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    hass.states.async_set(RAW, "400")
    entry = await _wh51(hass)
    await _press(hass, WET)
    assert entry.options["ad100"] == 417

    with caplog.at_level(logging.INFO, logger="custom_components.soil_probe"):
        await _press(hass, RESET)

    assert (entry.options["ad0"], entry.options["ad100"]) == (70, 500)
    assert "calibration reset: ad0 70 -> 70, ad100 417 -> 500" in caplog.text


@pytest.mark.parametrize(
    ("reading", "button", "error"),
    [
        ("300", DRY, "point_out_of_range"),
        ("75", WET, "span_too_small"),
        (STATE_UNAVAILABLE, DRY, "no_reading"),
    ],
)
async def test_unusable_captures_are_refused(
    hass: HomeAssistant, reading: str, button: str, error: str
) -> None:
    hass.states.async_set(RAW, reading)
    entry = await _wh51(hass)

    with pytest.raises(ServiceValidationError) as err:
        await _press(hass, button)

    assert err.value.translation_key == error
    assert (entry.options["ad0"], entry.options["ad100"]) == (70, 500)


async def test_generic_probe_has_captures_but_no_reset(hass: HomeAssistant) -> None:
    await _setup(hass, model="generic", raw_ad_entity=RAW, ad0=100, ad100=2000)

    assert hass.states.get(DRY) is not None
    assert hass.states.get(WET) is not None
    assert hass.states.get(RESET) is None


async def test_moisture_source_has_no_buttons_or_targets(hass: HomeAssistant) -> None:
    await _setup(hass, model="wh51", moisture_entity="sensor.m", pct0=0, pct100=100)

    for entity_id in (DRY, WET, RESET, DRY_TARGET, WET_TARGET):
        assert hass.states.get(entity_id) is None
