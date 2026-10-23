"""
Synthetic IMU dataset generator for JalanSense.

Why synthetic? We don't have labelled drives in Elmina yet. This generator
models the physics well enough to (1) build and test the whole pipeline end
to end and (2) give the model a starting point. During the pilot, real drives
are labelled (driver taps a button / dashcam review) and the model is retrained
on real data with train.py --data real.csv.

Classes
    0 smooth      normal tarmac
    1 rough       worn / patched / gravel surface (sustained vibration)
    2 pothole     sharp drop then rebound, often one-sided (roll)
    3 speed_bump  wide, symmetric upward bump at low speed (must NOT be reported)

Usage:  python generate_data.py --n 4000 --out data/synthetic.csv
"""
import argparse
import os
import numpy as np
import pandas as pd

from features import FS, FEATURE_NAMES, extract

LABELS = ["smooth", "rough", "pothole", "speed_bump"]
WIN = 2 * FS          # 2 s window
WHEELBASE_M = 2.6


def half_sine(n, amp):
    if n < 2:
        n = 2
    return amp * np.sin(np.linspace(0, np.pi, n))


def damped(n, freq, amp, decay, start, total):
    t = np.arange(total - start) / FS
    out = np.zeros(total)
    out[start:] = amp * np.exp(-decay * t) * np.sin(2 * np.pi * freq * t)
    return out


def base_noise(rng, std):
    return rng.normal(0, std, WIN)


def make_window(cls, rng):
    az = base_noise(rng, rng.uniform(0.02, 0.05))
    ax = base_noise(rng, rng.uniform(0.01, 0.03))
    gx = base_noise(rng, rng.uniform(0.5, 1.5))

    if cls == 0:  # smooth
        speed = rng.uniform(20, 80)

    elif cls == 1:  # rough surface
        speed = rng.uniform(15, 60)
        std = rng.uniform(0.12, 0.30)
        # band-limited: smooth white noise with a short moving average
        k = rng.integers(2, 5)
        noise = np.convolve(rng.normal(0, std * 1.6, WIN + k), np.ones(k) / k, "valid")[:WIN]
        az += noise
        gx += np.convolve(rng.normal(0, 4, WIN + k), np.ones(k) / k, "valid")[:WIN]
        ax += noise * 0.3

    elif cls == 2:  # pothole
        speed = rng.uniform(15, 65)
        v = speed / 3.6
        depth = rng.uniform(0.3, 1.0)                  # relative severity
        amp = depth * (0.5 + speed / 40)               # deeper & faster -> harder hit
        dur = max(2, int(rng.uniform(0.04, 0.10) * FS))
        t0 = rng.integers(int(0.5 * FS), int(1.0 * FS))
        for hit, scale in ((t0, 1.0), (t0 + int(WHEELBASE_M / v * FS), rng.uniform(0.5, 0.9))):
            if hit + 2 * dur >= WIN:
                continue
            az[hit:hit + dur] -= half_sine(dur, amp * scale)
            az[hit + dur:hit + 2 * dur] += half_sine(dur, amp * scale * rng.uniform(0.8, 1.3))
            az += damped(WIN, rng.uniform(8, 12), amp * 0.3 * scale, 12, hit + 2 * dur, WIN)
            side = rng.choice([-1, 1]) if rng.random() < 0.8 else 0  # mostly one wheel
            gx[hit:hit + 2 * dur] += side * half_sine(2 * dur, rng.uniform(10, 40) * depth)
            ax[hit:hit + dur] -= half_sine(dur, amp * 0.25 * scale)

    else:  # speed bump
        speed = rng.uniform(8, 30)
        v = speed / 3.6
        width = rng.uniform(0.4, 1.2)                  # metres
        amp = rng.uniform(0.25, 0.8) * (0.6 + speed / 30)
        dur = max(4, int(width / v * FS))
        t0 = rng.integers(int(0.3 * FS), int(0.7 * FS))
        for hit, scale in ((t0, 1.0), (t0 + int(WHEELBASE_M / v * FS), rng.uniform(0.7, 1.0))):
            if hit + dur >= WIN:
                continue
            az[hit:hit + dur] += half_sine(dur, amp * scale)
            az += damped(WIN, rng.uniform(1.0, 1.8), amp * 0.4 * scale, 3, hit + dur, WIN)
            gx[hit:hit + dur] += rng.normal(0, 2, dur)   # symmetric -> little roll

    return az, ax, gx, speed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="data/synthetic.csv")
    a = ap.parse_args()

    rng = np.random.default_rng(a.seed)
    # realistic class balance: most windows are uneventful
    probs = [0.40, 0.25, 0.20, 0.15]
    rows = []
    for _ in range(a.n):
        cls = int(rng.choice(4, p=probs))
        az, ax, gx, speed = make_window(cls, rng)
        rows.append(list(extract(az, ax, gx, speed)) + [LABELS[cls]])

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    pd.DataFrame(rows, columns=FEATURE_NAMES + ["label"]).to_csv(a.out, index=False)
    print(f"wrote {len(rows)} windows -> {a.out}")


if __name__ == "__main__":
    main()
