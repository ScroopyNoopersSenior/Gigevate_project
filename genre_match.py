import argparse
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_ARTISTS_CSV = BASE_DIR / "cleaned-data" / "artists_combined.csv"
DEFAULT_EVENTS_CSV = BASE_DIR / "cleaned-data" / "events_combined.csv"
DEFAULT_OUTPUT_DIR = BASE_DIR / "cleaned-data"


def parse_genres(value):
    """Converts a comma-separated genre cell into normalized genre names."""
    if pd.isna(value):
        return []

    value = str(value).strip()
    if value in {"", "-"}:
        return []

    return [genre.strip().lower() for genre in value.split(",") if genre.strip()]


class GenreScorer:
    """Scores how well an artist's genres match an event's genres."""

    def __init__(self, artists_path=DEFAULT_ARTISTS_CSV, events_path=DEFAULT_EVENTS_CSV):
        self.artists = pd.read_csv(artists_path)
        self.events = pd.read_csv(events_path)

    def score_artist_for_event(self, artist, event):
        """
        Returns a score from 0.0 to 1.0.

        Event main genre in artist main genres -> 1.0
        Event main genre in artist sub genres -> 0.5
        No match or missing event genre -> 0.0
        """
        event_genres = parse_genres(event.get("MainGenres"))
        artist_main_genres = parse_genres(artist.get("MainGenres"))
        artist_sub_genres = parse_genres(artist.get("SubGenres"))

        if not event_genres:
            return {
                "genre_score": 0.0,
                "genre_reason": "event has no genre",
                "matched_genre": None,
            }

        best_score = 0.0
        matched_genre = None
        reason = "no genre match"

        for event_genre in event_genres:
            if event_genre in artist_main_genres:
                return {
                    "genre_score": 1.0,
                    "genre_reason": "main genre match",
                    "matched_genre": event_genre,
                }

            if event_genre in artist_sub_genres and best_score < 0.5:
                best_score = 0.5
                matched_genre = event_genre
                reason = "sub genre match"

        return {
            "genre_score": best_score,
            "genre_reason": reason,
            "matched_genre": matched_genre,
        }

    def get_event(self, event_id):
        event_rows = self.events[self.events["EventId"] == event_id]
        if event_rows.empty:
            raise ValueError(f"No event found with EventId={event_id}")
        return event_rows.iloc[0]

    def recommend_artists_for_event(self, event_id, top_n=10, min_score=0.0):
        """Ranks artists by genre score for one event."""
        event = self.get_event(event_id)
        results = []

        for _, artist in self.artists.iterrows():
            score_data = self.score_artist_for_event(artist, event)
            if score_data["genre_score"] >= min_score:
                results.append(
                    {
                        "ArtistId": artist["ArtistId"],
                        "ArtistName": artist["ArtistName"],
                        "City": artist.get("City"),
                        "MainGenres": artist.get("MainGenres"),
                        "SubGenres": artist.get("SubGenres"),
                        **score_data,
                    }
                )

        recommendations = pd.DataFrame(results)
        if recommendations.empty:
            return recommendations

        return (
            recommendations.sort_values(
                ["genre_score", "ArtistName"],
                ascending=[False, True],
            )
            .head(top_n)
            .reset_index(drop=True)
        )

    def search_event_by_name(self, search_term):
        """Returns events whose name contains the search term."""
        search_term = search_term.lower()
        event_names = self.events["EventName"].fillna("").str.lower()
        return self.events[event_names.str.contains(search_term, regex=False)]


def calculate_match_score(artist, event):
    """Backward-compatible helper for older code."""
    return GenreScorer.__new__(GenreScorer).score_artist_for_event(artist, event)["genre_score"]


def main():
    parser = argparse.ArgumentParser(description="Rank artists by genre match for one event.")
    parser.add_argument("--event-id", type=int, required=True)
    parser.add_argument("--top-n", type=int, default=15)
    parser.add_argument("--min-score", type=float, default=0.0)
    parser.add_argument("--artists-csv", type=Path, default=DEFAULT_ARTISTS_CSV)
    parser.add_argument("--events-csv", type=Path, default=DEFAULT_EVENTS_CSV)
    parser.add_argument("--save-csv", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    scorer = GenreScorer(args.artists_csv, args.events_csv)
    recommendations = scorer.recommend_artists_for_event(
        event_id=args.event_id,
        top_n=args.top_n,
        min_score=args.min_score,
    )

    if recommendations.empty:
        print("No matching artists found.")
        return

    print(recommendations.to_string(index=False))

    if args.save_csv:
        args.output_dir.mkdir(exist_ok=True)
        output_path = args.output_dir / f"genre_recommendations_event_{args.event_id}.csv"
        recommendations.to_csv(output_path, index=False)
        print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()
