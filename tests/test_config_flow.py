"""Adding a probe from the UI and changing its sources later."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.soil_probe.const import DOMAIN

RAW = "sensor.backyard_central_ad"
MOISTURE = "sensor.backyard_central_moisture"
BATTERY = "sensor.backyard_central_battery"


async def _start(hass: HomeAssistant) -> dict[str, Any]:
    return dict(await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER}))


async def test_preset_model_with_raw_source_uses_the_preset_calibration(
    hass: HomeAssistant,
) -> None:
    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Backyard Central",
            "model": "wh51l",
            "raw_ad_entity": RAW,
            "battery_entity": BATTERY,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Backyard Central"
    assert result["data"] == {}
    assert result["options"] == {
        "model": "wh51l",
        "raw_ad_entity": RAW,
        "battery_entity": BATTERY,
        "ad0": 70,
        "ad100": 500,
    }


async def test_moisture_source_needs_no_calibration(hass: HomeAssistant) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "Planter", "model": "generic", "moisture_entity": MOISTURE},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"] == {
        "model": "generic",
        "moisture_entity": MOISTURE,
        "pct0": 0,
        "pct100": 100,
    }


@pytest.mark.parametrize(
    "sources",
    [{}, {"raw_ad_entity": RAW, "moisture_entity": MOISTURE}],
    ids=["neither", "both"],
)
async def test_exactly_one_of_raw_and_moisture_is_required(
    hass: HomeAssistant, sources: dict[str, str]
) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Planter", "model": "wh51"} | sources
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "one_source"}


async def test_generic_model_with_raw_source_asks_for_calibration(hass: HomeAssistant) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Planter", "model": "generic", "raw_ad_entity": RAW}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "calibration"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"ad0": 100, "ad100": 105}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"ad100": "span_too_small"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"ad0": 100.0, "ad100": 2000.0}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"] == {
        "model": "generic",
        "raw_ad_entity": RAW,
        "ad0": 100,
        "ad100": 2000,
    }


async def test_a_source_another_probe_uses_is_allowed(hass: HomeAssistant) -> None:
    MockConfigEntry(
        domain=DOMAIN, options={"model": "wh51", "raw_ad_entity": RAW, "ad0": 70, "ad100": 500}
    ).add_to_hass(hass)

    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Second", "model": "wh51", "raw_ad_entity": RAW}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY


def _entry(hass: HomeAssistant, **options: Any) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="Backyard Central", options=options)
    entry.add_to_hass(hass)
    return entry


async def test_options_swap_sources_and_keep_calibration(hass: HomeAssistant) -> None:
    entry = _entry(hass, model="wh51", raw_ad_entity=RAW, battery_entity=BATTERY, ad0=80, ad100=450)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"raw_ad_entity": "sensor.new_probe_ad"}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options == {
        "model": "wh51",
        "raw_ad_entity": "sensor.new_probe_ad",
        "ad0": 80,
        "ad100": 450,
    }


async def test_options_require_exactly_one_of_raw_and_moisture(hass: HomeAssistant) -> None:
    entry = _entry(hass, model="wh51", raw_ad_entity=RAW, ad0=70, ad100=500)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"raw_ad_entity": RAW, "moisture_entity": MOISTURE}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "one_source"}


async def test_options_switch_to_raw_on_a_preset_model_uses_the_preset(
    hass: HomeAssistant,
) -> None:
    entry = _entry(hass, model="wh51", moisture_entity=MOISTURE)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"raw_ad_entity": RAW}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options == {"model": "wh51", "raw_ad_entity": RAW, "ad0": 70, "ad100": 500}


async def test_options_switch_to_raw_on_generic_asks_for_calibration(
    hass: HomeAssistant,
) -> None:
    entry = _entry(hass, model="generic", moisture_entity=MOISTURE)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"raw_ad_entity": RAW}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "calibration"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"ad0": 300, "ad100": 300}
    )
    assert result["errors"] == {"ad100": "span_too_small"}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"ad0": 300, "ad100": 3000}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options == {"model": "generic", "raw_ad_entity": RAW, "ad0": 300, "ad100": 3000}
