// ================================================================
// ToF Test: standalone VL53L0X sanity check for the Smart Spirometer
//
// Reads the sensor in continuous mode and prints the distance to
// Serial as fast as it comes in (~20 Hz). No WiFi or session logic.
//
// Wiring (ESP32 default I2C pins), I2C at 100 kHz:
//   VIN -> 3V3 (not 5V), GND -> GND, SDA -> GPIO 21, SCL -> GPIO 22
//
// Distance is converted to volume by piecewise-linear interpolation
// through measured calibration points (CAL_MM / CAL_ML), clamped to
// 0-4000 mL. The chamber isn't linear, so add points as you measure them.
// Anything at or below 500 mL reads 0 (below the sensor's minimum range). Volume is smoothed with the same 5-sample rolling
// average SmartSpirometer.ino uses.
//
// Output (115200 baud), one line per reading (raw distance + smoothed
// volume; the raw mm is what goes into the calibration table):
//   dist_mm:88,vol_ml:1947
// This format also works in the Arduino Serial Plotter.
// Invalid readings (out of range / no target) print as  vol_ml:-1
//
// Library: Adafruit_VL53L0X
// ================================================================

#include <Wire.h>
#include "Adafruit_VL53L0X.h"

#define I2C_SDA 21
#define I2C_SCL 22

const uint32_t TIMING_BUDGET_US = 50000;   // 50 ms -> ~20 Hz (longer = less noise)

// Calibration: averaged distance at known volumes, ascending order.
// Below ~40 mm the VL53L0X readings compress and even reverse: 500 mL
// reads closer (36.6 mm) than 0 mL (38.9 mm), so volumes at or under
// 500 mL are not resolvable at this mounting and are reported as 0
// (see DEADZONE_ML). 750 mL is usable but wanders ~+/-300 mL.
// 0 / 750 mL points measured at the 50 ms timing budget.
const float CAL_MM[] = { 38.9,  43.9,   51.1,   70.5,   88.8,  107.7,  128.1,  147.0,  163.9 };
const float CAL_ML[] = {  0.0, 750.0, 1000.0, 1500.0, 2000.0, 2500.0, 3000.0, 3500.0, 4000.0 };
const int   CAL_N    = sizeof(CAL_MM) / sizeof(CAL_MM[0]);
const float MAX_ML   = 4000.0;

// Smoothed volumes at or below this read as 0 (sensor can't resolve them)
const float DEADZONE_ML = 500.0;

// ---- Rolling average: volume ----
const int ROLLING_N = 5;
float volBuffer[ROLLING_N];
int   bufIdx  = 0;
bool  bufFull = false;

Adafruit_VL53L0X lox = Adafruit_VL53L0X();

// Unclamped, so noise around 0 / 4000 mL averages out instead of
// being biased by the clamp; clamp after averaging.
float mmToML(float mm) {
  // Find the segment containing mm (end segments extrapolate)
  int i = 0;
  while (i < CAL_N - 2 && mm > CAL_MM[i + 1]) i++;
  float t = (mm - CAL_MM[i]) / (CAL_MM[i + 1] - CAL_MM[i]);
  return CAL_ML[i] + t * (CAL_ML[i + 1] - CAL_ML[i]);
}

float getRollingAvg(float newVal) {
  volBuffer[bufIdx] = newVal;
  bufIdx = (bufIdx + 1) % ROLLING_N;
  if (bufIdx == 0) bufFull = true;
  int count = bufFull ? ROLLING_N : bufIdx;
  float sum = 0;
  for (int i = 0; i < count; i++) sum += volBuffer[i];
  return sum / count;
}

bool initToFSensor() {
  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(100000);
  if (!lox.begin()) return false;
  Serial.println("VL53L0X found: SDA=21, SCL=22");
  return true;
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n=== ToF sensor test ===");

  if (!initToFSensor()) {
    Serial.println("[ERROR] Could not communicate with VL53L0X. Check wiring (SDA=21, SCL=22).");
    while (true) delay(1000);
  }

  lox.setMeasurementTimingBudgetMicroSeconds(TIMING_BUDGET_US);
  lox.startRangeContinuous(TIMING_BUDGET_US / 1000);
}

void loop() {
  if (!lox.isRangeComplete()) return;

  uint16_t mm = lox.readRangeResult();   // 0xffff when invalid
  if (mm >= 8190) {                     // invalid: keep it out of the average
    Serial.println("vol_ml:-1");
    return;
  }

  // Compute first: constrain() is a macro and would call getRollingAvg()
  // (and push into the buffer) more than once.
  float ml = getRollingAvg(mmToML(mm));
  ml = constrain(ml, 0, MAX_ML);
  if (ml <= DEADZONE_ML) ml = 0;

  Serial.print("dist_mm:");
  Serial.print(mm);
  Serial.print(",vol_ml:");
  Serial.println((int)lroundf(ml));
}
