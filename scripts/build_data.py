#!/usr/bin/env python3
"""Build houbarsky-index/data.json from Open-Meteo — runs in the daily GitHub Actions cron.

Why this exists: the map used to fetch Open-Meteo directly from the browser. At the
~7.5 km hex grid that is 1473 points = 15 chunked requests, which trips Open-Meteo's
~600-calls/minute limit (HTTP 429) and left the map blank in production. Precomputing
here — paced under the limit — and committing a static data.json means the page makes
ZERO live API calls: instant load, no rate limit, and the hex size is no longer capped
by the API budget.

Output shape (consumed by index.html):
  {
    "generated": ISO8601,
    "past": 14, "fut": 7,
    "lon_step": 0.105, "lat_step": 0.0675,
    "points": [ {"lon":..,"lat":..,"prcp":[..],"tmax":[..],"tmin":[..],"soil":[..]}, ... ]
  }
Each per-point array has PAST+FUT (=21) daily entries; index PAST == "today".
Scoring stays in the client so day-switching needs no refetch.
"""
import json, math, sys, time, urllib.error, urllib.request
from datetime import datetime, timezone

# --- grid params: MUST match the hex geometry in index.html -----------------
LON_STEP, LAT_STEP = 0.105, 0.0675   # ~7.5 km cells
PAST, FUT = 14, 7
CHUNK = 100
# Pace under Open-Meteo's ~600 calls/min: at most 5 chunks (500 locations) per
# 65 s window. A cron does not care that this takes a few minutes.
CHUNKS_PER_WINDOW = 5
WINDOW_SLEEP = 65

# simplified CZ border (lon,lat) — identical polygon to the old client code
CZ = [[12.09,50.25],[12.55,50.40],[13.00,50.50],[13.55,50.72],[14.30,50.88],
[14.30,51.05],[15.00,51.00],[15.28,50.85],[16.00,50.62],[16.20,50.66],[16.45,50.60],
[16.90,50.44],[17.40,50.27],[17.70,50.32],[18.00,50.05],[18.60,49.90],[18.85,49.52],
[18.40,49.40],[18.15,49.10],[17.65,48.85],[17.20,48.87],[16.95,48.62],[16.60,48.78],
[16.10,48.75],[15.00,48.98],[14.70,48.58],[14.05,48.55],[13.50,48.77],[13.00,49.30],
[12.40,49.75],[12.09,50.25]]

def in_cz(lon, lat):
    inside = False
    j = len(CZ) - 1
    for i in range(len(CZ)):
        xi, yi = CZ[i]; xj, yj = CZ[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

def build_points():
    pts = []
    row = 0
    lat = 48.55
    while lat <= 51.06:
        off = (LON_STEP / 2) if row % 2 else 0
        lon = 12.05 + off
        while lon <= 18.9:
            if in_cz(lon, lat):
                pts.append({"lon": round(lon, 3), "lat": round(lat, 3)})
            lon += LON_STEP
        lat += LAT_STEP
        row += 1
    return pts

def fetch_chunk(chunk, attempt=0):
    url = ('https://api.open-meteo.com/v1/forecast?latitude='
           + ','.join(str(p["lat"]) for p in chunk)
           + '&longitude=' + ','.join(str(p["lon"]) for p in chunk)
           + '&daily=precipitation_sum,temperature_2m_max,temperature_2m_min'
           + '&hourly=soil_moisture_0_to_7cm'
           + f'&past_days={PAST}&forecast_days={FUT}&timezone=Europe%2FPrague')
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            body = r.read()
        data = json.loads(body)
        return data if isinstance(data, list) else [data]
    except urllib.error.HTTPError as e:
        if e.code == 429 and attempt < 6:
            print(f"  429 rate-limited, waiting {WINDOW_SLEEP}s then retrying (attempt {attempt+1})", flush=True)
            time.sleep(WINDOW_SLEEP)
            return fetch_chunk(chunk, attempt + 1)
        raise

def compact(loc):
    sm = loc.get("hourly", {}).get("soil_moisture_0_to_7cm") or []
    daily = loc["daily"]
    days = len(daily["time"])
    soil = []
    for d in range(days):
        s = n = 0
        for h in range(d * 24, min((d + 1) * 24, len(sm))):
            if sm[h] is not None:
                s += sm[h]; n += 1
        soil.append(round(s / n, 3) if n else None)
    r1 = lambda arr: [round(x, 1) if x is not None else None for x in arr]
    return {
        "prcp": r1(daily["precipitation_sum"]),
        "tmax": r1(daily["temperature_2m_max"]),
        "tmin": r1(daily["temperature_2m_min"]),
        "soil": soil,
    }

def main():
    pts = build_points()
    print(f"grid: {len(pts)} points, {math.ceil(len(pts)/CHUNK)} chunks", flush=True)
    out_points = []
    chunk_no = 0
    for i in range(0, len(pts), CHUNK):
        chunk = pts[i:i + CHUNK]
        if chunk_no and chunk_no % CHUNKS_PER_WINDOW == 0:
            print(f"  window full — sleeping {WINDOW_SLEEP}s to respect Open-Meteo minute limit", flush=True)
            time.sleep(WINDOW_SLEEP)
        t = time.time()
        locs = fetch_chunk(chunk)
        if len(locs) != len(chunk):
            raise SystemExit(f"chunk {chunk_no+1}: expected {len(chunk)} locations, got {len(locs)}")
        for p, loc in zip(chunk, locs):
            out_points.append({"lon": p["lon"], "lat": p["lat"], **compact(loc)})
        print(f"  chunk {chunk_no+1} ok ({len(chunk)} pts, {time.time()-t:.1f}s)", flush=True)
        chunk_no += 1

    doc = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "past": PAST, "fut": FUT,
        "lon_step": LON_STEP, "lat_step": LAT_STEP,
        "points": out_points,
    }
    with open("data.json", "w") as f:
        json.dump(doc, f, separators=(",", ":"))
    print(f"wrote data.json — {len(out_points)} points", flush=True)

if __name__ == "__main__":
    main()
