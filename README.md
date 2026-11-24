# Soil Probe

A Home Assistant custom integration that turns loose soil-probe entities into one device per probe,
with calibration you can edit in the UI and a calculated moisture sensor.

Cheap wireless soil probes, such as the Ecowitt / Fine Offset WH51 and WH51L, are often received
without the vendor's gateway, for example through rtl_433 and MQTT. Home Assistant then sees only
separate entities for moisture, the raw AD reading and battery, with no device and no calibration.
Soil Probe follows those entities and gives each probe a real device with a moisture sensor
calculated from the raw reading.

**Status:** in development; not released yet.

Requires Home Assistant 2026.11 or newer.
