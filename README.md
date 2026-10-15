# Digital Spirometer

## Circuit

![Circuit diagram](circuit-diagram.svg)

The device runs on a 3.7 V 1100 mAh Li-ion battery. The battery connects to a charge/boost module on BAT+ and BAT−. The module charges the battery and steps its output up to 5 V, which is set with the module's potentiometer. The module's output goes to the ESP32's VIN and GND pins, and the ESP32's onboard regulator turns that into 3.3 V. The VL53L0X time-of-flight sensor runs off the ESP32's 3V3 and GND pins and talks to it over I²C: SDA on D21 and SCL on D22.

## Database

- Breath data is stored in Supabase in the `sessions` table, one row per breath (volume, duration, peak flow, outcome, check-in answers). Rows are keyed on device ID + timestamp, so re-sending a record updates it instead of making a duplicate.
- The ESP32 doesn't connect to the internet. The phone does the syncing: after a breath is saved, and again after the check-in, the web app pulls the last 20 records off the device and pushes them all to Supabase.
- The phone needs internet while it's on the SmartSpirometer network, which usually means cellular data. If a sync fails nothing is shown, and it just retries after the next breath. The device only keeps 20 records, so a breath can get dropped if it isn't synced before it falls off the end.

## Tracking

- An analog spirometer only shows the patient a number in the moment. Nothing gets recorded, so whether they actually did their breaths, and whether they're getting better, comes down to memory.
- This device logs every breath with a timestamp, so the care team can see two things over the recovery program: **adherence** (breaths done each day against the daily goal) and **inspiratory capacity** (best breath each day against the volume goal).
- Both can be flagged automatically, like when someone stops doing their breaths, or when their volume stops improving. That's a cue to check in early instead of finding out at the next appointment.
- The charts below use simulated data to show what on-track and flagged patients look like. Volumes under 500 mL are greyed out since the sensor can't read them (see Limitations). They're made with Plotly. Each chart also has an interactive `.html` version in `charts/` with hover tooltips. To regenerate them, run `pip install -r charts/requirements.txt` and then `python3 charts/generate_charts.py`.

| On track | Flagged |
|---|---|
| ![Adherence on track](charts/adherence_good.svg) | ![Adherence falling off](charts/adherence_bad.svg) |
| ![Inspiratory capacity improving](charts/ic_improving.svg) | ![Inspiratory capacity not improving](charts/ic_stagnant.svg) |

## Limitations

- Volume is measured with a VL53L0X time-of-flight sensor pointed at the piston. It's cheap and easy to wire up, but it isn't very accurate at close range. Below about 40 mm the readings bunch up and can even go backwards, so anything under ~500 mL can't be told apart from an empty chamber.
- Because of that, a breath only counts once the volume passes 750 mL. That's when timing starts and the score begins tracking. The extra margin above the ~500 mL blind spot keeps sensor noise from starting a breath by accident. Any breath that peaks below 750 mL won't register at all. While waiting for a breath, the app shows anything under 500 mL as 0 so the noise doesn't flicker on screen.
- Readings are also a bit noisy, so they're averaged over a few samples, which slows the response slightly.
- A more precise (and more expensive) ToF sensor built for short range would fix most of this. It could pick up the small piston movements at the bottom of the chamber, which would let the device measure lower volumes and start timing a breath sooner.
