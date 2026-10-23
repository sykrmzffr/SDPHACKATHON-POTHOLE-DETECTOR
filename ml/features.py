"""
Feature extraction for JalanSense road-event windows.

A "window" is ~2 seconds of IMU data sampled at 50 Hz around a trigger,
plus the vehicle speed at that moment. The SAME features are computed on
the ESP32 (firmware/jalansense_node/js_features.h) and in the phone drive mode
(web/js/engine.js), so a model trained here can run on any of them.

Inputs per window:
    az    : vertical acceleration in g (gravity removed -> ~0 on smooth road)
    ax    : longitudinal acceleration in g
    gx    : roll rate in deg/s (one wheel dropping into a pothole -> roll)
    speed : km/h from GPS
"""
import numpy as np

FS = 50  # Hz
FEATURE_NAMES = [
    "z_std",          # overall vibration energy
    "z_max",          # biggest upward jolt
    "z_min",          # biggest downward drop (pothole = wheel falls)
    "z_ptp",          # peak-to-peak
    "jerk_max",       # sharpest change in az (g/s) -> potholes are sharp
    "peak_width_s",   # time |az| stays above 0.3 g -> bumps are wide
    "n_peaks",        # count of |az| > 0.3 g crossings -> rough road = many
    "roll_std",       # roll-rate variation -> one-sided hit
    "x_std",          # longitudinal shake
    "speed_kmh",
    "z_ptp_per_speed" # normalise impact by speed
]

THRESH = 0.3


def extract(az, ax, gx, speed):
    az = np.asarray(az, dtype=float)
    ax = np.asarray(ax, dtype=float)
    gx = np.asarray(gx, dtype=float)
    jerk = np.abs(np.diff(az)) * FS
    above = np.abs(az) > THRESH
    crossings = int(np.sum(above[1:] & ~above[:-1]))
    z_ptp = float(az.max() - az.min())
    return np.array([
        float(az.std()),
        float(az.max()),
        float(az.min()),
        z_ptp,
        float(jerk.max()) if jerk.size else 0.0,
        float(above.sum()) / FS,
        float(crossings),
        float(gx.std()),
        float(ax.std()),
        float(speed),
        z_ptp / max(float(speed), 5.0),
    ])
