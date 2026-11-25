"""The set_sources action."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.soil_probe.const import DOMAIN

OLD_RAW = "sensor.old_ad"
OLD_BATTERY = "sensor.old_battery"
NEW_RAW = "sensor.new_ad"
NEW_BATTERY = "sensor.new_battery"
MOISTURE = "sensor.new_moisture"


async def _setup(
    hass: HomeAssistant, title: str = "Backyard Central", **options: Any
) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title=title, options=options)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _device_id(hass: HomeAssistant, entry: MockConfigEntry) -> str:
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, entry.entry_id), entry.entry_id
    )
    assert device is not None
    return device.id


async def _call(hass: HomeAssistant, device_ids: list[str], **data: Any) -> None:
    await hass.services.async_call(
        DOMAIN, "set_sources", {"device_id": device_ids, **data}, blocking=True
    )
    await hass.async_block_till_done()


async def _wh51(hass: HomeAssistant, **options: Any) -> MockConfigEntry:
    return await _setup(
        hass,
        **{
            "model": "wh51",
            "raw_ad_entity": OLD_RAW,
            "battery_entity": OLD_BATTERY,
            "ad0": 80,
            "ad100": 420,
        }
        | options,
    )


async def test_replacing_a_probe_sets_both_sensors_and_keeps_calibration(
    hass: HomeAssistant,
) -> None:
    hass.states.async_set(NEW_RAW, "250")
    entry = await _wh51(hass)

    await _call(hass, [_device_id(hass, entry)], raw_ad_entity=NEW_RAW, battery_entity=NEW_BATTERY)

    assert entry.options == {
        "model": "wh51",
        "raw_ad_entity": NEW_RAW,
        "battery_entity": NEW_BATTERY,
        "ad0": 80,
        "ad100": 420,
    }
    assert entry.state is ConfigEntryState.LOADED
    # Reloaded, so the moisture sensor follows the new source.
    state = hass.states.get("sensor.backyard_central_moisture")
    assert state is not None
    assert float(state.state) == pytest.approx(50.0)


async def test_a_left_out_battery_is_removed(hass: HomeAssistant) -> None:
    entry = await _wh51(hass)

    await _call(hass, [_device_id(hass, entry)], raw_ad_entity=NEW_RAW)

    assert "battery_entity" not in entry.options


async def test_reset_calibration_returns_to_the_model_defaults(hass: HomeAssistant) -> None:
    entry = await _wh51(hass)

    await _call(hass, [_device_id(hass, entry)], raw_ad_entity=NEW_RAW, reset_calibration=True)

    assert (entry.options["ad0"], entry.options["ad100"]) == (70, 500)


async def test_given_points_set_the_calibration(hass: HomeAssistant) -> None:
    entry = await _wh51(hass)

    await _call(hass, [_device_id(hass, entry)], raw_ad_entity=NEW_RAW, ad100=450)

    assert (entry.options["ad0"], entry.options["ad100"]) == (80, 450)


async def test_reset_with_one_given_point_takes_the_other_from_the_model(
    hass: HomeAssistant,
) -> None:
    entry = await _wh51(hass)

    await _call(
        hass, [_device_id(hass, entry)], raw_ad_entity=NEW_RAW, reset_calibration=True, ad0=90
    )

    assert (entry.options["ad0"], entry.options["ad100"]) == (90, 500)


async def test_switching_to_moisture_uses_the_unchanged_correction(hass: HomeAssistant) -> None:
    entry = await _wh51(hass)

    await _call(hass, [_device_id(hass, entry)], moisture_entity=MOISTURE)

    assert entry.options["moisture_entity"] == MOISTURE
    assert "raw_ad_entity" not in entry.options
    assert (entry.options["pct0"], entry.options["pct100"]) == (0, 100)


async def test_reset_on_a_moisture_probe_resets_the_correction(hass: HomeAssistant) -> None:
    entry = await _setup(hass, model="generic", moisture_entity=MOISTURE, pct0=20, pct100=80)

    await _call(hass, [_device_id(hass, entry)], moisture_entity=MOISTURE, reset_calibration=True)

    assert (entry.options["pct0"], entry.options["pct100"]) == (0, 100)


async def test_generic_needs_points_when_it_has_none(hass: HomeAssistant) -> None:
    entry = await _setup(hass, model="generic", moisture_entity=MOISTURE, pct0=0, pct100=100)
    device_id = _device_id(hass, entry)

    with pytest.raises(ServiceValidationError) as err:
        await _call(hass, [device_id], raw_ad_entity=NEW_RAW)
    assert err.value.translation_key == "calibration_needed"
    assert err.value.translation_placeholders == {"probe": "Backyard Central"}

    await _call(hass, [device_id], raw_ad_entity=NEW_RAW, ad0=100, ad100=2000)
    assert (entry.options["ad0"], entry.options["ad100"]) == (100, 2000)


async def test_generic_reset_needs_points(hass: HomeAssistant) -> None:
    entry = await _setup(hass, model="generic", raw_ad_entity=OLD_RAW, ad0=100, ad100=2000)

    with pytest.raises(ServiceValidationError) as err:
        await _call(hass, [_device_id(hass, entry)], raw_ad_entity=NEW_RAW, reset_calibration=True)

    assert err.value.translation_key == "calibration_needed"
    assert entry.options["raw_ad_entity"] == OLD_RAW


@pytest.mark.parametrize(
    ("data", "error"),
    [
        ({}, "one_source"),
        ({"raw_ad_entity": NEW_RAW, "moisture_entity": MOISTURE}, "one_source"),
        ({"moisture_entity": MOISTURE, "ad0": 70}, "ad_needs_raw"),
        ({"raw_ad_entity": NEW_RAW, "ad0": 300}, "point_out_of_range"),
        ({"raw_ad_entity": NEW_RAW, "ad0": 100, "ad100": 105}, "span_too_small"),
    ],
)
async def test_invalid_calls_change_nothing(
    hass: HomeAssistant, data: dict[str, Any], error: str
) -> None:
    entry = await _wh51(hass)
    before = dict(entry.options)

    with pytest.raises(ServiceValidationError) as err:
        await _call(hass, [_device_id(hass, entry)], **data)

    assert err.value.translation_key == error
    assert dict(entry.options) == before


async def test_a_refused_probe_stops_the_whole_call(hass: HomeAssistant) -> None:
    first = await _wh51(hass)
    second = await _setup(
        hass, "Planter", model="generic", moisture_entity=MOISTURE, pct0=0, pct100=100
    )

    with pytest.raises(ServiceValidationError):
        await _call(
            hass, [_device_id(hass, first), _device_id(hass, second)], raw_ad_entity=NEW_RAW
        )

    assert first.options["raw_ad_entity"] == OLD_RAW
    assert second.options["moisture_entity"] == MOISTURE


async def test_a_device_of_another_integration_is_refused(hass: HomeAssistant) -> None:
    await _wh51(hass)
    other = MockConfigEntry(domain="mqtt")
    other.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=other.entry_id, identifiers={("mqtt", "probe")}
    )

    with pytest.raises(ServiceValidationError):
        await _call(hass, [device.id], raw_ad_entity=NEW_RAW)
