from pathlib import Path

import pandas as pd


BASE_DIR = Path("Gigevate-data (not cleaned)") / "gigevate-export"
OUTPUT_DIR = Path("cleaned-data")


def clean_text(value):
    if pd.isna(value):
        return pd.NA
    text = str(value).strip()
    if not text:
        return pd.NA
    return " ".join(text.split())


def normalize_bool(value):
    if pd.isna(value):
        return pd.NA
    value = str(value).strip().lower()
    if value in {"t", "true", "1", "yes", "y"}:
        return True
    if value in {"f", "false", "0", "no", "n"}:
        return False
    return pd.NA


def unique_join(values):
    cleaned = []
    seen = set()
    for value in values:
        value = clean_text(value)
        if pd.isna(value):
            continue
        key = str(value).lower()
        if key not in seen:
            cleaned.append(str(value))
            seen.add(key)
    return ", ".join(cleaned) if cleaned else pd.NA


def read_csv(name):
    return pd.read_csv(BASE_DIR / f"{name}.csv")


def load_sources():
    organizers = read_csv("Organizers")
    organizer_details = read_csv("OrganizerDetails")
    events = read_csv("Events")
    event_details = read_csv("EventDetails")
    countries = read_csv("Countries")
    return organizers, organizer_details, events, event_details, countries


def prepare_organizers(organizers, organizer_details, countries):
    countries = countries[["Id", "Name", "Code"]].rename(
        columns={
            "Id": "country_id",
            "Name": "organizer_country_name",
            "Code": "organizer_country_code",
        }
    )

    organizers = organizers.rename(
        columns={
            "Id": "organizer_id",
            "OrganizerName": "organizer_name",
            "City": "organizer_city",
            "Country": "country_id",
            "Name": "contact_first_name",
            "Surname": "contact_last_name",
            "Email": "organizer_email",
            "ContactNumber": "organizer_contact_number",
            "IsActive": "organizer_is_active",
            "IsDeleted": "organizer_is_deleted",
            "CreatedOn": "organizer_created_on",
            "LastModifiedOn": "organizer_last_modified_on",
        }
    )

    organizer_details = organizer_details.rename(
        columns={
            "Id": "organizer_detail_id",
            "OrganizerId": "organizer_id",
            "BusinessName": "business_name",
            "LocationOfOperations": "location_of_operations",
            "Biography": "biography",
            "PreferredEventSizes": "preferred_event_sizes",
            "HasResidentDJ": "has_resident_dj",
            "HasPartnershipsOrSponsors": "has_partnerships_or_sponsors",
            "SoundEquipmentType": "sound_equipment_type",
            "SoundEquipmentConsole": "sound_equipment_console",
            "StageDimensions": "stage_dimensions",
            "HasStageVisuals": "has_stage_visuals",
            "StageType": "stage_type",
            "MaxCapacity": "max_capacity",
            "AmountOfStages": "amount_of_stages",
            "TechnicalEquipmentProvided": "technical_equipment_provided",
            "TradingHours": "trading_hours",
        }
    )

    organizer_columns = [
        "organizer_id",
        "organizer_is_active",
        "organizer_is_deleted",
        "organizer_created_on",
        "organizer_last_modified_on",
        "organizer_name",
        "organizer_city",
        "country_id",
        "contact_first_name",
        "contact_last_name",
        "organizer_email",
        "organizer_contact_number",
        "UserId",
    ]
    detail_columns = [
        "organizer_id",
        "organizer_detail_id",
        "business_name",
        "location_of_operations",
        "biography",
        "preferred_event_sizes",
        "has_resident_dj",
        "has_partnerships_or_sponsors",
        "sound_equipment_type",
        "sound_equipment_console",
        "stage_dimensions",
        "has_stage_visuals",
        "stage_type",
        "max_capacity",
        "amount_of_stages",
        "technical_equipment_provided",
        "trading_hours",
    ]

    organizer_profiles = organizers[organizer_columns].merge(
        organizer_details[detail_columns],
        on="organizer_id",
        how="left",
    )
    organizer_profiles = organizer_profiles.merge(countries, on="country_id", how="left")

    bool_columns = [
        "organizer_is_active",
        "organizer_is_deleted",
        "has_resident_dj",
        "has_partnerships_or_sponsors",
        "has_stage_visuals",
    ]
    for column in bool_columns:
        organizer_profiles[column] = organizer_profiles[column].apply(normalize_bool)

    text_columns = [
        "organizer_name",
        "organizer_city",
        "organizer_country_name",
        "organizer_country_code",
        "contact_first_name",
        "contact_last_name",
        "organizer_email",
        "organizer_contact_number",
        "business_name",
        "location_of_operations",
        "biography",
        "preferred_event_sizes",
        "sound_equipment_type",
        "sound_equipment_console",
        "stage_dimensions",
        "stage_type",
        "technical_equipment_provided",
        "trading_hours",
    ]
    for column in text_columns:
        organizer_profiles[column] = organizer_profiles[column].apply(clean_text)

    organizer_profiles["max_capacity"] = pd.to_numeric(
        organizer_profiles["max_capacity"], errors="coerce"
    )
    organizer_profiles["amount_of_stages"] = pd.to_numeric(
        organizer_profiles["amount_of_stages"], errors="coerce"
    )
    organizer_profiles["contact_name"] = (
        organizer_profiles["contact_first_name"].fillna("")
        + " "
        + organizer_profiles["contact_last_name"].fillna("")
    ).str.strip()
    organizer_profiles["contact_name"] = organizer_profiles["contact_name"].replace(
        "", pd.NA
    )

    return organizer_profiles


