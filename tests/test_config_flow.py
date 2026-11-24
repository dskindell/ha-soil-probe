"""Adding a probe from the UI."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.soil_probe.const import DOMAIN


async def test_user_step_creates_entry_named_after_the_probe(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Backyard Central"}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Backyard Central"
    assert result["data"] == {}
