import pandas as pd
import numpy as np
import re
from math import radians, sin, cos, sqrt, atan2
from pathlib import Path

# 1. Load data

BASE_DIR = Path(__file__).resolve().parent

artists = pd.read_csv(BASE_DIR / "cleaned-data" / "artists_combined.csv")
events = pd.read_csv(BASE_DIR / "cleaned-data" / "events_combined.csv")
worldcities = pd.read_csv(BASE_DIR / "worldcities.csv")

# 2. Text cleaning

INVALID_LOCATION_VALUES = {
    "",
    "-",
    ".",
    "tba",
    "unknown",
    "test",
    "asdf",
    "q",
    "past",
    "secret location",
    "new secret place",
    "n/a",
    "na",
    "none",
    "null"
}


COUNTRY_ALIASES = {
    "the netherlands": "netherlands",
    "netherland": "netherlands",
    "holland": "netherlands",
    "nl": "netherlands",

    "de": "germany",
    "deutschland": "germany",

    "uk": "united kingdom",
    "england": "united kingdom",
    "great britain": "united kingdom",

    "usa": "united states",
    "us": "united states",
    "u.s.": "united states",
    "u.s.a.": "united states",
    "united states of america": "united states",

    "portogallo": "portugal",
    "danmark": "denmark",
    "wien": "austria",
    "vienna": "austria",
    "italia": "italy",
    "tokyo": "japan",
    "calafornia": "united states"
}


CITY_ALIASES = {
    "amaterdam": "amsterdam",
    "amsterdam ": "amsterdam",
    "almere stad": "almere",

    "den haag": "the hague",
    "'s-gravenhage": "the hague",

    "gronigen": "groningen",
    "grongingen": "groningen",

    "joburg": "johannesburg",
    "jhb": "johannesburg",

    "wien": "vienna",
    "münchen": "munich",
    "munchen": "munich",

    "lisboa": "lisbon",
    "kraków": "krakow",
    "gdańsk": "gdansk",
    "warszawa": "warsaw",
    "köbenhavn v": "copenhagen",

    "miami, fl": "miami",
    "budapest, hungary": "budapest",
    "east lisbon": "lisbon",
    "istanbul province": "istanbul",
    "balearic islands": "ibiza",

    "düsseldorf": "dusseldorf",
    "borås": "boras",
    "almería": "almeria",
    "zürich": "zurich",
    "roma": "rome",

    # Regions mapped to representative cities
    "scotland": "glasgow",
    "gauteng": "johannesburg",
    "jersey": "saint helier",

    # Vague/non-city values
    "zuid": None,
    "usa": None,
    "poland": None,
    "south africa": None,
    "netherlands": None,
}


def clean_text(value):
    """
    Cleans text values so they can be compared reliably.
    """

    if pd.isna(value):
        return None

    value = str(value).strip().lower()

    # Remove double spaces
    value = re.sub(r"\s+", " ", value)

    if value in INVALID_LOCATION_VALUES:
        return None

    return value


def clean_country(value):
    """
    Cleans and normalizes country names.
    """

    value = clean_text(value)

    if value is None:
        return None

    return COUNTRY_ALIASES.get(value, value)


def clean_city(value):
    """
    Cleans city names and handles common spelling/format issues.
    """

    value = clean_text(value)

    if value is None:
        return None

    # If value contains a city and country, keep first part.
    # Example: "Nieuwegein, The Netherlands" -> "nieuwegein"
    if "," in value:
        value = value.split(",")[0].strip()

    # If value contains a slash, keep first part.
    # Example: "Maputo / Genova" -> "maputo"
    if "/" in value:
        value = value.split("/")[0].strip()

    if value in CITY_ALIASES:
        return CITY_ALIASES[value]

    return value


# 3. Prepare world city database

