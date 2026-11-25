"""Constants for Soil Probe."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "soil_probe"

CONF_MODEL: Final = "model"
CONF_RAW_SOURCE: Final = "raw_ad_entity"
CONF_MOISTURE_SOURCE: Final = "moisture_entity"
CONF_BATTERY_SOURCE: Final = "battery_entity"
CONF_AD0: Final = "ad0"
CONF_AD100: Final = "ad100"
CONF_PCT0: Final = "pct0"
CONF_PCT100: Final = "pct100"
CONF_DRY_TARGET: Final = "dry_target"
CONF_WET_TARGET: Final = "wet_target"
CONF_STALE_MINUTES: Final = "stale_minutes"
CONF_LOW_THRESHOLD: Final = "low_threshold"
CONF_THRESHOLD_MARGIN: Final = "threshold_margin"

# 0 turns the low-moisture threshold off.
DEFAULT_LOW_THRESHOLD: Final = 0
DEFAULT_THRESHOLD_MARGIN: Final = 2

# Ecowitt's own calibration procedure aims for these readings in air and in water.
DEFAULT_DRY_TARGET: Final = 10
DEFAULT_WET_TARGET: Final = 95

SOURCE_KEYS: Final = (CONF_RAW_SOURCE, CONF_MOISTURE_SOURCE, CONF_BATTERY_SOURCE)


def calibration_signal(entry_id: str) -> str:
    """Dispatcher signal sent when a probe's calibration or other settings change."""
    return f"{DOMAIN}_{entry_id}_calibration"
