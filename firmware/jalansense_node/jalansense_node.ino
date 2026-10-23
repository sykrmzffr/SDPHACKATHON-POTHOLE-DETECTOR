/*
  JalanSense IoT node - ESP32 + MPU6050 + NEO-6M GPS

  Mounted on township fleet vehicles (shuttles, security patrol, waste trucks).
  Samples the IMU at 50 Hz, triggers on a vertical jolt, extracts features
  over a 2 s window, classifies on-device (pothole / speed bump / rough /
  smooth) using the decision tree exported by ml/train.py (model.h), and
  sends pothole events with GPS location to the JalanSense backend.

  Wiring (ESP32 DevKit v1)
    MPU6050  VCC->3V3  GND->GND  SDA->GPIO21  SCL->GPIO22
    NEO-6M   VCC->3V3(or 5V per module)  GND->GND  TX->GPIO16  RX->GPIO17
    LED      GPIO2 (on-board) blinks on pothole detection
    BUTTON   GPIO0 (BOOT) = send a test pothole (for desk demos)

  Libraries: TinyGPSPlus (Library Manager). Everything else is ESP32 core.
  Mount: MPU6050 flat, Z axis pointing up, rigidly fixed to the chassis/dashboard.
*/
#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <TinyGPSPlus.h>
#include "config.h"
#include "js_features.h"
#include "model.h"

#define MPU_ADDR 0x68
#define WIN 100          // 2 s at 50 Hz
#define POST_TRIGGER 50  // wait 1 s after trigger so the jolt is centred
#define TRIGGER_G 0.35f
#define LED_PIN 2
#define BTN_PIN 0
#define QUEUE_MAX 30

TinyGPSPlus gps;
HardwareSerial GPSSerial(2);

float bufZ[WIN], bufX[WIN], bufG[WIN];
int head = 0, filled = 0;
float gravityZ = 1.0f;          // running estimate (handles slopes / mounting tilt)
int countdown = -1;             // samples until window is evaluated
unsigned long lastTick = 0, lastTrigger = 0;

String queue[QUEUE_MAX];        // events waiting for WiFi
int qLen = 0;

// ---------------------------------------------------------------- MPU6050
void mpuWrite(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(MPU_ADDR); Wire.write(reg); Wire.write(val); Wire.endTransmission();
}
bool mpuRead(float& axg, float& azg, float& gxd) {
  Wire.beginTransmission(MPU_ADDR); Wire.write(0x3B);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(MPU_ADDR, 14) != 14) return false;
  int16_t r[7];
  for (int i = 0; i < 7; i++) r[i] = (Wire.read() << 8) | Wire.read();
  axg = r[0] / 8192.0f;           // +-4 g range
  azg = r[2] / 8192.0f;
  gxd = r[4] / 65.5f;             // +-500 dps range
  return true;
}
void mpuInit() {
  mpuWrite(0x6B, 0x00);           // wake
  mpuWrite(0x1A, 0x03);           // DLPF ~44 Hz
  mpuWrite(0x1B, 0x08);           // gyro +-500 dps
  mpuWrite(0x1C, 0x08);           // accel +-4 g
  delay(100);
  float s = 0, ax, az, gx; int n = 0;
  for (int i = 0; i < 100; i++) { if (mpuRead(ax, az, gx)) { s += az; n++; } delay(10); }
  if (n) gravityZ = s / n;
  Serial.printf("MPU ready, gravity Z = %.3f g\n", gravityZ);
}

// ---------------------------------------------------------------- network
void wifiConnect() {
  if (WiFi.status() == WL_CONNECTED) return;
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
}

bool postJson(const String& body) {
  if (WiFi.status() != WL_CONNECTED) return false;
  HTTPClient http;
  http.begin(API_URL);
  http.addHeader("Content-Type", "application/json");
  int code = http.POST(body);
  http.end();
  return code > 0 && code < 300;
}

void flushQueue() {
  while (qLen > 0 && postJson(queue[0])) {
    for (int i = 1; i < qLen; i++) queue[i - 1] = queue[i];
    qLen--;
  }
}

void enqueue(const String& body) {
  if (postJson(body)) return;
  if (qLen == QUEUE_MAX) { for (int i = 1; i < qLen; i++) queue[i - 1] = queue[i]; qLen--; }
  queue[qLen++] = body;            // store-and-forward when out of coverage
  Serial.printf("queued (%d waiting)\n", qLen);
}

