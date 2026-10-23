"""
JalanSense backend - ingests road events from IoT nodes / phones, clusters
them into hotspots, ranks repair priority and tracks work-order status.

Run:
    pip install -r requirements.txt
    uvicorn app:app --reload --port 8000
    open http://localhost:8000          (dashboard)
    open http://localhost:8000/docs     (API docs)
"""
import math
import os
import sqlite3
import time
from contextlib import closing
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB_PATH = os.environ.get("JS_DB", os.path.join(HERE, "jalansense.db"))

CLUSTER_RADIUS_M = 15       # events within 15 m are the same defect
VERIFY_DEVICES = 2          # confirmed once 2 different vehicles hit it
FEATURES = ["z_std", "z_max", "z_min", "z_ptp", "jerk_max", "peak_width_s", "n_peaks",
            "roll_std", "x_std", "speed_kmh", "z_ptp_per_speed"]

# Optional: cloud model re-checks events that carry the full feature vector
_cloud = None
try:
    import joblib
    _mp = os.path.join(ROOT, "ml", "models", "cloud_forest.joblib")
    if os.path.exists(_mp):
        _cloud = joblib.load(_mp)
except Exception:
    _cloud = None

app = FastAPI(title="JalanSense API", version="0.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ---------------------------------------------------------------- database
def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with closing(db()) as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY, ts REAL, device_id TEXT, source TEXT,
            lat REAL, lng REAL, speed_kmh REAL, label TEXT, confidence REAL,
            severity INTEGER, z_ptp REAL, hotspot_id INTEGER);
        CREATE TABLE IF NOT EXISTS hotspots(
            id INTEGER PRIMARY KEY, lat REAL, lng REAL, label TEXT,
            hits INTEGER, devices TEXT, sev_sum REAL, max_sev INTEGER,
            first_seen REAL, last_seen REAL, status TEXT,
            status_changed REAL, reopened INTEGER DEFAULT 0);
        """)
        con.commit()


init_db()


# ---------------------------------------------------------------- logic
def haversine_m(lat1, lng1, lat2, lng2):
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def severity(z_ptp: float, speed: float) -> int:
    """1 (minor) .. 5 (dangerous). Impact normalised by speed: the same jolt
    at 20 km/h means a deeper hole than at 60 km/h."""
    s = z_ptp * (40.0 / max(speed, 10.0)) ** 0.5
    return int(min(5, max(1, round(s * 1.4))))


def priority(h) -> float:
    avg = h["sev_sum"] / max(h["hits"], 1)
    n_dev = len([d for d in (h["devices"] or "").split(",") if d])
    age_days = (time.time() - h["first_seen"]) / 86400
    return round(avg * 2 + h["max_sev"] + math.log2(1 + h["hits"]) + n_dev + min(age_days, 14) * 0.2, 2)


def hotspot_out(h):
    devices = [d for d in (h["devices"] or "").split(",") if d]
    return {
        "id": h["id"], "lat": h["lat"], "lng": h["lng"], "label": h["label"],
        "hits": h["hits"], "unique_devices": len(devices),
        "avg_severity": round(h["sev_sum"] / max(h["hits"], 1), 2),
        "max_severity": h["max_sev"], "first_seen": h["first_seen"], "last_seen": h["last_seen"],
        "status": h["status"], "reopened": h["reopened"], "priority": priority(h),
    }


class Event(BaseModel):
    device_id: str
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    speed_kmh: float = 30
    label: str = "pothole"                 # edge model's guess
    confidence: float = 0.8
    ts: Optional[float] = None
    source: str = "fleet"                  # fleet | phone
    features: Optional[dict] = None        # full feature vector, if sent


class StatusUpdate(BaseModel):
    status: str                      # new | verified | work_order | repaired | dismissed
    when: Optional[float] = None     # unix time; defaults to now (used for back-filled demo data)


@app.get("/api/health")
def health():
    return {"ok": True, "cloud_model": _cloud is not None}


@app.post("/api/events")
def ingest(e: Event):
    label, conf = e.label, e.confidence
    f = e.features or {}
    if _cloud is not None and all(k in f for k in FEATURES):
        x = [[float(f[k]) for k in FEATURES]]
        probs = _cloud.predict_proba(x)[0]
        i = int(probs.argmax())
        label, conf = str(_cloud.classes_[i]), float(probs[i])

    ts = e.ts or time.time()
    z_ptp = float(f.get("z_ptp", 1.0))
    sev = severity(z_ptp, e.speed_kmh)

    with closing(db()) as con:
        cur = con.execute(
            "INSERT INTO events(ts,device_id,source,lat,lng,speed_kmh,label,confidence,severity,z_ptp)"
            " VALUES(?,?,?,?,?,?,?,?,?,?)",
            (ts, e.device_id, e.source, e.lat, e.lng, e.speed_kmh, label, conf, sev, z_ptp))
        ev_id = cur.lastrowid
        hs_id = None

        if label == "pothole":
            best, best_d = None, 1e9
            # cheap bounding box first (~0.0003 deg ~ 33 m)
            for h in con.execute("SELECT * FROM hotspots WHERE label='pothole' AND status!='dismissed' "
                                 "AND abs(lat-?)<0.0003 AND abs(lng-?)<0.0003", (e.lat, e.lng)):
                d = haversine_m(e.lat, e.lng, h["lat"], h["lng"])
                if d < best_d:
                    best, best_d = h, d
            if best is not None and best_d <= CLUSTER_RADIUS_M:
                devs = set(d for d in (best["devices"] or "").split(",") if d) | {e.device_id}
                n = best["hits"] + 1
                status, reopened = best["status"], best["reopened"]
                if status == "repaired" and ts > (best["status_changed"] or 0):
                    status, reopened = "verified", reopened + 1   # repair didn't hold
                elif status == "new" and len(devs) >= VERIFY_DEVICES:
                    status = "verified"
                con.execute(
                    "UPDATE hotspots SET lat=?,lng=?,hits=?,devices=?,sev_sum=?,max_sev=?,last_seen=?,status=?,reopened=? WHERE id=?",
                    ((best["lat"] * best["hits"] + e.lat) / n, (best["lng"] * best["hits"] + e.lng) / n, n,
                     ",".join(sorted(devs)), best["sev_sum"] + sev, max(best["max_sev"], sev), ts, status, reopened, best["id"]))
                hs_id = best["id"]
            else:
                cur = con.execute(
                    "INSERT INTO hotspots(lat,lng,label,hits,devices,sev_sum,max_sev,first_seen,last_seen,status,status_changed)"
                    " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (e.lat, e.lng, "pothole", 1, e.device_id, sev, sev, ts, ts, "new", ts))
                hs_id = cur.lastrowid
            con.execute("UPDATE events SET hotspot_id=? WHERE id=?", (hs_id, ev_id))
        con.commit()
    return {"event_id": ev_id, "label": label, "confidence": round(conf, 3), "severity": sev, "hotspot_id": hs_id}


@app.get("/api/hotspots")
def hotspots(status: Optional[str] = None, min_severity: int = 1):
    with closing(db()) as con:
        rows = [hotspot_out(h) for h in con.execute("SELECT * FROM hotspots")]
    rows = [r for r in rows if r["max_severity"] >= min_severity and (status is None or r["status"] == status)]
    return sorted(rows, key=lambda r: -r["priority"])


@app.patch("/api/hotspots/{hid}")
def update_status(hid: int, u: StatusUpdate):
    if u.status not in {"new", "verified", "work_order", "repaired", "dismissed"}:
        raise HTTPException(400, "bad status")
    with closing(db()) as con:
        cur = con.execute("UPDATE hotspots SET status=?, status_changed=? WHERE id=?", (u.status, u.when or time.time(), hid))
        con.commit()
        if cur.rowcount == 0:
            raise HTTPException(404, "not found")
    return {"id": hid, "status": u.status}


@app.get("/api/events")
def events(label: Optional[str] = None, limit: int = 500):
    q, args = "SELECT * FROM events", []
    if label:
        q += " WHERE label=?"
        args.append(label)
    q += " ORDER BY ts DESC LIMIT ?"
    args.append(limit)
    with closing(db()) as con:
        return [dict(r) for r in con.execute(q, args)]


@app.get("/api/stats")
def stats():
    with closing(db()) as con:
        ev = con.execute("SELECT COUNT(*) n, COUNT(DISTINCT device_id) d FROM events").fetchone()
        by = {r["status"]: r["n"] for r in con.execute("SELECT status, COUNT(*) n FROM hotspots GROUP BY status")}
        fixed = con.execute("SELECT AVG(status_changed-first_seen) t FROM hotspots WHERE status='repaired'").fetchone()
    return {
        "events": ev["n"], "devices": ev["d"], "hotspots_by_status": by,
        "open_hotspots": sum(v for k, v in by.items() if k not in ("repaired", "dismissed")),
        "avg_days_to_repair": round((fixed["t"] or 0) / 86400, 1),
    }


@app.delete("/api/reset")
def reset():
    with closing(db()) as con:
        con.executescript("DELETE FROM events; DELETE FROM hotspots;")
        con.commit()
    return {"ok": True}


# Serve the dashboard from the same origin
_web = os.path.join(ROOT, "web")
if os.path.isdir(_web):
    app.mount("/", StaticFiles(directory=_web, html=True), name="web")