def prepare_historical_events(events, event_details):
    events = events.rename(
        columns={
            "Id": "event_id",
            "EventName": "event_name",
            "OrganizerName": "event_export_organizer_name",
            "OrganizerId": "organizer_id",
            "DateTimeStart": "historical_event_start",
            "DateTimeEnd": "historical_event_end",
            "City": "event_city",
            "Country": "event_country",
            "StreetAddress": "street_address",
            "Status": "event_status",
            "GenreName": "genre",
            "IsActive": "event_is_active",
            "IsDeleted": "event_is_deleted",
        }
    )

    event_details = event_details.rename(
        columns={
            "EventId": "event_id",
            "EventType": "event_type",
            "PrimaryGenre": "primary_genre",
            "AmountOfStages": "event_amount_of_stages",
            "AmountOfArtists": "event_amount_of_artists",
            "PASystem": "pa_system",
            "Turntable": "turntable",
            "CDJ": "cdj",
            "Mixer": "mixer",
            "Monitor": "monitor",
            "IsVisualsRequired": "visuals_required",
            "IsCancelled": "is_cancelled",
        }
    )

    event_columns = [
        "event_id",
        "organizer_id",
        "event_export_organizer_name",
        "event_name",
        "historical_event_start",
        "historical_event_end",
        "event_city",
        "event_country",
        "street_address",
        "event_status",
        "CancelledMessage",
        "genre",
        "event_is_active",
        "event_is_deleted",
    ]
    detail_columns = [
        "event_id",
        "event_type",
        "primary_genre",
        "event_amount_of_stages",
        "event_amount_of_artists",
        "pa_system",
        "turntable",
        "cdj",
        "mixer",
        "monitor",
        "visuals_required",
        "is_cancelled",
    ]

    historical_events = events[event_columns].merge(
        event_details[detail_columns],
        on="event_id",
        how="left",
    )

    bool_columns = [
        "event_is_active",
        "event_is_deleted",
        "visuals_required",
        "is_cancelled",
    ]
    for column in bool_columns:
        historical_events[column] = historical_events[column].apply(normalize_bool)

    text_columns = [
        "event_export_organizer_name",
        "event_name",
        "event_city",
        "event_country",
        "street_address",
        "CancelledMessage",
        "genre",
        "event_type",
        "primary_genre",
        "pa_system",
        "turntable",
        "cdj",
        "mixer",
        "monitor",
    ]
    for column in text_columns:
        historical_events[column] = historical_events[column].apply(clean_text)

    historical_events["organizer_id"] = pd.to_numeric(
        historical_events["organizer_id"], errors="coerce"
    ).astype("Int64")
    historical_events["historical_event_start"] = pd.to_datetime(
        historical_events["historical_event_start"], errors="coerce", utc=True
    )
    historical_events["historical_event_end"] = pd.to_datetime(
        historical_events["historical_event_end"], errors="coerce", utc=True
    )
    historical_events["event_status"] = pd.to_numeric(
        historical_events["event_status"], errors="coerce"
    ).astype("Int64")
    historical_events["event_amount_of_stages"] = pd.to_numeric(
        historical_events["event_amount_of_stages"], errors="coerce"
    ).astype("Int64")
    historical_events["event_amount_of_artists"] = pd.to_numeric(
        historical_events["event_amount_of_artists"], errors="coerce"
    ).astype("Int64")
    historical_events["cancelled_event"] = (
        historical_events["is_cancelled"].fillna(False)
        | historical_events["CancelledMessage"].notna()
    )

    return historical_events


