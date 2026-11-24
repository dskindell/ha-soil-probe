"""Two-point calibration: map a source reading to moisture %."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .const import CONF_AD0, CONF_AD100, CONF_PCT0, CONF_PCT100, CONF_RAW_SOURCE


def calibration_keys(options: Mapping[str, Any]) -> tuple[str, str]:
    """Option keys of the source readings at 0 % and at 100 % moisture."""
    if CONF_RAW_SOURCE in options:
        return CONF_AD0, CONF_AD100
    return CONF_PCT0, CONF_PCT100


def calibrated_moisture(reading: float, at0: float, at100: float) -> float:
    """Moisture % from a source reading and its readings at 0 % and 100 %, clamped to 0-100."""
    return min(100.0, max(0.0, (reading - at0) * 100 / (at100 - at0)))
