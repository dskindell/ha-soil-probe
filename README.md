# Soil Probe

A Home Assistant custom integration that turns loose soil-probe entities into one device per probe,
with calibration you can edit in the UI and a calculated moisture sensor.

For soil probes such as the Ecowitt WH51 and WH51L when you use rtl_433 instead of the Ecowitt
gateway. Home Assistant then gets separate moisture, raw AD and battery entities, with no device and
no calibration. Soil Probe turns those into one device per probe with a calibrated moisture sensor.

**Status:** in development; not released yet.

Requires Home Assistant 2026.11 or newer.