def prepare_worldcities(worldcities_df):
    """
    Standardizes the external world cities dataset.
    Supports common column names from datasets like SimpleMaps.
    """

    df = worldcities_df.copy()

    column_map = {}

    if "city_ascii" in df.columns:
        column_map["city_ascii"] = "city_name"
    elif "city" in df.columns:
        column_map["city"] = "city_name"
    else:
        raise ValueError("worldcities.csv must contain a 'city' or 'city_ascii' column.")

    if "country" in df.columns:
        column_map["country"] = "country_name"
    else:
        raise ValueError("worldcities.csv must contain a 'country' column.")

    if "lat" in df.columns:
        column_map["lat"] = "latitude"
    elif "latitude" in df.columns:
        column_map["latitude"] = "latitude"
    else:
        raise ValueError("worldcities.csv must contain a 'lat' or 'latitude' column.")

    if "lng" in df.columns:
        column_map["lng"] = "longitude"
    elif "lon" in df.columns:
        column_map["lon"] = "longitude"
    elif "longitude" in df.columns:
        column_map["longitude"] = "longitude"
    else:
        raise ValueError("worldcities.csv must contain a 'lng', 'lon' or 'longitude' column.")

    if "iso2" in df.columns:
        column_map["iso2"] = "country_code"
    elif "country_code" in df.columns:
        column_map["country_code"] = "country_code"

    if "population" in df.columns:
        column_map["population"] = "population"

    df = df.rename(columns=column_map)

    required_columns = ["city_name", "country_name", "latitude", "longitude"]
    df = df[required_columns + [col for col in ["country_code", "population"] if col in df.columns]]

    df["city_clean"] = df["city_name"].apply(clean_city)
    df["country_clean"] = df["country_name"].apply(clean_country)

    if "country_code" in df.columns:
        df["country_code_clean"] = df["country_code"].apply(clean_text)
    else:
        df["country_code_clean"] = None

    if "population" not in df.columns:
        df["population"] = 0

    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["population"] = pd.to_numeric(df["population"], errors="coerce").fillna(0)

    df = df.dropna(subset=["city_clean", "country_clean", "latitude", "longitude"])

    # If multiple places have the same city/country, keep the largest one.
    df = df.sort_values("population", ascending=False)
    df = df.drop_duplicates(subset=["city_clean", "country_clean"], keep="first")

    return df


worldcities_clean = prepare_worldcities(worldcities)


# Lookup by city + country
CITY_COUNTRY_LOOKUP = {
    (row["city_clean"], row["country_clean"]): {
        "lat": row["latitude"],
        "lng": row["longitude"],
        "matched_city": row["city_name"],
        "matched_country": row["country_name"],
        "population": row["population"]
    }
    for _, row in worldcities_clean.iterrows()
}


# Lookup by city + ISO2 country code, if available
CITY_CODE_LOOKUP = {}

if "country_code_clean" in worldcities_clean.columns:
    CITY_CODE_LOOKUP = {
        (row["city_clean"], row["country_code_clean"]): {
            "lat": row["latitude"],
            "lng": row["longitude"],
            "matched_city": row["city_name"],
            "matched_country": row["country_name"],
            "population": row["population"]
        }
        for _, row in worldcities_clean.iterrows()
        if row["country_code_clean"] is not None
    }


# Fallback lookup by city only.
# This is less reliable, so only use it when country is missing.
CITY_ONLY_LOOKUP = (
    worldcities_clean
    .sort_values("population", ascending=False)
    .drop_duplicates(subset=["city_clean"], keep="first")
    .set_index("city_clean")
    .to_dict("index")
)

COUNTRY_CENTER_LOOKUP = (
    worldcities_clean
    .sort_values("population", ascending=False)
    .drop_duplicates(subset=["country_clean"], keep="first")
    .set_index("country_clean")
    .to_dict("index")
)

# 4. Location matching

unmatched_locations = []


def get_coordinates(city, country=None, country_code=None, source="unknown"):
    """
    Converts city/country input into coordinates.

    Matching order:
    1. city + country
    2. city + country code
    3. city only, only if country is missing
    4. country fallback if city is missing or actually a country
    """

    city_clean = clean_city(city)
    country_clean = clean_country(country)
    country_code_clean = clean_text(country_code)

    # If the city field is actually a country name, use that as country fallback
    if city_clean is not None and city_clean in COUNTRY_CENTER_LOOKUP:
        row = COUNTRY_CENTER_LOOKUP[city_clean]

        return {
            "lat": row["latitude"],
            "lng": row["longitude"],
            "matched_city": row["city_name"],
            "matched_country": row["country_name"],
            "population": row["population"],
            "match_type": "country_fallback_from_city_field"
        }

    # If city is missing, try country fallback
    if city_clean is None:
        if country_clean is not None and country_clean in COUNTRY_CENTER_LOOKUP:
            row = COUNTRY_CENTER_LOOKUP[country_clean]

            return {
                "lat": row["latitude"],
                "lng": row["longitude"],
                "matched_city": row["city_name"],
                "matched_country": row["country_name"],
                "population": row["population"],
                "match_type": "country_fallback"
            }

        unmatched_locations.append({
            "source": source,
            "raw_city": city,
            "raw_country": country,
            "raw_country_code": country_code,
            "reason": "missing_or_invalid_city"
        })
        return None

    # Best match: city + country
    if country_clean is not None:
        key = (city_clean, country_clean)

        if key in CITY_COUNTRY_LOOKUP:
            result = CITY_COUNTRY_LOOKUP[key].copy()
            result["match_type"] = "city_country"
            return result

    # Second-best match: city + country code
    if country_code_clean is not None:
        key = (city_clean, country_code_clean)

        if key in CITY_CODE_LOOKUP:
            result = CITY_CODE_LOOKUP[key].copy()
            result["match_type"] = "city_country_code"
            return result

    # Fallback: city only, only when country is missing
    if country_clean is None and country_code_clean is None:
        if city_clean in CITY_ONLY_LOOKUP:
            row = CITY_ONLY_LOOKUP[city_clean]

            return {
                "lat": row["latitude"],
                "lng": row["longitude"],
                "matched_city": row["city_name"],
                "matched_country": row["country_name"],
                "population": row["population"],
                "match_type": "city_only"
            }

    # Last fallback: if city-country combination fails, but country exists,
    # use the country center instead of giving score 0.
    if country_clean is not None and country_clean in COUNTRY_CENTER_LOOKUP:
        row = COUNTRY_CENTER_LOOKUP[country_clean]

        return {
            "lat": row["latitude"],
            "lng": row["longitude"],
            "matched_city": row["city_name"],
            "matched_country": row["country_name"],
            "population": row["population"],
            "match_type": "country_fallback_after_failed_city_match"
        }

    unmatched_locations.append({
        "source": source,
        "raw_city": city,
        "raw_country": country,
        "raw_country_code": country_code,
        "clean_city": city_clean,
        "clean_country": country_clean,
        "clean_country_code": country_code_clean,
        "reason": "city_country_combination_not_found"
    })

    return None

