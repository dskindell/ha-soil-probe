"""Probe models and their calibration presets.

Adding a model is one entry in MODELS; the setup form's model picker is built from it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, kw_only=True)
class ProbeModel:
    """A probe model's device info, default calibration and calibration limits."""

    name: str
    """Shown in the model picker as is, so it needs no translation."""
    manufacturer: str | None
    model: str | None
    ad0: int | None
    """Raw AD reading at 0 % moisture; None means the user enters it at setup."""
    ad100: int | None
    """Raw AD reading at 100 % moisture; None means the user enters it at setup."""
    ad0_max: int
    ad100_max: int


GENERIC: Final = "generic"

# AD100 must be at least this far above AD0 to keep the formula's slope sane.
MIN_SPAN: Final = 10

MODELS: Final[dict[str, ProbeModel]] = {
    # WH51 and WH51L manuals: 70 dry, 500 wet; AD0 0-200, AD100 up to 1000.
    "wh51": ProbeModel(
        name="Ecowitt WH51",
        manufacturer="Ecowitt",
        model="WH51",
        ad0=70,
        ad100=500,
        ad0_max=200,
        ad100_max=1000,
    ),
    "wh51l": ProbeModel(
        name="Ecowitt WH51L",
        manufacturer="Ecowitt",
        model="WH51L",
        ad0=70,
        ad100=500,
        ad0_max=200,
        ad100_max=1000,
    ),
    GENERIC: ProbeModel(
        name="Generic",
        manufacturer=None,
        model=None,
        ad0=None,
        ad100=None,
        ad0_max=65535,
        ad100_max=65535,
    ),
}
