# Changelog

All notable changes are listed here. Versions follow [Semantic Versioning](https://semver.org/); betas are published as GitHub pre-releases, which HACS offers only to those who turn on the repository's pre-release switch.

## [0.1.0-beta.4] - 2026-11-24

### Fixed

- `Needs water` is off (no problem) while `Low moisture threshold` is 0, instead of unavailable. It is still unavailable whenever moisture is unavailable.

## [0.1.0-beta.3] - 2026-11-24

### Added

- A `Needs water` sensor on each probe, with `Low moisture threshold` (0, the default, turns it off) and `Low moisture margin` (2 % by default) on the device page. It turns on when moisture drops below the threshold and off again at the threshold plus the margin, for watering alerts or irrigation automations.

## [0.1.0-beta.2] - 2026-11-24

### Added

- A `soil_probe.set_sources` action that sets a probe's sensors in one call, for example the new raw AD and battery sensors after replacing a probe. `reset_calibration` returns to the model's defaults; `ad0` and `ad100` set the calibration points.
- Usage documentation in the README.

## [0.1.0-beta.1] - 2026-11-24

First release.

### Added

- Add a probe from the UI: a name, a model (Ecowitt WH51, Ecowitt WH51L or Generic), a raw AD sensor or a moisture % sensor, and an optional battery sensor. Generic probes with a raw AD sensor also ask for the raw readings at 0 % and 100 %.
- Configure changes a probe's sensors. A renamed sensor is followed.
- One device per probe, with a `Moisture` sensor calibrated from the raw AD reading between two points: the raw readings at 0 % and 100 % moisture. A moisture % source can be corrected the same way.
- The two calibration points as numbers on the device page.
- `Capture dry` and `Capture wet` buttons that set a calibration point so the current reading matches a target (10 % dry and 95 % wet by default, also numbers on the device page), and a `Reset calibration` button that returns to the model's defaults.
- `Battery` and `Raw AD` sensors on the device, copied from their sources.
- An optional `Unavailable after no update` timeout per probe.
