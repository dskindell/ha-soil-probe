"""Config flow for Soil Probe."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector
import probatio

from .const import DOMAIN

USER_SCHEMA = probatio.Schema({probatio.Required(CONF_NAME): selector.TextSelector()})


class SoilProbeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add a probe."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Name the probe."""
        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_NAME], data={})
        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA)
