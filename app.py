from datetime import date, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd
from meteostat import config, daily, hourly


ROOT = Path(__file__).parent
config.block_large_requests = False
STATIONS = {
    "16597": {"name": "Luqa, Malta", "country": "MT", "lat": 35.85, "lon": 14.50},
    "03772": {"name": "London Heathrow", "country": "GB", "lat": 51.48, "lon": -0.45},
    "72503": {"name": "New York Central Park", "country": "US", "lat": 40.78, "lon": -73.97},
    "02460": {"name": "Stockholm Arlanda, Sweden", "country": "SE", "lat": 59.65, "lon": 17.95},
    "02526": {"name": "Gothenburg, Sweden", "country": "SE", "lat": 57.72, "lon": 11.97},
    "02600": {"name": "Malmö, Sweden", "country": "SE", "lat": 55.57, "lon": 13.07},
    "02020": {"name": "Kiruna, Sweden", "country": "SE", "lat": 67.82, "lon": 20.34},
    "02411": {"name": "Uppsala, Sweden", "country": "SE", "lat": 59.90, "lon": 17.60},
    "01384": {"name": "Oslo Gardermoen, Norway", "country": "NO", "lat": 60.20, "lon": 11.08},
    "06180": {"name": "Copenhagen, Denmark", "country": "DK", "lat": 55.62, "lon": 12.65},
    "02974": {"name": "Helsinki, Finland", "country": "FI", "lat": 60.32, "lon": 24.96},
    "04030": {"name": "Reykjavik, Iceland", "country": "IS", "lat": 64.13, "lon": -21.90},
    "03969": {"name": "Dublin Airport, Ireland", "country": "IE", "lat": 53.43, "lon": -6.30},
    "06240": {"name": "Amsterdam Schiphol, Netherlands", "country": "NL", "lat": 52.31, "lon": 4.79},
    "06600": {"name": "Zurich, Switzerland", "country": "CH", "lat": 47.48, "lon": 8.57},
    "07149": {"name": "Paris Montsouris, France", "country": "FR", "lat": 48.82, "lon": 2.34},
    "10384": {"name": "Berlin Tempelhof, Germany", "country": "DE", "lat": 52.47, "lon": 13.40},
    "11034": {"name": "Vienna, Austria", "country": "AT", "lat": 48.11, "lon": 16.57},
    "16242": {"name": "Rome Ciampino, Italy", "country": "IT", "lat": 41.80, "lon": 12.59},
    "16716": {"name": "Athens, Greece", "country": "GR", "lat": 37.89, "lon": 23.73},
    "08221": {"name": "Madrid Barajas, Spain", "country": "ES", "lat": 40.45, "lon": -3.56},
    "08536": {"name": "Lisbon, Portugal", "country": "PT", "lat": 38.77, "lon": -9.13},
    "47662": {"name": "Tokyo, Japan", "country": "JP", "lat": 35.69, "lon": 139.75},
    "94767": {"name": "Sydney, Australia", "country": "AU", "lat": -33.95, "lon": 151.18},
    "71624": {"name": "Toronto, Canada", "country": "CA", "lat": 43.68, "lon": -79.63},
    "72530": {"name": "Chicago O'Hare, USA", "country": "US", "lat": 41.99, "lon": -87.90},
    "72295": {"name": "Los Angeles, USA", "country": "US", "lat": 33.94, "lon": -118.41},
    "41194": {"name": "Dubai, UAE", "country": "AE", "lat": 25.25, "lon": 55.36},
    "48698": {"name": "Singapore, Singapore", "country": "SG", "lat": 1.36, "lon": 103.99},
}


def demo_data(start: date, end: date):
    """Small deterministic fallback so the UI stays useful without network access."""
    points = []
    cursor = start
    while cursor <= end:
        day = cursor.timetuple().tm_yday
        temp = 18.2 + 7.8 * __import__("math").sin((day - 100) / 365 * 6.283)
        points.append({
            "date": cursor.isoformat(),
            "temp": round(temp, 1),
            "prcp": round(max(0, 2.8 + 3.6 * __import__("math").sin(day * 1.7)), 1),
            "wspd": round(18 + 5 * __import__("math").sin(day / 20), 1),
        })
        cursor += timedelta(days=1)
    return points


