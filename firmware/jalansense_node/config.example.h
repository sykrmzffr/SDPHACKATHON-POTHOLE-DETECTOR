// Copy this file to config.h and fill in your values. config.h is git-ignored.
#pragma once

#define WIFI_SSID     "your-wifi-or-phone-hotspot"
#define WIFI_PASS     "password"
// Backend URL - for a demo, run the backend on a laptop on the same hotspot
// and use the laptop's IP, e.g. http://192.168.43.10:8000/api/events
#define API_URL       "http://192.168.43.10:8000/api/events"
#define DEVICE_ID     "shuttle-01"

// If there's no GPS fix (indoors demo), use this location instead (Elmina)
#define DEMO_LAT      3.19917
#define DEMO_LNG      101.50056
#define DEMO_SPEED    30.0
