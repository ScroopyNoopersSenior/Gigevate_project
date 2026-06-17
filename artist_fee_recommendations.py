import argparse
from pathlib import Path

import pandas as pd


DEFAULT_ARTISTS_CSV = Path("cleaned-data/artists_combined.csv")
DEFAULT_VENUES_CSV = Path("cleaned-data/most_important_venuedata.csv")
DEFAULT_OUTPUT_DIR = Path("cleaned-data")


class FeeRecommender:
    """Reusable fee/budget recommender for artists, venues, or similar items."""

    def __init__(self, top_n=10):
        self.top_n = top_n

    def recommend(self, items, budget, budget_currency="EUR", hours=1):
        checked = items.copy()
        is_artist_list = checked["type"].eq("artist").all()

        checked["hours"] = hours if is_artist_list else pd.NA
        checked["total_fee"] = checked["fee"] * hours if is_artist_list else checked["fee"]
        checked["budget"] = budget
        checked["budget_currency"] = budget_currency
        checked["margin"] = budget - checked["total_fee"]
        checked["amount_outside_budget"] = checked["margin"].where(checked["margin"] < 0, 0).abs()

        checked["budget_check"] = "Onbekend"
        checked["reason"] = "fee ontbreekt"
        checked.loc[checked["fee"].notna() & checked["currency"].isna(), "reason"] = "valuta ontbreekt"
        checked.loc[
            checked["fee"].notna() & checked["currency"].notna() & (checked["currency"] != budget_currency),
            "reason",
        ] = "valuta mismatch"

        comparable = checked["total_fee"].notna() & (checked["currency"] == budget_currency)
        checked.loc[comparable & (checked["total_fee"] <= budget), "budget_check"] = "Ja"
        checked.loc[comparable & (checked["total_fee"] > budget), "budget_check"] = "Nee"
        checked.loc[checked["budget_check"] == "Ja", "reason"] = "binnen budget"
        checked.loc[checked["budget_check"] == "Nee", "reason"] = "buiten budget"

        top = checked[checked["budget_check"] == "Ja"].sort_values(
            ["amount_outside_budget", "margin", "total_fee"], ascending=[True, True, False]
        )
        rest = checked.drop(top.index).sort_values(
            ["budget_check", "amount_outside_budget", "name"], ascending=[True, True, True], na_position="last"
        )

        output = pd.concat([top, rest], ignore_index=True)
        output["rank"] = output.index + 1
        output["in_top_10"] = output.index < min(self.top_n, len(top))
        return output


class FeeScorer:
    """Scores whether an artist fits inside a requested budget."""

    def __init__(self, budget, budget_currency="EUR", hours=1):
        self.budget = budget
        self.budget_currency = currency(budget_currency)
        self.hours = hours

    def score_artist_for_event(self, artist, event=None):
        """
        Returns a fee score from 0.0 to 1.0.

        Missing fee receives a small fallback score so artists are not silently
        removed because of incomplete data.
        """
        fee = self._artist_fee(artist)
        artist_currency = self._artist_currency(artist)

        if self.budget is None or self.budget <= 0:
            return {
                "fee_score": 0.0,
                "fee_reason": "invalid budget",
                "total_fee": pd.NA,
                "budget_margin": pd.NA,
                "budget_check": "Onbekend",
            }

        if pd.isna(fee):
            return {
                "fee_score": 0.3,
                "fee_reason": "fee unknown",
                "total_fee": pd.NA,
                "budget_margin": pd.NA,
                "budget_check": "Onbekend",
            }

        if pd.isna(artist_currency):
            return {
                "fee_score": 0.2,
                "fee_reason": "currency unknown",
                "total_fee": fee * self.hours,
                "budget_margin": pd.NA,
                "budget_check": "Onbekend",
            }

        if artist_currency != self.budget_currency:
            return {
                "fee_score": 0.0,
                "fee_reason": "currency mismatch",
                "total_fee": fee * self.hours,
                "budget_margin": pd.NA,
                "budget_check": "Onbekend",
            }

        total_fee = fee * self.hours
        margin = self.budget - total_fee

        if total_fee <= self.budget:
            score = 1.0
            reason = "within budget"
            budget_check = "Ja"
        else:
            score = max(0.0, 1.0 - ((total_fee - self.budget) / self.budget))
            reason = "outside budget"
            budget_check = "Nee"

        return {
            "fee_score": round(score, 3),
            "fee_reason": reason,
            "total_fee": round(total_fee, 2),
            "budget_margin": round(margin, 2),
            "budget_check": budget_check,
        }

    def _artist_fee(self, artist):
        for column in ["AvgBookingFee", "HourlyFeeRange", "artist_fee", "fee"]:
            if column in artist and pd.notna(artist.get(column)):
                return pd.to_numeric(artist.get(column), errors="coerce")
        return pd.NA

    def _artist_currency(self, artist):
        for column in ["CurrencyCode", "currency_code", "CurrencySymbol", "currency_symbol"]:
            if column in artist and pd.notna(artist.get(column)):
                return currency(artist.get(column))
        return pd.NA


