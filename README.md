# JalanSense: Fleet-Powered Pothole Detection for the Township of Tomorrow

**Sime Darby Property University Hackathon 2026, People track** (Safety & Security · Getting Around)

JalanSense turns the vehicles a township already runs into road inspectors: shuttles, security patrols, waste trucks and landscaping vans. Each vehicle carries a low-cost IoT node, or a phone. The node feels every jolt and uses on-device machine learning to decide whether it was a **pothole**, a **speed bump** or just a **rough surface**. It then sends real potholes, with GPS location and severity, to an estate-operations dashboard. The dashboard turns repeated hits into verified hotspots, ranks them by repair priority, and tracks each one from detection through work order to repair.

## Why

- Uneven, rough and potholed roads are a common complaint in growing townships like City of Elmina. Construction traffic and heavy rain wear roads down quickly.
- Today, defects are found when a resident complains or during a periodic manual inspection. Both are slow, patchy and reactive.
- Nationally, the MyJalan app received **40,938** road complaints between its launch in Aug 2023 and Aug 2025. Of the 12,459 road-damage complaints handled by the Works Ministry, **11,860 were resolved**. **69.6%** of complaints had to be redirected to other agencies such as local councils and private road owners ([Malay Mail, 20 Aug 2025](https://www.malaymail.com/news/malaysia/2025/08/20/myjalan-app-proves-successful-as-11860-road-damage-complaints-resolved-says-works-minister/188277)). Township roads need their own early-warning loop.

## How it works

```
 Fleet vehicle                    Cloud                          Estate team
┌──────────────────┐   pothole   ┌────────────────────────┐   ┌───────────────────────┐
│ ESP32 + MPU6050  │──event────▶│ FastAPI ingest          │──▶│ Dashboard: map,        │
│ + GPS  (or phone)│  lat/lng,   │ cloud ML re-check       │   │ priority queue,        │
│ 50 Hz IMU        │  severity,  │ 15 m clustering         │   │ work orders, repair    │
│ edge ML (tree)   │  features   │ verify ≥2 vehicles      │   │ verification           │
└──────────────────┘             │ priority score          │   └───────────────────────┘
   speed bumps & rough           │ re-open if hit again    │
   roads filtered on-device      └────────────────────────┘
```

1. **Sense:** the IMU is sampled at 50 Hz. A vertical jolt above 0.35 g opens a 2-second window.
2. **Classify at the edge:** 11 features (peak-to-peak, jerk, peak width, roll, speed-normalised impact and others) go into a small decision tree. Speed bumps and rough patches are dropped on the device.
3. **Cluster and verify:** pothole events within 15 m merge into one hotspot. A hotspot becomes *verified* once two or more different vehicles hit it, which cuts false alarms.
4. **Prioritise:** the score combines severity, number of hits, number of vehicles and age of the defect.
5. **Close the loop:** the estate team raises a work order and marks the defect repaired. If fleet vehicles hit the same spot again, the hotspot **re-opens automatically**, which shows that the repair did not hold. This gives evidence for contractor warranty claims.

## Repo layout

| Folder | What | Owner |
|---|---|---|
| `firmware/jalansense_node/` | ESP32 sketch, feature extraction (C), exported edge model | Syakir |
| `ml/` | Synthetic data generator, feature extraction, training, model export | Zeeq |
| `backend/` | FastAPI and SQLite: ingest, clustering, priority, work-order status | Zeeq |
| `web/` | Estate dashboard (`index.html`) and phone drive mode (`drive.html`) | Zeeq |
| `docs/` | Submission text, video script, survey, pilot plan | Faris |
| `survey/` | Google Form builder script (`create_form.gs`) and MOCK response generator | Faris |

## Run it

**Dashboard only, no install.** Open `web/index.html` through any static server, or enable GitHub Pages on the `/web` folder. This runs in demo mode with data stored in the browser.

```bash
cd web && python3 -m http.server 8080      # http://localhost:8080
```

**Full stack** (API, dashboard, cloud model):

```bash
cd ml && pip install -r requirements.txt && python generate_data.py && python train.py
cd ../backend && pip install -r requirements.txt && uvicorn app:app --host 0.0.0.0 --port 8000
# http://localhost:8000          dashboard (shows "LIVE API")
# http://localhost:8000/docs     API docs
# http://<laptop-ip>:8000/drive.html on a phone on the same Wi-Fi
```

Note that phone motion sensors require **HTTPS** on most browsers. GitHub Pages provides that, so use the Pages link for phone demos.

**Firmware:** copy `config.example.h` to `config.h`, fill in Wi-Fi and API URL, install *TinyGPSPlus*, select board *ESP32 Dev Module* and upload. Press **BOOT** to send a test pothole.

## Model results (synthetic data, to be re-trained on pilot drives)

| Model | Accuracy | Pothole precision | Pothole recall | Speed-bump recall |
|---|---|---|---|---|
| Edge decision tree (depth 6, runs on ESP32) | 97.4% | 93.4% | 95.4% | 94.7% |
| Cloud random forest | 99.3% | 98.5% | 97.9% | 100% |

These numbers come from **physics-based synthetic data** (`ml/generate_data.py`). Real roads are noisier. The pilot plan collects labelled drives so the model can be retrained with `python train.py --data real.csv`.

## Bill of materials (per vehicle node)

| Part | Approx. price (MY) |
|---|---|
| ESP32 DevKit | RM 20–30 |
| MPU6050 IMU | RM 8–12 |
| NEO-6M GPS | RM 25–40 |
| Enclosure, 12V→5V USB car adapter, mounting | RM 15–25 |
| **Total** | **≈ RM 70–110 per vehicle** |

A production node would add a 4G/LTE-M module, or use the vehicle's existing telematics, instead of Wi-Fi with store-and-forward.

## Resident survey

- `survey/create_form.gs`: paste into script.google.com and run `createSurvey`. It creates the Google Form and its response sheet in your Drive and logs the share link.
- `web/survey.html`: survey insights dashboard. It opens with **mock** data (`web/data/survey_sample.csv`, 150 invented responses, clearly bannered). Use **Load Google Forms CSV** to view real responses (Sheets → File → Download → CSV).
- Never quote the mock numbers as findings.