def build_organizer_summary(organizer_profiles, historical_events):
    events_with_organizer = historical_events[
        historical_events["organizer_id"].notna()
    ].copy()

    event_summary = (
        events_with_organizer.groupby("organizer_id")
        .agg(
            total_historical_events=("event_id", "nunique"),
            active_historical_events=(
                "event_is_active",
                lambda values: int(values.fillna(False).sum()),
            ),
            deleted_historical_events=(
                "event_is_deleted",
                lambda values: int(values.fillna(False).sum()),
            ),
            cancelled_historical_events=(
                "cancelled_event",
                lambda values: int(values.fillna(False).sum()),
            ),
            first_historical_event_start=("historical_event_start", "min"),
            latest_historical_event_start=("historical_event_start", "max"),
            event_cities=("event_city", unique_join),
            event_countries=("event_country", unique_join),
            street_addresses=("street_address", unique_join),
            genres_hosted=("genre", unique_join),
            primary_genres_hosted=("primary_genre", unique_join),
            event_types_hosted=("event_type", unique_join),
            event_pa_systems=("pa_system", unique_join),
            event_cdjs=("cdj", unique_join),
            event_mixers=("mixer", unique_join),
            event_monitors=("monitor", unique_join),
        )
        .reset_index()
    )

    organizer_summary = organizer_profiles.merge(
        event_summary, on="organizer_id", how="left"
    )

    count_columns = [
        "total_historical_events",
        "active_historical_events",
        "deleted_historical_events",
        "cancelled_historical_events",
    ]
    for column in count_columns:
        organizer_summary[column] = organizer_summary[column].fillna(0).astype(int)

    output_columns = [
        "organizer_id",
        "organizer_name",
        "business_name",
        "organizer_is_active",
        "organizer_is_deleted",
        "organizer_city",
        "organizer_country_name",
        "organizer_country_code",
        "location_of_operations",
        "contact_name",
        "organizer_email",
        "organizer_contact_number",
        "max_capacity",
        "amount_of_stages",
        "preferred_event_sizes",
        "has_resident_dj",
        "has_partnerships_or_sponsors",
        "sound_equipment_type",
        "sound_equipment_console",
        "stage_dimensions",
        "stage_type",
        "has_stage_visuals",
        "technical_equipment_provided",
        "trading_hours",
        "total_historical_events",
        "active_historical_events",
        "deleted_historical_events",
        "cancelled_historical_events",
        "first_historical_event_start",
        "latest_historical_event_start",
        "event_cities",
        "event_countries",
        "street_addresses",
        "genres_hosted",
        "primary_genres_hosted",
        "event_types_hosted",
        "event_pa_systems",
        "event_cdjs",
        "event_mixers",
        "event_monitors",
        "biography",
    ]

    return organizer_summary[output_columns].sort_values(
        ["total_historical_events", "organizer_name"], ascending=[False, True]
    )


