import json
import math
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

from recommendation_engine import RecommendationEngine, currency


BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"

ENGINE = None


def get_engine():
    global ENGINE
    if ENGINE is None:
        ENGINE = RecommendationEngine()
    return ENGINE


def clean_value(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if pd.isna(value):
        return None
    return value


def to_float(value, default=None):
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_int(value, default=None):
    number = to_float(value, default)
    if number is None:
        return default
    return int(number)


def normalize_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "ja", "j", "on"}


def unique_values(series, limit=80):
    values = []
    seen = set()
    for raw_value in series.dropna():
        for part in str(raw_value).split(","):
            value = part.strip()
            key = value.lower()
            if value and value != "-" and key not in seen:
                values.append(value)
                seen.add(key)
    return sorted(values)[:limit]


def build_options():
    engine = get_engine()
    artists = engine.artists
    events = engine.events

    return {
        "genres": unique_values(pd.concat([artists["MainGenres"], artists["SubGenres"], events["MainGenres"]])),
        "cities": unique_values(pd.concat([artists["City"], artists["CurrentLocation"], events["City"]])),
        "eventTypes": unique_values(events["EventType"]),
    }


def build_event_data(payload):
    event_date = payload.get("eventDate") or payload.get("date")
    start_time = payload.get("startTime") or "22:00"
    end_time = payload.get("endTime")

    date_time_start = f"{event_date} {start_time}" if event_date else None
    date_time_end = f"{event_date} {end_time}" if event_date and end_time else None

    return {
        "EventName": payload.get("eventName") or "New event",
        "City": payload.get("city") or "Amsterdam",
        "Country": payload.get("country") or "Netherlands",
        "MainGenres": payload.get("genre") or payload.get("mainGenres") or "Techno",
        "EventType": payload.get("eventType") or "Club night",
        "DateTimeStart": date_time_start,
        "DateTimeEnd": date_time_end,
    }


def dataframe_to_records(df):
    if df.empty:
        return []

    records = []
    for record in df.to_dict(orient="records"):
        cleaned = {}
        for key, value in record.items():
            value = clean_value(value)
            if hasattr(value, "item"):
                value = value.item()
            cleaned[key] = value
        records.append(cleaned)
    return records


def recommendation_response(payload):
    engine = get_engine()
    budget_min = to_float(payload.get("budgetMin"), 500)
    budget_max = to_float(payload.get("budgetMax") or payload.get("budget"), 2500)
    hours = to_float(payload.get("hours"), 1)
    top_n = to_int(payload.get("topN"), 50)
    max_distance_km = to_float(payload.get("maxDistanceKm"), None)
    require_available = normalize_bool(payload.get("onlyAvailable"), True)
    only_within_budget = normalize_bool(payload.get("onlyWithinBudget"), False)

    recommendations = engine.recommend_for_form(
        event_data=build_event_data(payload),
        budget=budget_max,
        hours=hours,
        budget_currency=currency(payload.get("currency") or "EUR"),
        top_n=top_n,
        require_available=require_available,
        max_distance_km=max_distance_km,
        min_score=to_float(payload.get("minScore"), 0.0),
    )

    if only_within_budget and not recommendations.empty and "budget_check" in recommendations:
        recommendations = recommendations[recommendations["budget_check"] == "Ja"].reset_index(drop=True)
        recommendations["rank"] = recommendations.index + 1

    summary = engine.summarize_recommendations(
        recommendations,
        budget_min=budget_min,
        budget_max=budget_max,
    )

    return {
        "summary": summary,
        "recommendations": dataframe_to_records(recommendations),
        "event": build_event_data(payload),
        "filters": {
            "budgetMin": budget_min,
            "budgetMax": budget_max,
            "hours": hours,
            "maxDistanceKm": max_distance_km,
            "onlyAvailable": require_available,
            "onlyWithinBudget": only_within_budget,
        },
    }


class RecommendationHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self.send_json({"ok": True})
            return
        if parsed.path == "/api/options":
            self.send_json(build_options())
            return
        if parsed.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/recommendations":
            self.send_error(404, "Not found")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or "{}")
            self.send_json(recommendation_response(payload))
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=500)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


def main():
    server = None
    for port in range(8000, 8100):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), RecommendationHandler)
            break
        except OSError:
            continue

    if server is None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), RecommendationHandler)

    print(f"Recommendation dashboard running at http://127.0.0.1:{server.server_port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
