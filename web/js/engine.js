// JalanSense shared engine: features, edge model, severity, hotspot clustering,
// and a data store that talks to the backend API when it is available and
// falls back to the browser (localStorage) when hosted as a static site.
(function (global) {
  "use strict";

  const FEATURES = ["z_std", "z_max", "z_min", "z_ptp", "jerk_max", "peak_width_s",
    "n_peaks", "roll_std", "x_std", "speed_kmh", "z_ptp_per_speed"];
  const CLUSTER_RADIUS_M = 15;
  const VERIFY_DEVICES = 2;
  const ELMINA = [3.1992, 101.5006];

  // ---------------------------------------------------------------- features
  function std(a) {
    const m = a.reduce((s, x) => s + x, 0) / a.length;
    return Math.sqrt(a.reduce((s, x) => s + (x - m) * (x - m), 0) / a.length);
  }
  function extract(az, ax, gx, speed, fs) {
    fs = fs || 50;
    let jerk = 0, above = 0, cross = 0, prev = false;
    for (let i = 0; i < az.length; i++) {
      if (i > 0) jerk = Math.max(jerk, Math.abs(az[i] - az[i - 1]) * fs);
      const a = Math.abs(az[i]) > 0.3;
      if (a) above++;
      if (i > 0 && a && !prev) cross++;
      prev = a;
    }
    const zmax = Math.max(...az), zmin = Math.min(...az), ptp = zmax - zmin;
    return {
      z_std: std(az), z_max: zmax, z_min: zmin, z_ptp: ptp, jerk_max: jerk,
      peak_width_s: above / fs, n_peaks: cross, roll_std: std(gx), x_std: std(ax),
      speed_kmh: speed, z_ptp_per_speed: ptp / Math.max(speed, 5),
    };
  }

  // ---------------------------------------------------------------- model
  let MODEL = null;
  async function loadModel(url) {
    try { MODEL = await (await fetch(url || "js/model.json")).json(); } catch (e) { MODEL = null; }
    return MODEL;
  }
  function classify(f) {
    if (!MODEL) { // fallback rule if model.json failed to load
      if (f.z_ptp < 0.45) return "smooth";
      if (f.n_peaks >= 4) return "rough";
      if (f.peak_width_s > 0.25 && f.roll_std < 6) return "speed_bump";
      return "pothole";
    }
    const v = FEATURES.map(k => f[k]);
    let n = 0;
    while (MODEL.left[n] !== -1) n = v[MODEL.feature[n]] <= MODEL.threshold[n] ? MODEL.left[n] : MODEL.right[n];
    return MODEL.classes[MODEL.value[n]];
  }
  function severity(zptp, speed) {
    const s = zptp * Math.sqrt(40 / Math.max(speed, 10));
    return Math.min(5, Math.max(1, Math.round(s * 1.4)));
  }

  // ---------------------------------------------------------------- geo
  function dist(lat1, lng1, lat2, lng2) {
    const r = 6371000, t = Math.PI / 180;
    const dp = (lat2 - lat1) * t, dl = (lng2 - lng1) * t;
    const a = Math.sin(dp / 2) ** 2 + Math.cos(lat1 * t) * Math.cos(lat2 * t) * Math.sin(dl / 2) ** 2;
    return 2 * r * Math.asin(Math.sqrt(a));
  }

  function priority(h) {
    const avg = h.sev_sum / Math.max(h.hits, 1);
    const age = (Date.now() / 1000 - h.first_seen) / 86400;
    return +(avg * 2 + h.max_sev + Math.log2(1 + h.hits) + h.devices.length + Math.min(age, 14) * 0.2).toFixed(2);
  }
  function out(h) {
    return {
      id: h.id, lat: h.lat, lng: h.lng, label: h.label, hits: h.hits,
      unique_devices: h.devices.length, avg_severity: +(h.sev_sum / h.hits).toFixed(2),
      max_severity: h.max_sev, first_seen: h.first_seen, last_seen: h.last_seen,
      status: h.status, reopened: h.reopened, priority: priority(h),
    };
  }

  // ---------------------------------------------------------------- local store
  const KEY = "jalansense_store_v1";
  function load() {
    try { const s = JSON.parse(localStorage.getItem(KEY)); if (s && s.events) return s; } catch (e) { }
    return { events: [], hotspots: [], nextId: 1 };
  }
  let mem = null;
  function st() { if (!mem) mem = load(); return mem; }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(mem)); } catch (e) { } }

  const local = {
    mode: "local",
    async ingest(e) {
      const s = st();
      const ts = e.ts || Date.now() / 1000;
      const f = e.features || {};
      const sev = severity(f.z_ptp || 1, e.speed_kmh || 30);
      const ev = { id: s.events.length + 1, ts, device_id: e.device_id, source: e.source || "fleet",
        lat: e.lat, lng: e.lng, speed_kmh: e.speed_kmh || 30, label: e.label, severity: sev, hotspot_id: null };
      if (e.label === "pothole") {
        let best = null, bd = 1e9;
        for (const h of s.hotspots) {
          if (h.status === "dismissed") continue;
          const d = dist(e.lat, e.lng, h.lat, h.lng);
          if (d < bd) { bd = d; best = h; }
        }
        if (best && bd <= CLUSTER_RADIUS_M) {
          const n = best.hits + 1;
          best.lat = (best.lat * best.hits + e.lat) / n; best.lng = (best.lng * best.hits + e.lng) / n;
          best.hits = n; best.sev_sum += sev; best.max_sev = Math.max(best.max_sev, sev);
          best.last_seen = Math.max(best.last_seen, ts);
          if (!best.devices.includes(e.device_id)) best.devices.push(e.device_id);
          if (best.status === "repaired" && ts > best.status_changed) { best.status = "verified"; best.reopened++; }
          else if (best.status === "new" && best.devices.length >= VERIFY_DEVICES) best.status = "verified";
          ev.hotspot_id = best.id;
        } else {
          const h = { id: s.nextId++, lat: e.lat, lng: e.lng, label: "pothole", hits: 1, devices: [e.device_id],
            sev_sum: sev, max_sev: sev, first_seen: ts, last_seen: ts, status: "new", status_changed: ts, reopened: 0 };
          s.hotspots.push(h); ev.hotspot_id = h.id;
        }
      }
      s.events.push(ev);
      if (s.events.length > 5000) s.events.splice(0, s.events.length - 5000);
      save();
      return { event_id: ev.id, label: e.label, severity: sev, hotspot_id: ev.hotspot_id };
    },
    async hotspots() { return st().hotspots.map(out).sort((a, b) => b.priority - a.priority); },
    async events(label) { return st().events.filter(e => !label || e.label === label); },
    async setStatus(id, status, when) {
      const h = st().hotspots.find(h => h.id === id);
      if (h) { h.status = status; h.status_changed = when || Date.now() / 1000; save(); }
    },
    async stats() {
      const s = st(), by = {};
      s.hotspots.forEach(h => by[h.status] = (by[h.status] || 0) + 1);
      const fixed = s.hotspots.filter(h => h.status === "repaired");
      return {
        events: s.events.length, devices: new Set(s.events.map(e => e.device_id)).size, hotspots_by_status: by,
        open_hotspots: s.hotspots.filter(h => !["repaired", "dismissed"].includes(h.status)).length,
        avg_days_to_repair: fixed.length ? +(fixed.reduce((a, h) => a + (h.status_changed - h.first_seen), 0) / fixed.length / 86400).toFixed(1) : 0,
      };
    },
    async reset() { mem = { events: [], hotspots: [], nextId: 1 }; save(); },
    reload() { mem = null; },
  };

  // ---------------------------------------------------------------- API store
  function apiStore(base) {
    const j = (p, o) => fetch(base + p, o).then(r => r.json());
    const H = { "Content-Type": "application/json" };
    return {
      mode: "api",
      ingest: e => j("/api/events", { method: "POST", headers: H, body: JSON.stringify(e) }),
      hotspots: () => j("/api/hotspots"),
      events: label => j("/api/events" + (label ? "?label=" + label : "") + (label ? "&" : "?") + "limit=5000"),
      setStatus: (id, status, when) => j("/api/hotspots/" + id, { method: "PATCH", headers: H, body: JSON.stringify({ status, when }) }),
      stats: () => j("/api/stats"),
      reset: () => j("/api/reset", { method: "DELETE" }),
      reload() { },
    };
  }

  async function connect() {
    const qs = new URLSearchParams(location.search);
    const base = qs.get("api") || "";
    if (location.protocol.startsWith("http")) {
      try {
        const r = await fetch(base + "/api/health", { cache: "no-store" });
        if (r.ok && (await r.json()).ok) return apiStore(base);
      } catch (e) { }
    }
    return local;
  }

  // ---------------------------------------------------------------- demo data
  function rng(seed) { // mulberry32
    return function () {
      seed |= 0; seed = seed + 0x6D2B79F5 | 0;
      let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }

  // Approximate fallback road lines around Elmina, used only if OpenStreetMap
  // road data can't be fetched.
  const FALLBACK_ROADS = [
    [[3.1925, 101.4890], [3.1960, 101.4960], [3.1990, 101.5010], [3.2030, 101.5080], [3.2070, 101.5140]],
    [[3.2060, 101.4930], [3.2020, 101.4975], [3.1990, 101.5010], [3.1950, 101.5060], [3.1910, 101.5110]],
    [[3.1880, 101.4990], [3.1930, 101.5030], [3.1990, 101.5060], [3.2040, 101.5040]],
    [[3.1950, 101.4920], [3.2000, 101.4940], [3.2050, 101.4990], [3.2080, 101.5060]],
  ];

  async function fetchRoads() {
    // Bundled OpenStreetMap snapshot first, so the demo never depends on Overpass being up
    try {
      const b = await (await fetch("data/roads.json")).json();
      if (b && b.length > 20) return { roads: b, real: true };
    } catch (e) { }
    const cacheKey = "jalansense_roads_v1";
    try { const c = JSON.parse(localStorage.getItem(cacheKey)); if (c && c.length) return { roads: c, real: true }; } catch (e) { }
    const q = '[out:json][timeout:20];way["highway"~"^(primary|secondary|tertiary|residential|unclassified)$"](3.180,101.478,3.218,101.522);out geom;';
    try {
      const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), 12000);
      const r = await fetch("https://overpass-api.de/api/interpreter", { method: "POST", body: "data=" + encodeURIComponent(q), signal: ctl.signal });
      clearTimeout(t);
      const d = await r.json();
      const roads = d.elements.filter(w => w.geometry && w.geometry.length > 2)
        .map(w => ({ hw: w.tags.highway, name: w.tags.name || "", pts: w.geometry.map(g => [+g.lat.toFixed(6), +g.lon.toFixed(6)]) }));
      if (roads.length > 20) {
        try { localStorage.setItem(cacheKey, JSON.stringify(roads)); } catch (e) { }
        return { roads, real: true };
      }
    } catch (e) { }
    return { roads: FALLBACK_ROADS.map((p, i) => ({ hw: "secondary", name: "Road segment " + "ABCD"[i], pts: p })), real: false };
  }

  function pointOn(road, r) {
    const p = road.pts, i = Math.floor(r() * (p.length - 1)), f = r();
    return [p[i][0] + (p[i + 1][0] - p[i][0]) * f, p[i][1] + (p[i + 1][1] - p[i][1]) * f];
  }
  function jitter(pt, r, m) { // m metres
    return [pt[0] + (r() - 0.5) * m / 55000, pt[1] + (r() - 0.5) * m / 55000];
  }

  const FLEET = ["shuttle-01", "shuttle-02", "shuttle-03", "patrol-01", "patrol-02", "waste-01", "waste-02", "landscape-01"];

  // Build a month of plausible fleet detections on real roads.
  function demoEvents(roads, seed, nHot) {
    const r = rng(seed || 2026), now = Date.now() / 1000, evs = [];
    const weighted = roads.flatMap(rd => Array(rd.hw === "residential" ? 1 : 3).fill(rd));
    const plans = [];
    for (let k = 0; k < (nHot || 28); k++) {
      const c = pointOn(weighted[Math.floor(r() * weighted.length)], r);
      const depth = 0.35 + r() * 0.9;
      const hits = 1 + Math.floor(r() * r() * 9);
      const t0 = now - (2 + r() * 28) * 86400;
      const repaired = r() < 0.25;
      plans.push({ c, depth, hits, t0, repaired });
      for (let i = 0; i < hits; i++) {
        const speed = 15 + r() * 45, p = jitter(c, r, 8);
        const zptp = depth * (0.5 + speed / 40) * 2.1;
        evs.push({ device_id: FLEET[Math.floor(r() * FLEET.length)], source: "fleet",
          lat: p[0], lng: p[1], speed_kmh: +speed.toFixed(1), label: "pothole", confidence: 0.85,
          ts: Math.min(now - 3600 * (1 + r() * 20), t0 + i * (0.5 + r() * 2) * 86400 * (repaired ? 0.3 : 1)), features: { z_ptp: +zptp.toFixed(3) } });
      }
    }
    // a few speed bumps + rough patches the model correctly filtered out
    for (let k = 0; k < 40; k++) {
      const p = pointOn(weighted[Math.floor(r() * weighted.length)], r);
      evs.push({ device_id: FLEET[Math.floor(r() * FLEET.length)], source: "fleet", lat: p[0], lng: p[1],
        speed_kmh: 20, label: r() < 0.5 ? "speed_bump" : "rough", confidence: 0.9, ts: now - r() * 28 * 86400, features: { z_ptp: 0.8 } });
    }
    evs.sort((a, b) => a.ts - b.ts);
    return { evs, plans };
  }

  // Seeded road-condition index (0 good .. 1 poor) per road for the "scanned roads" layer
  function roadCondition(roads, seed) {
    const r = rng((seed || 7) + 11);
    return roads.map(rd => {
      const base = r();
      return Math.min(1, base * base * 1.3 + (rd.hw === "residential" ? 0.1 : 0));
    });
  }

  global.JalanSense = { FEATURES, ELMINA, extract, loadModel, classify, severity, dist, connect, local,
    fetchRoads, demoEvents, roadCondition, rng, FLEET };
})(window);