def build_historical_event_locations_output(historical_events, organizer_profiles):
    organizer_names = organizer_profiles[
        ["organizer_id", "organizer_name", "business_name"]
    ]
    output = historical_events.merge(organizer_names, on="organizer_id", how="left")

    output_columns = [
        "event_id",
        "event_name",
        "organizer_id",
        "organizer_name",
        "business_name",
        "event_export_organizer_name",
        "historical_event_start",
        "historical_event_end",
        "event_city",
        "event_country",
        "street_address",
        "event_status",
        "cancelled_event",
        "genre",
        "event_type",
        "primary_genre",
        "event_amount_of_stages",
        "event_amount_of_artists",
        "pa_system",
        "turntable",
        "cdj",
        "mixer",
        "monitor",
        "visuals_required",
    ]

    return output[output_columns].sort_values(
        ["organizer_id", "historical_event_start", "event_id"]
    )


def build_most_important_eventdata(historical_event_locations):
    output_columns = [
        "event_id",
        "event_name",
        "organizer_id",
        "organizer_name",
        "event_country",
        "historical_event_start",
        "historical_event_end",
        "primary_genre",
        "event_type",
        "event_amount_of_stages",
        "event_amount_of_artists",
        "pa_system",
        "cdj",
        "mixer",
        "monitor",
        "turntable",
        "visuals_required",
        "event_status",
        "cancelled_event",
    ]

    return historical_event_locations[output_columns].sort_values(
        ["organizer_id", "historical_event_start", "event_id"]
    )


def build_most_important_venuedata(organizer_summary):
    output = organizer_summary.rename(
        columns={
            "event_cities": "historical_venue_cities",
            "event_countries": "historical_event_countries",
            "street_addresses": "historical_venue_street_addresses",
        }
    )

    output_columns = [
        "organizer_id",
        "organizer_name",
        "business_name",
        "contact_name",
        "organizer_email",
        "organizer_contact_number",
        "organizer_city",
        "organizer_country_name",
        "organizer_country_code",
        "location_of_operations",
        "historical_venue_cities",
        "historical_venue_street_addresses",
        "historical_event_countries",
        "max_capacity",
        "amount_of_stages",
        "preferred_event_sizes",
        "sound_equipment_type",
        "sound_equipment_console",
        "technical_equipment_provided",
        "stage_dimensions",
        "stage_type",
        "has_stage_visuals",
        "has_resident_dj",
        "has_partnerships_or_sponsors",
        "trading_hours",
        "primary_genres_hosted",
        "event_types_hosted",
        "total_historical_events",
        "organizer_is_active",
        "organizer_is_deleted",
    ]

    return output[output_columns].sort_values(
        ["total_historical_events", "organizer_name"], ascending=[False, True]
    )


def main():
    organizers, organizer_details, events, event_details, countries = load_sources()
    organizer_profiles = prepare_organizers(organizers, organizer_details, countries)
    historical_events = prepare_historical_events(events, event_details)

    organizer_summary = build_organizer_summary(organizer_profiles, historical_events)
    historical_event_locations = build_historical_event_locations_output(
        historical_events, organizer_profiles
    )
    most_important_eventdata = build_most_important_eventdata(
        historical_event_locations
    )
    most_important_venuedata = build_most_important_venuedata(organizer_summary)

    OUTPUT_DIR.mkdir(exist_ok=True)
    most_important_eventdata.to_csv(
        OUTPUT_DIR / "most_important_eventdata.csv", index=False
    )
    most_important_venuedata.to_csv(
        OUTPUT_DIR / "most_important_venuedata.csv", index=False
    )

    print(
        f"Wrote {OUTPUT_DIR / 'most_important_eventdata.csv'} "
        f"({len(most_important_eventdata)} rows)"
    )
    print(
        f"Wrote {OUTPUT_DIR / 'most_important_venuedata.csv'} "
        f"({len(most_important_venuedata)} rows)"
    )


if __name__ == "__main__":
    main()
