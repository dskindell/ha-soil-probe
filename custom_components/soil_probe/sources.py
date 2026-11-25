"""Rules for a probe's sources, shared by Configure and the set_sources action."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .const import (
    CONF_AD0,
    CONF_AD100,
    CONF_MODEL,
    CONF_MOISTURE_SOURCE,
    CONF_PCT0,
    CONF_PCT100,
    CONF_RAW_SOURCE,
    SOURCE_KEYS,
)
from .models import MODELS

CALIBRATION_KEYS = (CONF_AD0, CONF_AD100, CONF_PCT0, CONF_PCT100)


def has_one_source(sources: Mapping[str, Any]) -> bool:
    """Exactly one of raw AD and moisture % is given."""
    return (CONF_RAW_SOURCE in sources) != (CONF_MOISTURE_SOURCE in sources)


def with_sources(options: Mapping[str, Any], sources: Mapping[str, Any]) -> dict[str, Any]:
    """Replace the sources in options with the given ones; a missing one is removed."""
    kept = {key: value for key, value in options.items() if key not in SOURCE_KEYS}
    return kept | {key: sources[key] for key in SOURCE_KEYS if key in sources}


def needs_calibration(options: Mapping[str, Any]) -> bool:
    """A raw source missing a calibration point, which only the user can supply."""
    return CONF_RAW_SOURCE in options and not (CONF_AD0 in options and CONF_AD100 in options)


def with_defaults(options: dict[str, Any]) -> dict[str, Any]:
    """Fill in missing calibration points for the chosen source from its defaults."""
    if CONF_MOISTURE_SOURCE in options:
        # 0 and 100 leave the source's percentage unchanged.
        return {CONF_PCT0: 0, CONF_PCT100: 100} | options
    model = MODELS[options[CONF_MODEL]]
    if CONF_RAW_SOURCE not in options or model.ad0 is None or model.ad100 is None:
        return options
    return {CONF_AD0: model.ad0, CONF_AD100: model.ad100} | options


def without_calibration(options: Mapping[str, Any]) -> dict[str, Any]:
    """Options with the calibration points removed, so defaults apply again."""
    return {key: value for key, value in options.items() if key not in CALIBRATION_KEYS}
