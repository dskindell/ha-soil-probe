# Soil Probe

A Home Assistant custom integration that turns loose soil-probe entities into one device per probe,
with calibration you can edit in the UI and a calculated moisture sensor.

For soil probes such as the Ecowitt WH51 and WH51L when you use rtl_433 instead of the Ecowitt
gateway. Home Assistant then gets separate moisture, raw AD and battery entities, with no device and
no calibration. Soil Probe turns those into one device per probe with a calibrated moisture sensor.

**Status:** beta. The first release is `0.1.0-beta.1`.

Requires Home Assistant 2026.11 or newer.

## Install

In HACS (the Marketplace), add `https://github.com/dskindell/ha-soil-probe` as a custom repository
of type Integration, then download Soil Probe. Restart Home Assistant.

## Add a probe

Settings → Devices & services → Add integration → Soil Probe. Add one entry per probe:

- **Name:** the device name, for example the probe's location.
- **Model:** Ecowitt WH51, Ecowitt WH51L or Generic. The model sets the default calibration and the
  device's manufacturer and model. It can't be changed later; to change it, delete the probe and add
  it again.
- **Raw AD sensor** or **Moisture % sensor:** give exactly one. Use the raw AD sensor when the probe
  has one; only raw AD can be calibrated dry and wet.
- **Battery sensor:** optional.

A Generic probe with a raw AD sensor also asks for its raw AD reading at 0 % and at 100 % moisture.

Any sensor can be picked, and the same sensor can be used by more than one probe. Soil Probe doesn't
change the source sensors. If a source sensor with a unique ID is renamed, the probe follows it; if
it's deleted, a warning is logged and the probe's sensors go unavailable until you pick a new one.

To change a probe's sensors later, open the probe's entry and choose Configure, or use the
`soil_probe.set_sources` action below.

## The probe's device

Each probe is one device, which you can rename and give an area like any other.

| Entity | When | What it is |
| --- | --- | --- |
| Moisture | always | Soil moisture in %, calibrated. Long-term statistics are recorded. |
| Raw AD | raw AD source | A copy of the raw reading (diagnostic). |
| Battery | battery source | A copy of the battery reading (diagnostic). |
| Raw AD at 0 %, Raw AD at 100 % | raw AD source | The calibration points. |
| Source % at 0 %, Source % at 100 % | moisture % source | The correction points; 0 and 100 leave the reading unchanged. |
| Dry capture target, Wet capture target | raw AD source | The readings the capture buttons aim for; 10 % and 95 % by default. |
| Capture dry, Capture wet | raw AD source | Calibrate from the current reading. |
| Reset calibration | raw AD source, not Generic | Back to the model's default calibration. |
| Unavailable after no update | always | Minutes without a report before the sensors go unavailable; 0 turns it off. |

Moisture is `(reading − point at 0 %) × 100 / (point at 100 % − point at 0 %)`, kept between 0 and
100 %. The WH51 and WH51L defaults are 70 and 500, from Ecowitt's manuals.

When a source sensor is unavailable, unknown or not a number, the entities copied from it are
unavailable too. They come back with its next reading.

## Calibrate

Ecowitt's procedure for the WH51L (manual pp. 22–24), with the capture buttons:

1. Take the probe out of the soil and wipe it dry. Once the raw AD reading has settled, press
   **Capture dry**. This sets Raw AD at 0 % so the current reading shows as the dry target (10 %).
2. Put the probe in water up to its line. Once the reading has settled, press **Capture wet**. This
   sets Raw AD at 100 % so the current reading shows as the wet target (95 %).
3. Put the probe back in the soil.

Set the targets to 0 and 100 to capture straight to 0 % and 100 %. You can also type the two points
in directly, for example from recorded data. The two points must stay at least 10 apart, and a
capture without a reading is refused. Each capture and reset is logged at info level.

## Action: `soil_probe.set_sources`

Sets a probe's sensors, for example after replacing the probe:

```yaml
action: soil_probe.set_sources
data:
  device_id: <the probe's device>
  raw_ad_entity: sensor.new_probe_ad_raw
  battery_entity: sensor.new_probe_battery
  reset_calibration: true
```

| Field | |
| --- | --- |
| `device_id` | Required. One or more probe devices; each gets the same sensors. |
| `raw_ad_entity` or `moisture_entity` | Exactly one is required. |
| `battery_entity` | Optional. Left out, the probe has no battery sensor. |
| `reset_calibration` | Default `false`, which keeps the calibration. `true` goes back to the model's defaults (0 and 100 for a moisture % probe). |
| `ad0`, `ad100` | Optional calibration points to set. Required for a Generic probe that is reset or gets its first raw AD sensor. |

The sensors given replace the probe's sensors. A refused call changes no probe. Each changed probe
reloads.