def first_existing(df, names):
    return next((name for name in names if name in df.columns), None)


def clean(value):
    if pd.isna(value):
        return pd.NA
    value = str(value).strip()
    return pd.NA if value in {"", "-"} else value


def currency(value):
    value = clean(value)
    if pd.isna(value):
        return pd.NA
    return {"€": "EUR", "$": "USD", "£": "GBP"}.get(str(value).upper(), str(value).upper())


def load_items(path, kind, id_col=None, name_col=None, fee_col=None, currency_col=None):
    df = pd.read_csv(path)
    id_col = id_col or first_existing(df, ["ArtistId", "artist_id", "organizer_id", "venue_id", "Id"])
    name_col = name_col or first_existing(
        df,
        ["ArtistName", "artist_name", "StageName", "business_name", "venue_name", "organizer_name"],
    )
    fee_col = fee_col or first_existing(
        df,
        [
            "HourlyFeeRange",
            "artist_fee",
            "AvgBookingFee",
            "fee",
            "venue_fee",
            "venue_price",
            "rental_fee",
            "hire_fee",
            "price",
        ],
    )
    currency_col = currency_col or first_existing(
        df,
        ["CurrencyCode", "currency_code", "CurrencySymbol", "currency_symbol", "venue_currency_code"],
    )
    city_col = first_existing(df, ["City", "artist_city", "CurrentLocation", "organizer_city", "venue_city"])

    if not id_col or not name_col:
        raise ValueError(f"{path} mist een id- of naamkolom.")

    return pd.DataFrame(
        {
            "type": kind,
            "id": df[id_col],
            "name": df[name_col].apply(clean),
            "fee": pd.to_numeric(df[fee_col], errors="coerce") if fee_col else pd.NA,
            "currency": df[currency_col].apply(currency) if currency_col else pd.NA,
            "city": df[city_col].apply(clean) if city_col else pd.NA,
        }
    ).drop_duplicates(subset=["id"])


def check_budget(items, budget, budget_currency, top_n=10, hours=1):
    return FeeRecommender(top_n=top_n).recommend(items, budget, budget_currency, hours)


def save_results(results, prefix, output_dir):
    output_dir.mkdir(exist_ok=True)
    full_path = output_dir / f"{prefix}_full.csv"
    results.to_csv(full_path, index=False)
    return full_path


def print_result(label, results):
    top = results[results["in_top_10"]]
    print(f"\n{label} top 10 binnen budget")
    columns = ["rank", "name", "fee", "hours", "total_fee", "currency", "margin", "city"]
    print(top[columns].to_string(index=False) if len(top) else "Geen top 10: geen bekende fee binnen budget.")
    print("\nFull status")
    print(results["budget_check"].value_counts(dropna=False).to_string())


def ask_path(question, default):
    while True:
        answer = input(f"{question} [{default}]: ").strip()
        path = Path(answer) if answer else default
        if str(path).startswith("source "):
            print("Dit lijkt een terminalcommando. Geef hier alleen een CSV-pad of druk Enter.")
            continue
        if not path.exists():
            print(f"Bestand niet gevonden: {path}. Probeer opnieuw of druk Enter voor default.")
            continue
        return path


def ask_float(question):
    while True:
        answer = input(f"{question} (enter = overslaan): ").strip()
        if not answer:
            return None
        try:
            return float(answer)
        except ValueError:
            print("Vul een getal in, bijvoorbeeld 2800.")


