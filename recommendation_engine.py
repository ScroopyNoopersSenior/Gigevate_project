import argparse
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
            ["final_score", "genre_score", "location_score", "fee_score", "NumberOfBookings"],
            ascending=[False, False, False, False, False],
        ).reset_index(drop=True)

        recommendations.insert(0, "rank", recommendations.index + 1)
        return recommendations.head(top_n)

    def calculate_final_score(self, genre_score, location_score, fee_score, availability_score):
        """Combines normalized filter scores using the configured weights."""
        final_score = (
            self.weights["genre"] * genre_score
            + self.weights["location"] * location_score
            + self.weights["fee"] * fee_score
            + self.weights["availability"] * availability_score
        )
        return round(final_score, 3)


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
