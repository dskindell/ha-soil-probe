"""The calibrated moisture sensor and the probe's device."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
import pytest
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed

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


BATTERY = "sensor.wh51_battery"


async def test_raw_and_battery_are_copied_onto_the_device(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    hass.states.async_set(RAW, "285")
    hass.states.async_set(BATTERY, "100")
    entry = await _setup(
        hass, model="wh51", raw_ad_entity=RAW, battery_entity=BATTERY, ad0=70, ad100=500
    )

    raw = hass.states.get("sensor.backyard_central_raw_ad")
    battery = hass.states.get("sensor.backyard_central_battery")
    assert raw is not None
    assert battery is not None
    assert float(raw.state) == 285
    assert float(battery.state) == 100
    assert battery.attributes["device_class"] == "battery"
    assert battery.attributes["unit_of_measurement"] == "%"
    for entity_id in ("sensor.backyard_central_raw_ad", "sensor.backyard_central_battery"):
        entity = entity_registry.async_get(entity_id)
        assert entity is not None
        assert entity.entity_category is er.EntityCategory.DIAGNOSTIC
        assert entity.config_entry_id == entry.entry_id

    hass.states.async_set(BATTERY, STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.backyard_central_battery").state == STATE_UNAVAILABLE  # type: ignore[union-attr]


async def test_copies_without_a_source_are_left_out_and_removed(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    entry = await _setup(
        hass, model="wh51", raw_ad_entity=RAW, battery_entity=BATTERY, ad0=70, ad100=500
    )
    assert entity_registry.async_get("sensor.backyard_central_battery") is not None

    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"], {"moisture_entity": MOISTURE}
    )
    await hass.async_block_till_done()

    assert entity_registry.async_get("sensor.backyard_central_battery") is None
    assert entity_registry.async_get("sensor.backyard_central_raw_ad") is None
    assert entity_registry.async_get(OUTPUT) is not None


async def test_no_update_timeout_makes_sensors_unavailable(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    hass.states.async_set(RAW, "285")
    hass.states.async_set(BATTERY, "100")
    await _setup(hass, model="wh51", raw_ad_entity=RAW, battery_entity=BATTERY, ad0=70, ad100=500)
    timeout = "number.backyard_central_unavailable_after_no_update"
    assert float(hass.states.get(timeout).state) == 0  # type: ignore[union-attr]
    assert hass.states.get(timeout).attributes["unit_of_measurement"] == "min"  # type: ignore[union-attr]

    # Off by default: an hour without updates changes nothing.
    freezer.tick(timedelta(hours=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert float(hass.states.get(OUTPUT).state) == 50.0  # type: ignore[union-attr]

    await hass.services.async_call(
        "number", "set_value", {"entity_id": timeout, "value": 10}, blocking=True
    )
    # The sources last reported an hour ago, so the new timeout applies at once.
    for entity_id in (OUTPUT, "sensor.backyard_central_raw_ad", "sensor.backyard_central_battery"):
        assert hass.states.get(entity_id).state == STATE_UNAVAILABLE  # type: ignore[union-attr]

    hass.states.async_set(RAW, "285")
    await hass.async_block_till_done()
    assert float(hass.states.get(OUTPUT).state) == 50.0  # type: ignore[union-attr]

    freezer.tick(timedelta(minutes=9))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert float(hass.states.get(OUTPUT).state) == 50.0  # type: ignore[union-attr]

    freezer.tick(timedelta(minutes=2))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(OUTPUT).state == STATE_UNAVAILABLE  # type: ignore[union-attr]


async def test_a_repeated_value_counts_as_an_update(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    hass.states.async_set(RAW, "285")
    await _setup(hass, model="wh51", raw_ad_entity=RAW, ad0=70, ad100=500, stale_minutes=10)

    freezer.tick(timedelta(minutes=8))
    hass.states.async_set(RAW, "285")  # same value: reported, not changed
    freezer.tick(timedelta(minutes=8))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert float(hass.states.get(OUTPUT).state) == 50.0  # type: ignore[union-attr]