def ask_currency(default):
    while True:
        answer = input(f"Budget valuta [{default}]: ").strip() or default
        normalized = currency(answer)
        if str(normalized).replace(".", "", 1).isdigit():
            print("Dit lijkt een bedrag. Vul hier alleen valuta in, bijvoorbeeld EUR.")
            continue
        return normalized


def ask_yes_no(question):
    return input(f"{question} [y/N]: ").strip().lower() in {"y", "yes", "j", "ja"}


def main():
    parser = argparse.ArgumentParser(description="Korte fee/budgetchecker voor artists en venues.")
    parser.add_argument("--artist-budget", type=float)
    parser.add_argument("--venue-budget", type=float)
    parser.add_argument("--budget", type=float, help="Fallback budget voor beide.")
    parser.add_argument("--hours", type=float, help="Aantal uur dat artiesten spelen.")
    parser.add_argument("--currency", default="EUR")
    parser.add_argument("--artists-csv", type=Path)
    parser.add_argument("--venues-csv", type=Path)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--show-full", action="store_true")
    parser.add_argument("--save-full", action="store_true")
    parser.add_argument("--artist-fee-col")
    parser.add_argument("--artist-currency-col")
    parser.add_argument("--venue-fee-col")
    parser.add_argument("--venue-currency-col")
    args = parser.parse_args()

    interactive = not any(
        [
            args.artist_budget,
            args.venue_budget,
            args.budget,
            args.artists_csv,
            args.venues_csv,
            args.save_full,
            args.show_full,
        ]
    )

    if interactive:
        print("Fee budgetchecker")
        print("Laat CSV-pad leeg om de bestaande cleaned-data file te gebruiken.")
        args.artists_csv = ask_path("Cleaned artiesten CSV", DEFAULT_ARTISTS_CSV)
        args.venues_csv = ask_path("Cleaned venues CSV", DEFAULT_VENUES_CSV)
        args.currency = ask_currency(args.currency)
        args.artist_budget = ask_float("Hoeveel budget heb je voor artiesten?")
        args.hours = ask_float("Hoeveel uur duurt de artiestenset / het event?")
        args.venue_budget = ask_float("Hoeveel budget heb je voor venues?")
        args.show_full = ask_yes_no("Volledige lijst ook in terminal tonen?")
        args.save_full = ask_yes_no("Volledige CSV's opslaan/downloaden?")
    else:
        args.artists_csv = args.artists_csv or DEFAULT_ARTISTS_CSV
        args.venues_csv = args.venues_csv or DEFAULT_VENUES_CSV

    budget_currency = currency(args.currency)
    artist_budget = args.artist_budget if args.artist_budget is not None else args.budget
    venue_budget = args.venue_budget if args.venue_budget is not None else args.budget
    artist_hours = args.hours if args.hours is not None else 1

    if artist_budget is None and venue_budget is None:
        raise ValueError("Geef een artist budget, venue budget of algemeen --budget mee.")

    fee_recommender = FeeRecommender()

    if artist_budget is not None:
        artists = load_items(
            args.artists_csv,
            "artist",
            fee_col=args.artist_fee_col,
            currency_col=args.artist_currency_col,
        )
        artist_results = fee_recommender.recommend(artists, artist_budget, budget_currency, hours=artist_hours)
        print_result("Artists", artist_results)
        if args.show_full:
            print(artist_results.to_string(index=False))
        if args.save_full:
            full_path = save_results(artist_results, "artist_budget", args.output_dir)
            print(f"Saved full artist CSV: {full_path}")

    if venue_budget is not None:
        venues = load_items(
            args.venues_csv,
            "venue",
            fee_col=args.venue_fee_col,
            currency_col=args.venue_currency_col,
        )
        venue_results = fee_recommender.recommend(venues, venue_budget, budget_currency)
        print_result("Venues", venue_results)
        if args.show_full:
            print(venue_results.to_string(index=False))
        if args.save_full:
            full_path = save_results(venue_results, "venue_budget", args.output_dir)
            print(f"Saved full venue CSV: {full_path}")


if __name__ == "__main__":
    main()
