"""Config and options flows for Soil Probe."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_NAME, MAX_LENGTH_STATE_STATE
from homeassistant.core import callback
from homeassistant.helpers import selector
import probatio

from .const import (
    CONF_AD0,
    CONF_AD100,
    CONF_BATTERY_SOURCE,
    CONF_LABEL,
    CONF_MODEL,
    CONF_MOISTURE_SOURCE,
    CONF_RAW_SOURCE,
    DOMAIN,
)
from .models import MIN_SPAN, MODELS
from .sources import has_one_source, needs_calibration, with_defaults, with_sources

_SENSOR = selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))

SOURCES_SCHEMA = probatio.Schema(
    {
        probatio.Optional(CONF_RAW_SOURCE): _SENSOR,
        probatio.Optional(CONF_MOISTURE_SOURCE): _SENSOR,
        probatio.Optional(CONF_BATTERY_SOURCE): _SENSOR,
    }
)

USER_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_NAME): selector.TextSelector(),
        probatio.Optional(CONF_LABEL): selector.TextSelector(),
        probatio.Required(CONF_MODEL): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value=key, label=model.name)
                    for key, model in MODELS.items()
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
    }
).extend(SOURCES_SCHEMA.schema)


def _source_errors(user_input: dict[str, Any]) -> dict[str, str]:
    return {} if has_one_source(user_input) else {"base": "one_source"}


def _user_errors(user_input: dict[str, Any]) -> dict[str, str]:
    if len(user_input.get(CONF_LABEL, "").strip()) > MAX_LENGTH_STATE_STATE:
        return {CONF_LABEL: "label_too_long"}
    return _source_errors(user_input)


def _label(user_input: dict[str, Any]) -> dict[str, str]:
    """The label to store; none means the label follows the device name."""
    label = user_input.get(CONF_LABEL, "").strip()
    return {CONF_LABEL: label} if label else {}


def _calibration_schema(model_key: str) -> probatio.Schema:
    model = MODELS[model_key]
    return probatio.Schema(
        {
            probatio.Required(CONF_AD0): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=model.ad0_max, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
            probatio.Required(CONF_AD100): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_SPAN,
                    max=model.ad100_max,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        }
    )


def _calibration_errors(user_input: dict[str, Any]) -> dict[str, str]:
    if user_input[CONF_AD100] - user_input[CONF_AD0] < MIN_SPAN:
        return {CONF_AD100: "span_too_small"}
    return {}


def _calibration(user_input: dict[str, Any]) -> dict[str, int]:
    return {CONF_AD0: int(user_input[CONF_AD0]), CONF_AD100: int(user_input[CONF_AD100])}


class SoilProbeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add a probe."""

    VERSION = 1

    def __init__(self) -> None:
        self._title = ""
        self._options: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Change a probe's sources."""
        return SoilProbeOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Name the probe and pick its model and sources."""
        errors: dict[str, str] = {}
        if user_input is not None and not (errors := _user_errors(user_input)):
            self._title = user_input[CONF_NAME]
            self._options = with_defaults(
                with_sources({CONF_MODEL: user_input[CONF_MODEL], **_label(user_input)}, user_input)
            )
            if needs_calibration(self._options):
                return await self.async_step_calibration()
            return self._create()
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_calibration(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the raw readings at 0 % and 100 % when the model has no preset."""
        errors: dict[str, str] = {}
        if user_input is not None and not (errors := _calibration_errors(user_input)):
            self._options |= _calibration(user_input)
            return self._create()
        return self.async_show_form(
            step_id="calibration",
            data_schema=self.add_suggested_values_to_schema(
                _calibration_schema(self._options[CONF_MODEL]), user_input
            ),
            errors=errors,
        )

    def _create(self) -> ConfigFlowResult:
        return self.async_create_entry(title=self._title, data={}, options=self._options)


class SoilProbeOptionsFlow(OptionsFlowWithReload):
    """Change a probe's sources; name and model stay as set up."""

    def __init__(self) -> None:
        self._options: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Pick the sources."""
        errors: dict[str, str] = {}
        if user_input is not None and not (errors := _source_errors(user_input)):
            self._options = with_defaults(with_sources(dict(self.config_entry.options), user_input))
            if needs_calibration(self._options):
                return await self.async_step_calibration()
            return self.async_create_entry(data=self._options)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                SOURCES_SCHEMA,
                self.config_entry.options if user_input is None else user_input,
            ),
            errors=errors,
        )

    async def async_step_calibration(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the raw readings at 0 % and 100 % when the model has no preset."""
        errors: dict[str, str] = {}
        if user_input is not None and not (errors := _calibration_errors(user_input)):
            return self.async_create_entry(data=self._options | _calibration(user_input))
        return self.async_show_form(
            step_id="calibration",
            data_schema=self.add_suggested_values_to_schema(
                _calibration_schema(self._options[CONF_MODEL]), user_input
            ),
            errors=errors,
        )
