"""
MOCK survey responses for JalanSense, used ONLY to preview the survey dashboard
before real responses arrive. Every row is invented. Never report these numbers
as findings.

Output matches the Google Forms / Sheets CSV export format (same column titles
as create_form.gs), so the dashboard reads mock and real files the same way.

    python generate_mock.py            # -> ../web/data/survey_mock.csv (150 rows)
"""
import csv
import os
import random
from datetime import datetime, timedelta

random.seed(2026)
N = 150
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web", "data", "survey_sample.csv")

COLS = [
    "Timestamp", "Consent", "Township", "Area or precinct", "Your connection to the township",
    "Main way you travel inside the township", "Age group", "Overall road condition",
    "How often do you notice potholes or uneven road?", "Which problems have you seen?",
    "In the last 12 months, has a bad road caused you any of these?",
    "Roughly how much have you spent on vehicle repairs caused by bad roads in the last 12 months?",
    "Where is the worst spot you know?", "Have you ever reported a road problem?",
    "If you reported it, how long until it was repaired?",
    "Satisfaction with how road problems are handled", "Support for sensors on township vehicles",
    "Would you run a pothole-detecting app on your phone while driving?",
    "Any concerns about the phone app?", "Any other comments?",
]

TOWNSHIPS = [("City of Elmina", 55), ("Denai Alam", 12), ("Bandar Bukit Raja", 9), ("Bukit Jelutong", 6),
             ("Ara Damansara", 5), ("USJ Heights", 4), ("Subang Bestari", 4), ("Bandar Ainsworth", 2),
             ("Nilai Impian", 2), ("Other / Lain-lain", 1)]
# how worn the roads are per township (0 good .. 1 bad) -> drives answers
WEAR = {"City of Elmina": 0.62, "Denai Alam": 0.55, "Bandar Bukit Raja": 0.5, "Bukit Jelutong": 0.45,
        "Ara Damansara": 0.4, "USJ Heights": 0.35, "Subang Bestari": 0.45, "Bandar Ainsworth": 0.3,
        "Nilai Impian": 0.5, "Other / Lain-lain": 0.5}
AREAS = {"City of Elmina": ["Elmina East", "Elmina West", "near Central Park", "near the school", "near the mosque",
                            "near the commercial area", "", "", ""]}
CONN = [("Resident (owner)", 50), ("Resident (tenant)", 22), ("Work or study here", 16), ("Visitor / pass through", 12)]
MODE = [("Car", 62), ("Motorcycle", 18), ("Bicycle / e-scooter", 5), ("Walking", 6), ("Bus / shuttle", 6),
        ("Wheelchair / stroller", 3)]
AGE = [("18-24", 22), ("25-34", 30), ("35-44", 24), ("45-54", 14), ("55+", 10)]
FREQ = ["Daily", "Weekly", "Monthly", "Rarely", "Never"]
PROBLEMS = ["Potholes", "Uneven or badly patched surface", "Sunken drain or manhole covers", "Cracked surface",
            "Damaged speed bumps", "Faded road markings", "Waterlogging after rain"]
REPORTED = ["Yes, to the developer or estate management", "Yes, to the local council or MyJalan",
            "No, I did not know where to report", "No, I did not think it would be fixed", "No, never needed to"]
SPOTS = ["Roundabout near the school", "Junction near the mosque", "Main road towards the highway exit",
         "Road behind the shoplots", "Near the construction site entrance", "Bus stop near the park",
         "Slip road into the housing area", "Lorong belakang rumah teres", "Depan sekolah, waktu hujan teruk",
         "Near the guardhouse", "Exit to the toll", "Road beside the drain, after the bridge", "", "", "", "", ""]
COMMENTS = [
    "Lorries from the construction sites make it worse every month.",
    "Please fix before the rainy season, the holes fill with water and you can't see them.",
    "Jalan dah ok tapi bila hujan banyak lubang muncul.",
    "Motorcyclists are the most at risk, I almost fell last month.",
    "Patching is done but it comes back after a few weeks.",
    "Good idea, as long as my location data is not shared.",
    "Would be nice to see the status of reports in an app.",
    "Roads in my area are actually quite good.",
    "Sangat setuju, lubang jalan bahaya untuk anak-anak naik basikal.",
    "Speed bumps too high and damaged, not only potholes.",
    "Pushing a stroller on the uneven pedestrian crossing is hard.",
    "Hope this gets implemented!",
    "Dah report banyak kali tapi lambat dibaiki.",
    "Not sure the app would work well with my old phone.",
    "", "", "", "", "", "", "", "",
]


