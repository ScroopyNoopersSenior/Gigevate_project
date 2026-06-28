import argparse
from datetime import timedelta
from pathlib import Path

import pandas as pd

from artist_fee_recommendations import FeeScorer, currency
from availability_check import AvailabilityChecker
from genre_match import GenreScorer
from location_score import LocationScorer


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_ARTISTS_CSV = BASE_DIR / "cleaned-data" / "artists_combined.csv"
DEFAULT_EVENTS_CSV = BASE_DIR / "cleaned-data" / "events_combined.csv"
DEFAULT_BOOKINGS_CSV = BASE_DIR / "Gigevate-data (not cleaned)" / "gigevate-export" / "Bookings.csv"
DEFAULT_OUTPUT_DIR = BASE_DIR / "cleaned-data"


DEFAULT_WEIGHTS = {
    "genre": 0.40,
    "location": 0.35,
    "fee": 0.25,
    "availability": 0.00,
}


class RecommendationEngine:
    """Combines all artist filters into one ranked recommendation system."""

    def __init__(
        self,
        artists_path=DEFAULT_ARTISTS_CSV,
        events_path=DEFAULT_EVENTS_CSV,
        bookings_path=DEFAULT_BOOKINGS_CSV,
        location_scale_km=100,
        availability_buffer_hours=8,
        weights=None,
    ):
        self.artists = pd.read_csv(artists_path)
        self.events = pd.read_csv(events_path)
        self.weights = weights or DEFAULT_WEIGHTS

        self.genre_scorer = GenreScorer(artists_path, events_path)
        self.location_scorer = LocationScorer(scale_km=location_scale_km)
        self.availability_checker = AvailabilityChecker(
            events_path,
            bookings_path,
            buffer_hours=availability_buffer_hours,
        )

    def get_event(self, event_id):
        event_rows = self.events[self.events["EventId"] == event_id]
        if event_rows.empty:
            raise ValueError(f"No event found with EventId={event_id}")
        return event_rows.iloc[0]

    def recommend_for_event(
        self,
        event_id,
        budget,
        hours=1,
        budget_currency="EUR",
        top_n=10,
        require_available=True,
    ):
        """Returns artists ranked by final recommendation score."""
        event = self.get_event(event_id)
        fee_scorer = FeeScorer(
            budget=budget,
            budget_currency=budget_currency,
            hours=hours,
        )

        rows = []
        for _, artist in self.artists.iterrows():
            availability = self.availability_checker.score_artist_for_event(artist, event)

            if require_available and not availability["available"]:
                continue

            genre = self.genre_scorer.score_artist_for_event(artist, event)
            location = self.location_scorer.score_artist_for_event(artist, event)
            fee = fee_scorer.score_artist_for_event(artist, event)

            final_score = self.calculate_final_score(
                genre_score=genre["genre_score"],
                location_score=location["location_score"],
                fee_score=fee["fee_score"],
                availability_score=availability["availability_score"],
            )

            rows.append(
                {
                    "ArtistId": artist["ArtistId"],
                    "ArtistName": artist["ArtistName"],
                    "City": artist.get("City"),
                    "CurrentLocation": artist.get("CurrentLocation"),
                    "CountryName": artist.get("CountryName"),
                    "final_score": final_score,
                    **availability,
                    **genre,
                    **location,
                    **fee,
                    "MainGenres": artist.get("MainGenres"),
                    "SubGenres": artist.get("SubGenres"),
                    "AvgBookingFee": artist.get("AvgBookingFee"),
                    "NumberOfBookings": artist.get("NumberOfBookings"),
                }
            )

        recommendations = pd.DataFrame(rows)
        if recommendations.empty:
            return recommendations

        recommendations = recommendations.sort_values(
            [
                "final_score",
                "total_fee",
                "genre_score",
                "location_score",
                "fee_score",
                "NumberOfBookings",
            ],
            ascending=[False, True, False, False, False, False],
            na_position="last",
        ).reset_index(drop=True)

        recommendations.insert(0, "rank", recommendations.index + 1)
        return recommendations.head(top_n)

    def recommend_for_form(
        self,
        event_data,
        budget,
        hours=1,
        budget_currency="EUR",
        top_n=10,
        require_available=True,
        max_distance_km=None,
        min_score=0.0,
    ):
        """
        Returns ranked artists for event data submitted by a web form.

        The expected event_data keys mirror the cleaned event CSV columns used
        by the existing scorers: City, Country, MainGenres, DateTimeStart,
        DateTimeEnd, EventType and EventName.
        """
        event = self._event_from_form(event_data, hours=hours)
        fee_scorer = FeeScorer(
            budget=budget,
            budget_currency=budget_currency,
            hours=hours,
        )

        rows = []
        for _, artist in self.artists.iterrows():
            availability = self._score_availability_for_form_event(artist, event)

            if require_available and not availability["available"]:
                continue

            genre = self.genre_scorer.score_artist_for_event(artist, event)
            location = self.location_scorer.score_artist_for_event(artist, event)
            fee = fee_scorer.score_artist_for_event(artist, event)

            distance_km = location.get("distance_km")
            if max_distance_km is not None and pd.notna(distance_km) and distance_km > max_distance_km:
                continue

            final_score = self.calculate_final_score(
                genre_score=genre["genre_score"],
                location_score=location["location_score"],
                fee_score=fee["fee_score"],
                availability_score=availability["availability_score"],
            )

            if final_score < min_score:
                continue

            rows.append(
                {
                    "ArtistId": artist["ArtistId"],
                    "ArtistName": artist["ArtistName"],
                    "City": artist.get("City"),
                    "CurrentLocation": artist.get("CurrentLocation"),
                    "CountryName": artist.get("CountryName"),
                    "final_score": final_score,
                    **availability,
                    **genre,
                    **location,
                    **fee,
                    "MainGenres": artist.get("MainGenres"),
                    "SubGenres": artist.get("SubGenres"),
                    "AvgBookingFee": artist.get("AvgBookingFee"),
                    "NumberOfBookings": artist.get("NumberOfBookings"),
                    "CurrencyCode": artist.get("CurrencyCode"),
                    "SpotifyURL": artist.get("SpotifyURL"),
                }
            )

        recommendations = pd.DataFrame(rows)
        if recommendations.empty:
            return recommendations

        recommendations = recommendations.sort_values(
            [
                "final_score",
                "total_fee",
                "genre_score",
                "location_score",
                "fee_score",
                "NumberOfBookings",
            ],
            ascending=[False, True, False, False, False, False],
            na_position="last",
        ).reset_index(drop=True)

        recommendations.insert(0, "rank", recommendations.index + 1)
        return recommendations.head(top_n)

    def summarize_recommendations(self, recommendations, budget_min=None, budget_max=None):
        """Builds dashboard summary data for API consumers."""
        if recommendations.empty:
            return {
                "artists_found": 0,
                "within_budget": 0,
                "available": 0,
                "strong_matches": 0,
                "fee_distribution": [],
            }

        within_budget = 0
        if "budget_check" in recommendations:
            within_budget = int((recommendations["budget_check"] == "Ja").sum())

        available = 0
        if "available" in recommendations:
            available = int(recommendations["available"].sum())

        strong_matches = int((recommendations["final_score"] >= 0.8).sum())

        return {
            "artists_found": int(len(recommendations)),
            "within_budget": within_budget,
            "available": available,
            "strong_matches": strong_matches,
            "fee_distribution": self._fee_distribution(recommendations, budget_min, budget_max),
        }

    def calculate_final_score(self, genre_score, location_score, fee_score, availability_score):
        """Combines normalized filter scores using the configured weights."""
        final_score = (
            self.weights["genre"] * genre_score
            + self.weights["location"] * location_score
            + self.weights["fee"] * fee_score
            + self.weights["availability"] * availability_score
        )
        return round(final_score, 3)

    def _event_from_form(self, event_data, hours=1):
        start_time = event_data.get("DateTimeStart") or event_data.get("date_time_start")
        end_time = event_data.get("DateTimeEnd") or event_data.get("date_time_end")

        start_timestamp = pd.to_datetime(start_time, utc=True, errors="coerce")
        end_timestamp = pd.to_datetime(end_time, utc=True, errors="coerce")

        if pd.isna(end_timestamp) and pd.notna(start_timestamp):
            end_timestamp = start_timestamp + timedelta(hours=float(hours or 1))

        return pd.Series(
            {
                "EventId": event_data.get("EventId"),
                "EventName": event_data.get("EventName") or event_data.get("event_name") or "Nieuw event",
                "DateTimeStart": start_timestamp,
                "DateTimeEnd": end_timestamp,
                "City": event_data.get("City") or event_data.get("city"),
                "Country": event_data.get("Country") or event_data.get("country"),
                "StreetAddress": event_data.get("StreetAddress") or event_data.get("street_address"),
                "EventType": event_data.get("EventType") or event_data.get("event_type"),
                "MainGenres": event_data.get("MainGenres") or event_data.get("main_genres"),
            }
        )

    def _score_availability_for_form_event(self, artist, event):
        event_id = event.get("EventId")
        if pd.notna(event_id):
            return self.availability_checker.score_artist_for_event(artist, event)

        info = self.availability_checker.get_availability_info_time(
            artist["ArtistId"],
            event["DateTimeStart"],
            event["DateTimeEnd"],
        )

        return {
            "available": info["available"],
            "availability_score": info["availability_score"],
            "availability_reason": "available" if info["available"] else "booking conflict",
            "conflicts": info["conflicts"],
        }

    def _fee_distribution(self, recommendations, budget_min=None, budget_max=None):
        fees = pd.to_numeric(recommendations.get("total_fee"), errors="coerce").dropna()
        if fees.empty:
            return []

        lower = float(budget_min) if budget_min is not None else 0.0
        upper = float(budget_max) if budget_max is not None else max(float(fees.max()), lower + 1)
        step = max((upper - lower) / 4, 1)
        bins = [
            (0, lower if lower > 0 else step),
            (lower if lower > 0 else step, lower + step),
            (lower + step, lower + (step * 2)),
            (lower + (step * 2), upper),
            (upper, None),
        ]

        distribution = []
        for start, end in bins:
            if end is None:
                count = int((fees >= start).sum())
                label = f"{self._format_eur(start)}+"
            else:
                count = int(((fees >= start) & (fees < end)).sum())
                label = f"{self._format_eur(start)} - {self._format_eur(end)}"
            distribution.append({"label": label, "count": count})

        return distribution

    @staticmethod
    def _format_eur(value):
        return f"EUR {int(round(value)):,}".replace(",", ".")


