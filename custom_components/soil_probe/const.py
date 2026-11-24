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

SOURCE_KEYS: Final = (CONF_RAW_SOURCE, CONF_MOISTURE_SOURCE, CONF_BATTERY_SOURCE)