def pick(pairs):
    items, weights = zip(*pairs)
    return random.choices(items, weights=weights)[0]


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


rows = []
start = datetime(2026, 11, 2, 8, 0)
for i in range(N):
    town = pick(TOWNSHIPS)
    wear = clamp(WEAR[town] + random.gauss(0, 0.18), 0, 1)
    mode = pick(MODE)
    conn = pick(CONN)
    age = pick(AGE)
    area = random.choice(AREAS.get(town, ["", "", "near the main road"]))

    rating = int(clamp(round(5 - wear * 4 + random.gauss(0, 0.6)), 1, 5))
    fidx = int(clamp(round((1 - wear) * 4 + random.gauss(0, 0.7)), 0, 4))
    freq = FREQ[fidx]

    probs = [p for p in PROBLEMS if random.random() < (0.25 + wear * 0.6 if p in PROBLEMS[:3] else 0.15 + wear * 0.35)]
    if freq == "Never":
        probs = []

    impacts = []
    exposed = mode in ("Car", "Motorcycle", "Bicycle / e-scooter")
    if exposed and random.random() < 0.15 + wear * 0.35:
        impacts.append("Tyre or rim damage")
    if mode == "Car" and random.random() < wear * 0.25:
        impacts.append("Suspension or alignment problem")
    if random.random() < (0.45 if mode in ("Motorcycle", "Bicycle / e-scooter", "Wheelchair / stroller") else 0.12) * (0.4 + wear):
        impacts.append("Near-accident or fall")
    if random.random() < 0.2 + wear * 0.4:
        impacts.append("Had to swerve suddenly")
    if random.random() < 0.3 + wear * 0.4:
        impacts.append("Had to slow down a lot")
    if not impacts:
        impacts = ["None of these"]

    if "Tyre or rim damage" in impacts or "Suspension or alignment problem" in impacts:
        cost = random.choices(["Below RM 100", "RM 100 - 300", "RM 300 - 1,000", "Above RM 1,000"], [25, 40, 28, 7])[0]
    elif mode in ("Walking", "Bus / shuttle", "Wheelchair / stroller"):
        cost = random.choice(["RM 0", ""])
    else:
        cost = random.choices(["RM 0", "Not sure"], [80, 20])[0]

    rep = random.choices(REPORTED, [18, 8, 30, 24, 20] if wear > 0.35 else [8, 4, 15, 13, 60])[0]
    if rep.startswith("Yes"):
        fix = random.choices(["Less than 1 week", "1 - 4 weeks", "More than 1 month", "Never repaired"], [15, 38, 30, 17])[0]
    else:
        fix = "Did not report / not sure"
    sat = int(clamp(round(4 - wear * 2.5 + random.gauss(0, 0.8) - (0.6 if fix in ("More than 1 month", "Never repaired") else 0)), 1, 5))
    support = int(clamp(round(3.6 + wear * 1.2 + random.gauss(0, 0.8)), 1, 5))
    app = random.choices(["Yes", "Maybe", "No"], [45 + wear * 20, 35, 15 if mode == "Car" else 30])[0]
    conc = [c for c in ["Battery use", "Location privacy", "Mobile data use"] if random.random() < [0.35, 0.3, 0.2][["Battery use", "Location privacy", "Mobile data use"].index(c)]]
    if mode in ("Walking", "Bus / shuttle", "Wheelchair / stroller") and random.random() < 0.6:
        conc.append("I do not drive")
    if not conc:
        conc = ["No concerns"]

    ts = start + timedelta(minutes=random.randint(0, 6 * 24 * 60))
    rows.append([
        f"{ts.month}/{ts.day}/{ts.year} {ts.strftime('%H:%M:%S')}", "I agree / Saya setuju", town, area, conn, mode, age,
        rating, freq, ", ".join(probs), ", ".join(impacts), cost,
        random.choice(SPOTS) if wear > 0.3 else "", rep, fix, sat, support, app, ", ".join(conc), random.choice(COMMENTS),
    ])

rows.sort(key=lambda r: datetime.strptime(r[0], "%m/%d/%Y %H:%M:%S"))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(COLS)
    w.writerows(rows)
print(f"wrote {len(rows)} MOCK rows -> {os.path.normpath(OUT)}")