def print_recommendations(recommendations):
    if recommendations.empty:
        print("No recommendations found.")
        return

    columns = [
        "rank",
        "ArtistName",
        "final_score",
        "available",
        "genre_score",
        "location_score",
        "distance_km",
        "fee_score",
        "total_fee",
        "budget_margin",
        "genre_reason",
        "location_reason",
        "fee_reason",
    ]
    visible_columns = [column for column in columns if column in recommendations.columns]
    print(recommendations[visible_columns].to_string(index=False))


def main():
    parser = argparse.ArgumentParser(description="Rank artists for one event using all filters.")
    parser.add_argument("--event-id", type=int, required=True)
    parser.add_argument("--budget", type=float, required=True)
    parser.add_argument("--hours", type=float, default=1)
    parser.add_argument("--currency", default="EUR")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--include-unavailable", action="store_true")
    parser.add_argument("--save-csv", action="store_true")
    parser.add_argument("--artists-csv", type=Path, default=DEFAULT_ARTISTS_CSV)
    parser.add_argument("--events-csv", type=Path, default=DEFAULT_EVENTS_CSV)
    parser.add_argument("--bookings-csv", type=Path, default=DEFAULT_BOOKINGS_CSV)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    engine = RecommendationEngine(
        artists_path=args.artists_csv,
        events_path=args.events_csv,
        bookings_path=args.bookings_csv,
    )

    recommendations = engine.recommend_for_event(
        event_id=args.event_id,
        budget=args.budget,
        hours=args.hours,
        budget_currency=currency(args.currency),
        top_n=args.top_n,
        require_available=not args.include_unavailable,
    )

    print_recommendations(recommendations)

    if args.save_csv:
        args.output_dir.mkdir(exist_ok=True)
        output_path = args.output_dir / f"recommendations_event_{args.event_id}.csv"
        recommendations.to_csv(output_path, index=False)
        print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()