// ---------------------------------------------------------------- detection
void evaluateWindow() {
  float z[WIN], x[WIN], g[WIN];
  for (int i = 0; i < WIN; i++) {  // unroll ring buffer oldest -> newest
    int k = (head + i) % WIN;
    z[i] = bufZ[k]; x[i] = bufX[k]; g[i] = bufG[k];
  }
  bool fix = gps.location.isValid() && gps.location.age() < 3000;
  float speed = (gps.speed.isValid() && fix) ? gps.speed.kmph() : DEMO_SPEED;
  double lat = fix ? gps.location.lat() : DEMO_LAT;
  double lng = fix ? gps.location.lng() : DEMO_LNG;

  float f[JS_N_FEATURES];
  js_extract(z, x, g, WIN, speed, f);
  int cls = js_classify(f);
  const char* label = JS_CLASSES[cls];
  Serial.printf("[%s] ptp=%.2fg jerk=%.0f width=%.2fs speed=%.0f fix=%d\n", label, f[3], f[4], f[5], speed, fix);

  if (strcmp(label, "pothole") != 0) return;   // bumps / rough / smooth are not reported as potholes

  digitalWrite(LED_PIN, HIGH);
  char body[520];
  snprintf(body, sizeof(body),
    "{\"device_id\":\"%s\",\"source\":\"fleet\",\"lat\":%.6f,\"lng\":%.6f,\"speed_kmh\":%.1f,"
    "\"label\":\"%s\",\"confidence\":0.8,\"features\":{\"z_std\":%.4f,\"z_max\":%.4f,\"z_min\":%.4f,"
    "\"z_ptp\":%.4f,\"jerk_max\":%.3f,\"peak_width_s\":%.3f,\"n_peaks\":%.0f,\"roll_std\":%.4f,"
    "\"x_std\":%.4f,\"speed_kmh\":%.2f,\"z_ptp_per_speed\":%.5f}}",
    DEVICE_ID, lat, lng, speed, label, f[0], f[1], f[2], f[3], f[4], f[5], f[6], f[7], f[8], f[9], f[10]);
  enqueue(String(body));
  delay(80);
  digitalWrite(LED_PIN, LOW);
}

// Desk demo: write a synthetic pothole into the buffer and evaluate it
void injectTestPothole() {
  for (int i = 0; i < WIN; i++) { bufZ[i] = (random(-30, 30)) / 1000.0f; bufX[i] = 0; bufG[i] = random(-10, 10) / 10.0f; }
  for (int k = 0; k < 3; k++) {
    bufZ[45 + k] -= 1.1f * sinf(PI * k / 3);
    bufZ[48 + k] += 1.1f * sinf(PI * k / 3);
    bufG[45 + k] += 25 * sinf(PI * k / 3);
  }
  for (int k = 0; k < 20; k++) bufZ[51 + k] += 0.33f * expf(-k / 6.0f) * sinf(k * 1.2f);
  head = 0; filled = WIN;
  evaluateWindow();
}

// ---------------------------------------------------------------- main
void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BTN_PIN, INPUT_PULLUP);
  Wire.begin(21, 22);
  Wire.setClock(400000);
  GPSSerial.begin(9600, SERIAL_8N1, 16, 17);
  mpuInit();
  wifiConnect();
  Serial.println("JalanSense node running");
}

void loop() {
  while (GPSSerial.available()) gps.encode(GPSSerial.read());

  if (digitalRead(BTN_PIN) == LOW && millis() - lastTrigger > 1500) {
    lastTrigger = millis();
    Serial.println("test pothole");
    injectTestPothole();
  }

  if (millis() - lastTick >= 20) {        // 50 Hz
    lastTick += 20;
    float ax, az, gx;
    if (mpuRead(ax, az, gx)) {
      gravityZ = gravityZ * 0.995f + az * 0.005f;
      float vz = az - gravityZ;
      bufZ[head] = vz; bufX[head] = ax; bufG[head] = gx;
      head = (head + 1) % WIN;
      if (filled < WIN) filled++;

      if (countdown < 0 && filled == WIN && fabsf(vz) > TRIGGER_G && millis() - lastTrigger > 2000) {
        countdown = POST_TRIGGER;
        lastTrigger = millis();
      }
      if (countdown >= 0 && --countdown < 0) evaluateWindow();
    }
  }

  static unsigned long lastNet = 0;
  if (millis() - lastNet > 10000) {        // reconnect + drain offline queue
    lastNet = millis();
    wifiConnect();
    flushQueue();
  }
}