# 5. Distance calculation

def haversine_distance(coord1, coord2):
    """
    Calculates the distance in kilometers between two latitude/longitude points.
    """

    lat1 = coord1["lat"]
    lon1 = coord1["lng"]
    lat2 = coord2["lat"]
    lon2 = coord2["lng"]

    earth_radius_km = 6371

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return earth_radius_km * c

# 6. Distance to score

def distance_to_score(distance_km, scale_km=100):
    """
    Converts distance to a score between 0 and 1.

    The closer the artist is to the event, the higher the score.

    Examples with scale_km=100:
    0 km   -> 1.00
    25 km  -> 0.80
    50 km  -> 0.67
    100 km -> 0.50
    250 km -> 0.29
    500 km -> 0.17
    """

    if distance_km is None:
        return 0.0

    return 1 / (1 + distance_km / scale_km)


def classify_distance(distance_km):
    """
    Returns a readable explanation category for the distance.
    """

    if distance_km is None:
        return "location could not be matched"

    if distance_km <= 10:
        return "same city or very close"
    elif distance_km <= 50:
        return "nearby city"
    elif distance_km <= 100:
        return "regional match"
    elif distance_km <= 250:
        return "same-country or nearby-country match"
    elif distance_km <= 500:
        return "medium distance"
    elif distance_km <= 1000:
        return "long distance"
    else:
        return "very long distance"

# 7. Main location score function

def location_score_for_artist_event(artist, event, scale_km=100):
    """
    Calculates location score for one artist and one event.

    Returns:
    - location_score
    - distance_km
    - location_reason
    - matched artist/event locations
    """

    # Prefer CurrentLocation, because an artist may currently live somewhere
    # different from their original profile city.
    artist_city = artist.get("CurrentLocation")

    if pd.isna(artist_city) or str(artist_city).strip() == "":
        artist_city = artist.get("City")

    artist_country = artist.get("CountryName")
    artist_country_code = artist.get("CountryCode")

    event_city = event.get("City")
    event_country = event.get("Country")

    artist_coord = get_coordinates(
        city=artist_city,
        country=artist_country,
        country_code=artist_country_code,
        source="artist"
    )

    event_coord = get_coordinates(
        city=event_city,
        country=event_country,
        country_code=None,
        source="event"
    )

    # Fallback: if artist city could not be matched using CurrentLocation,
    # try the original City column.
    if artist_coord is None and artist.get("City") != artist_city:
        artist_coord = get_coordinates(
            city=artist.get("City"),
            country=artist_country,
            country_code=artist_country_code,
            source="artist_fallback_city"
        )

    if artist_coord is None or event_coord is None:
        return {
            "location_score": 0.0,
            "distance_km": np.nan,
            "location_reason": "location could not be matched",
            "artist_matched_city": None,
            "artist_matched_country": None,
            "event_matched_city": None,
            "event_matched_country": None
        }

    distance_km = haversine_distance(artist_coord, event_coord)
    score = distance_to_score(distance_km, scale_km=scale_km)

    return {
        "location_score": round(score, 3),
        "distance_km": round(distance_km, 1),
        "location_reason": classify_distance(distance_km),
        "artist_matched_city": artist_coord["matched_city"],
        "artist_matched_country": artist_coord["matched_country"],
        "event_matched_city": event_coord["matched_city"],
        "event_matched_country": event_coord["matched_country"]
    }