def get_weather(query):
    station_id = query.get("station", ["16597"])[0]
    start = date.fromisoformat(query.get("start", ["2020-01-01"])[0])
    end = date.fromisoformat(query.get("end", ["2020-12-31"])[0])
    granularity = query.get("granularity", ["daily"])[0]
    if end < start:
        raise ValueError("End date must be after start date")
    # Keep requests browser-friendly while allowing multi-decade comparisons.
    if (end - start).days > 3650 and granularity != "monthly":
        granularity = "monthly"
    fetcher = daily if granularity in ("daily", "monthly") else hourly
    frame = fetcher(station_id, start, end).fetch()
    if frame.empty:
        raise RuntimeError("Meteostat returned no observations for this range")
    if granularity == "monthly":
        # Climate means are averaged, while precipitation is accumulated.
        frame = frame.resample("ME").agg({"temp": "mean", "prcp": "sum", "wspd": "mean"})
    rows = []
    for timestamp, row in frame.iterrows():
        def numeric(name):
            value = row.get(name)
            return None if value is None or pd.isna(value) or not math.isfinite(float(value)) else round(float(value), 1)

        rows.append({
            "date": timestamp.strftime("%Y-%m-%d"),
            "temp": numeric("temp"),
            "prcp": numeric("prcp"),
            "wspd": numeric("wspd"),
        })
    return rows, False


def get_analysis(query):
    station_id = query.get("station", ["16597"])[0]
    start = date.fromisoformat(query.get("start", ["1980-01-01"])[0])
    end = date.fromisoformat(query.get("end", [date.today().isoformat()])[0])
    frame = daily(station_id, start, end).fetch()
    if frame.empty:
        raise RuntimeError("Meteostat returned no observations for this range")
    frame = frame.copy()
    frame["year"] = frame.index.year
    annual = frame.groupby("year").agg(
        avg_temp=("temp", "mean"),
        rainfall=("prcp", "sum"),
        avg_wind=("wspd", "mean"),
        warmest=("temp", "max"),
        coldest=("temp", "min"),
        wet_days=("prcp", lambda values: values.gt(0).sum()),
    )
    baseline = annual.avg_temp.mean()
    rows = []
    for year, row in annual.iterrows():
        def value(name, digits=1):
            item = row[name]
            return None if pd.isna(item) else round(float(item), digits)

        rows.append({
            "year": int(year),
            "avg_temp": value("avg_temp"),
            "rainfall": value("rainfall"),
            "avg_wind": value("avg_wind"),
            "warmest": value("warmest"),
            "coldest": value("coldest"),
            "wet_days": int(row["wet_days"]),
            "anomaly": round(value("avg_temp") - round(float(baseline), 1), 1) if not pd.isna(row["avg_temp"]) else None,
        })
    return rows


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/weather":
            try:
                rows, fallback = get_weather(parse_qs(parsed.query))
            except Exception as error:
                query = parse_qs(parsed.query)
                start = date.fromisoformat(query.get("start", ["2020-01-01"])[0])
                end = date.fromisoformat(query.get("end", ["2020-12-31"])[0])
                rows, fallback = demo_data(start, end), True
                print(f"Meteostat request failed; using demo data: {error}", flush=True)
            payload = {"station": STATIONS.get(parse_qs(parsed.query).get("station", ["16597"])[0], STATIONS["16597"]),
                       "data": rows, "fallback": fallback}
            body = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/stations":
            body = json.dumps(STATIONS).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/analysis":
            try:
                query = parse_qs(parsed.query)
                rows = get_analysis(query)
                station_id = query.get("station", ["16597"])[0]
                payload = {"station": STATIONS.get(station_id, STATIONS["16597"]), "data": rows}
                body = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as error:
                print(f"Analysis request failed: {error}", flush=True)
                self.send_error(502, "Unable to retrieve Meteostat analysis")
            return
        super().do_GET()


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 8000))

    print(f"Weather Atlas running on port {port}")

    ThreadingHTTPServer(
        ("0.0.0.0", port),
        Handler
    ).serve_forever()