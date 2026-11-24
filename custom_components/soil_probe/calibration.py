"""Two-point calibration: map a source reading to moisture %, and solve points from a capture."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import State
from homeassistant.exceptions import ServiceValidationError

from .const import (
    CONF_AD0,
    CONF_AD100,
    CONF_MODEL,
    CONF_PCT0,
    CONF_PCT100,
    CONF_RAW_SOURCE,
    DOMAIN,
)
from .models import MIN_SPAN, MODELS


def calibration_keys(options: Mapping[str, Any]) -> tuple[str, str]:
    """Option keys of the source readings at 0 % and at 100 % moisture."""
    if CONF_RAW_SOURCE in options:
        return CONF_AD0, CONF_AD100
    return CONF_PCT0, CONF_PCT100


def point_limits(options: Mapping[str, Any]) -> dict[str, tuple[int, int]]:
    """Allowed range of each calibration point."""
    if CONF_RAW_SOURCE in options:
        model = MODELS[options[CONF_MODEL]]
        return {CONF_AD0: (0, model.ad0_max), CONF_AD100: (MIN_SPAN, model.ad100_max)}
    return {CONF_PCT0: (0, 100 - MIN_SPAN), CONF_PCT100: (MIN_SPAN, 100)}


def reading_of(state: State | None) -> float | None:
    """The source's numeric reading, or None when it has none."""
    if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
        return None
    try:
        return float(state.state)
    except ValueError:
        return None


def calibrated_moisture(reading: float, at0: float, at100: float) -> float:
    """Moisture % from a source reading and its readings at 0 % and 100 %, clamped to 0-100."""
    return min(100.0, max(0.0, (reading - at0) * 100 / (at100 - at0)))


def solve_at0(reading: float, at100: float, target: float) -> float:
    """The 0 % point that makes reading come out as target %, keeping the 100 % point."""
    return (100 * reading - target * at100) / (100 - target)


def solve_at100(reading: float, at0: float, target: float) -> float:
    """The 100 % point that makes reading come out as target %, keeping the 0 % point."""
    return at0 + (reading - at0) * 100 / target


def check_points(options: Mapping[str, Any]) -> None:
    """Raise if a calibration point is out of range or the two are too close."""
    low, high = calibration_keys(options)
    for key, (minimum, maximum) in point_limits(options).items():
        if not minimum <= options[key] <= maximum:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="point_out_of_range",
                translation_placeholders={
                    "value": str(options[key]),
                    "min": str(minimum),
                    "max": str(maximum),
                },
            )
    if options[high] - options[low] < MIN_SPAN:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="span_too_small",
            translation_placeholders={"min_span": str(MIN_SPAN)},
        )
