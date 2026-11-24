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
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector
import probatio

from .const import (
    CONF_AD0,
    CONF_AD100,
    CONF_BATTERY_SOURCE,
    CONF_MODEL,
    CONF_MOISTURE_SOURCE,
    CONF_RAW_SOURCE,
    DOMAIN,
    SOURCE_KEYS,
)
from .models import MIN_SPAN, MODELS

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
    """Exactly one of raw AD and moisture % must be given."""
    if (CONF_RAW_SOURCE in user_input) == (CONF_MOISTURE_SOURCE in user_input):
        return {"base": "one_source"}
    return {}


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


def _with_sources(options: dict[str, Any], user_input: dict[str, Any]) -> dict[str, Any]:
    """Replace the sources in options with those in user_input; a missing one is removed."""
    kept = {key: value for key, value in options.items() if key not in SOURCE_KEYS}
    return kept | {key: user_input[key] for key in SOURCE_KEYS if key in user_input}


def _needs_calibration(options: dict[str, Any]) -> bool:
    return CONF_RAW_SOURCE in options and CONF_AD0 not in options


def _with_preset(options: dict[str, Any]) -> dict[str, Any]:
    """Add the model's default calibration when a raw source has none yet."""
    model = MODELS[options[CONF_MODEL]]
    if not _needs_calibration(options) or model.ad0 is None or model.ad100 is None:
        return options
    return options | {CONF_AD0: model.ad0, CONF_AD100: model.ad100}


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
        if user_input is not None and not (errors := _source_errors(user_input)):
            self._title = user_input[CONF_NAME]
            self._options = _with_preset(
                _with_sources({CONF_MODEL: user_input[CONF_MODEL]}, user_input)
            )
            if _needs_calibration(self._options):
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
            self._options = _with_preset(_with_sources(dict(self.config_entry.options), user_input))
            if _needs_calibration(self._options):
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
