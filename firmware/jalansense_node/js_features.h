// Feature extraction - C port of ml/features.py. Keep the two in sync.
#pragma once
#include <math.h>

#define JS_FS 50.0f
#define JS_THRESH 0.3f

static float js_std(const float* a, int n) {
  float m = 0; for (int i = 0; i < n; i++) m += a[i]; m /= n;
  float v = 0; for (int i = 0; i < n; i++) v += (a[i] - m) * (a[i] - m);
  return sqrtf(v / n);
}

// out[11] order: z_std, z_max, z_min, z_ptp, jerk_max, peak_width_s,
//                n_peaks, roll_std, x_std, speed_kmh, z_ptp_per_speed
static void js_extract(const float* az, const float* ax, const float* gx, int n, float speed, float* out) {
  float zmax = az[0], zmin = az[0], jerk = 0; int above = 0, cross = 0; bool prev = false;
  for (int i = 0; i < n; i++) {
    if (az[i] > zmax) zmax = az[i];
    if (az[i] < zmin) zmin = az[i];
    if (i > 0) { float j = fabsf(az[i] - az[i - 1]) * JS_FS; if (j > jerk) jerk = j; }
    bool a = fabsf(az[i]) > JS_THRESH;
    if (a) above++;
    if (i > 0 && a && !prev) cross++;
    prev = a;
  }
  float ptp = zmax - zmin;
  out[0] = js_std(az, n); out[1] = zmax; out[2] = zmin; out[3] = ptp; out[4] = jerk;
  out[5] = above / JS_FS; out[6] = (float)cross; out[7] = js_std(gx, n); out[8] = js_std(ax, n);
  out[9] = speed; out[10] = ptp / (speed > 5 ? speed : 5);
}