class LocationScorer:
    """Scores how close an artist is to an event location."""

    def __init__(self, scale_km=100):
        self.scale_km = scale_km

    def score_artist_for_event(self, artist, event):
        """Returns location score and distance details for one artist/event pair."""
        return location_score_for_artist_event(
            artist=artist,
            event=event,
            scale_km=self.scale_km
        )

# 8. Rank artists for one event

def rank_artists_by_location(event_id, min_score=0.0, scale_km=100):
    """
    Ranks all artists by location fit for one event.

    Parameters:
    - event_id: the EventId from events_combined.csv
    - min_score: optional minimum location score
    - scale_km: controls how fast the score drops with distance

    Returns:
    - DataFrame with artists ranked by location_score
    """

    event_rows = events[events["EventId"] == event_id]

    if event_rows.empty:
        raise ValueError(f"No event found with EventId={event_id}")

    event = event_rows.iloc[0]

    results = artists.copy()

    location_results = results.apply(
        lambda artist: location_score_for_artist_event(
            artist=artist,
            event=event,
            scale_km=scale_km
        ),
        axis=1
    )

    location_results = pd.DataFrame(location_results.tolist())

    results = pd.concat(
        [results.reset_index(drop=True), location_results],
        axis=1
    )

    results = results[results["location_score"] >= min_score]

    results = results.sort_values(
        by=["location_score", "NumberOfBookings"],
        ascending=[False, False]
    )

    return results[
        [
            "ArtistId",
            "ArtistName",
            "City",
            "CurrentLocation",
            "CountryName",
            "CountryCode",
            "location_score",
            "distance_km",
            "location_reason",
            "artist_matched_city",
            "artist_matched_country",
            "event_matched_city",
            "event_matched_country",
            "NumberOfBookings"
        ]
    ]

# 9. Add location score to full artist-event pairs

def score_all_artists_for_all_events(max_events=None, scale_km=100):
    """
    Creates a full artist-event location score table.

    Warning:
    This can become large:
    number of events * number of artists
    """

    scored_rows = []

    selected_events = events.copy()

    if max_events is not None:
        selected_events = selected_events.head(max_events)

    for _, event in selected_events.iterrows():
        for _, artist in artists.iterrows():
            score_data = location_score_for_artist_event(
                artist=artist,
                event=event,
                scale_km=scale_km
            )

            scored_rows.append({
                "EventId": event["EventId"],
                "EventName": event["EventName"],
                "EventCity": event["City"],
                "EventCountry": event["Country"],
                "ArtistId": artist["ArtistId"],
                "ArtistName": artist["ArtistName"],
                "ArtistCity": artist["City"],
                "ArtistCurrentLocation": artist["CurrentLocation"],
                "ArtistCountry": artist["CountryName"],
                **score_data
            })

    return pd.DataFrame(scored_rows)

# 10. Save unmatched locations

def save_unmatched_locations(filename="unmatched_locations.csv"):
    """
    Saves all locations that could not be matched.
    Useful for data quality checks and client reporting.
    """

    if len(unmatched_locations) == 0:
        return pd.DataFrame(columns=[
            "source",
            "raw_city",
            "raw_country",
            "raw_country_code",
            "clean_city",
            "clean_country",
            "clean_country_code",
            "reason"
        ])

    df = pd.DataFrame(unmatched_locations)

    expected_columns = [
        "source",
        "raw_city",
        "raw_country",
        "raw_country_code",
        "clean_city",
        "clean_country",
        "clean_country_code",
        "reason"
    ]

    for col in expected_columns:
        if col not in df.columns:
            df[col] = None

    df = df[expected_columns]
    df = df.drop_duplicates()
    df.to_csv(filename, index=False)

    return df


if __name__ == "__main__":
    print("Artists:", artists.shape)
    print("Events:", events.shape)
    print("World cities:", worldcities.shape)

    test_event_id = events.iloc[0]["EventId"]

    print("\nTesting event:")
    print(events[events["EventId"] == test_event_id][["EventId", "EventName", "City", "Country"]])

    ranked = rank_artists_by_location(
        event_id=test_event_id,
        min_score=0.0,
        scale_km=100
    )

    print("\nTop 20 artists by location score:")
    print(ranked[[
        "ArtistName",
        "City",
        "CurrentLocation",
        "CountryName",
        "location_score",
        "distance_km",
        "location_reason"
    ]].head(20))

    unmatched = save_unmatched_locations()
    print("\nUnmatched locations:")
    print(unmatched.head(30))

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)

    unmatched = save_unmatched_locations()
    print("\nUnmatched locations full:")

    unmatched = save_unmatched_locations()

    if unmatched.empty:
        print("No unmatched locations found.")
    else:
        print(unmatched.head(50).to_string(index=False))
