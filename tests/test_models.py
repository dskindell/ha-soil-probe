"""The model table."""

from __future__ import annotations

import pytest

from custom_components.soil_probe.models import GENERIC, MIN_SPAN, MODELS, ProbeModel


@pytest.mark.parametrize("key", [key for key in MODELS if key != GENERIC])
def test_preset_calibration_is_within_its_limits(key: str) -> None:
    model = MODELS[key]
    assert model.ad0 is not None
    assert model.ad100 is not None
    assert 0 <= model.ad0 <= model.ad0_max
    assert model.ad0 + MIN_SPAN <= model.ad100 <= model.ad100_max


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("wh51", ("Ecowitt", "WH51", 70, 500)),
        ("wh51l", ("Ecowitt", "WH51L", 70, 500)),
        (GENERIC, (None, None, None, None)),
    ],
)
def test_model_presets(key: str, expected: tuple[object, ...]) -> None:
    model: ProbeModel = MODELS[key]
    assert (model.manufacturer, model.model, model.ad0, model.ad100) == expected
