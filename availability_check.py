import pandas as pd
import warnings
warnings.filterwarnings("ignore")


class AvailabilityChecker:

    def __init__(self, events_path, bookings_path, buffer_hours=8):

        self.buffer_hours = buffer_hours

        self.events = pd.read_csv(events_path)
        self.bookings = pd.read_csv(bookings_path)

        self.events["StartTime"] = (self.events["DateTimeStart"].apply(self.parse_datetime_safe))

        self.events["EndTime"] = (self.events["DateTimeEnd"].apply(self.parse_datetime_safe))

        self.booking_schedule = self.bookings.merge(
            self.events[
                [
                    "EventId",
                    "EventName",
                    "StartTime",
                    "EndTime"
                ]
            ],
            on="EventId",
            how="left"
        )


    def parse_datetime_safe(self, dt):

        if pd.isna(dt):
            return pd.NaT

        dt = str(dt).strip()

        invalid_values = [
            "-infinity",
            "infinity",
            "0001-01-01",
            "0001-01-01 00:00:00+00"
        ]

        if dt in invalid_values:
            return pd.NaT

        try:
            return pd.to_datetime(dt, utc=True)
        except:
            return pd.NaT


    def get_event(self, event_id):

        event = self.events[
            self.events["EventId"] == event_id
        ]

        if len(event) == 0:
            return None

        return event.iloc[0]


    def has_conflict(self, event_start, event_end, booking_start, booking_end):

        if pd.isna(event_start):
            return False

        if pd.isna(event_end):
            event_end = event_start

        if pd.isna(booking_end):
            booking_end = booking_start

        booking_end = (booking_end + pd.Timedelta(hours=self.buffer_hours))

        return (event_start < booking_end and event_end > booking_start)


    def get_availability_info(self, artist_id, event_id ):

        event = self.get_event(event_id)

        if event is None:
            raise ValueError(f"Event {event_id} not found.")

        artist_bookings = self.booking_schedule[self.booking_schedule["ArtistId"]== artist_id]

        conflict_count = 0

        for _, booking in artist_bookings.iterrows():

            booking_start = booking["StartTime"]
            booking_end = booking["EndTime"]

            if pd.isna(booking_start):
                continue

            if self.has_conflict(
                event["StartTime"],
                event["EndTime"],
                booking_start,
                booking_end
            ):
                conflict_count += 1

        available = conflict_count == 0

        return {
            "available": available,
            "availability_score": 1.0 if available else 0.0,
            "conflicts": conflict_count
        }


    def get_availability_info_time(self, artist_id, start_time, end_time):
        """
        Returns availability info for a custom time window.
        """

        if not isinstance(start_time, pd.Timestamp):
            start_time = self.parse_datetime_safe(start_time)

        if not isinstance(end_time, pd.Timestamp):
            end_time = self.parse_datetime_safe(end_time)

        artist_bookings = self.booking_schedule[self.booking_schedule["ArtistId"]== artist_id]

        conflict_count = 0

        for _, booking in artist_bookings.iterrows():

            booking_start = booking["StartTime"]
            booking_end = booking["EndTime"]

            if pd.isna(booking_start):
                continue

            if self.has_conflict(
                start_time,
                end_time,
                booking_start,
                booking_end
            ):
                conflict_count += 1

        available = conflict_count == 0

        return {
            "available": available,
            "availability_score": 1.0 if available else 0.0,
            "conflicts": conflict_count
        }


    def is_available(self, artist_id, event_id):

        result = self.get_availability_info(artist_id, event_id)

        return result["available"]


    def is_available_time(self, artist_id, start_time, end_time):

        result = self.get_availability_info_time(artist_id, start_time, end_time)

        return result["available"]


    def get_availability_score(self, artist_id, event_id):

        result = self.get_availability_info(artist_id, event_id)

        return result["availability_score"]


    def score_artist_for_event(self, artist, event):
        """Returns availability data for one artist and one event."""

        artist_id = artist.get("ArtistId") if hasattr(artist, "get") else artist
        event_id = event.get("EventId") if hasattr(event, "get") else event

        info = self.get_availability_info(artist_id, event_id)

        return {
            "available": info["available"],
            "availability_score": info["availability_score"],
            "availability_reason": "available" if info["available"] else "booking conflict",
            "conflicts": info["conflicts"]
        }


    def get_available_artists(self, artists_path, start_time, end_time):
        """
        Returns all artists that are
        available during a custom
        time period.
        """

        artists = pd.read_csv(artists_path)

        results = []

        for _, artist in artists.iterrows():

            info = (
                self.get_availability_info_time(
                    artist["ArtistId"],
                    start_time,
                    end_time
                )
            )

            if info["available"]:
                results.append({
                    "ArtistId": artist["ArtistId"],
                    "ArtistName": artist["ArtistName"],
                    "Available": info["available"],
                    "AvailabilityScore": info["availability_score"]
                })

        return pd.DataFrame(results)


    def check_all_artists(self, artists_path, event_id):

        artists = pd.read_csv(artists_path)
        results = []

        for _, artist in artists.iterrows():

            info = self.get_availability_info(
                artist["ArtistId"],
                event_id
            )

            results.append({
                "ArtistId": artist["ArtistId"],
                "ArtistName": artist["ArtistName"],
                "Available": info["available"],
                "AvailabilityScore": info["availability_score"],
                "Conflicts": info["conflicts"]
            })

        return pd.DataFrame(results)


    def count_available_artists(self, artists_path, start_time, end_time):

        available_artists = (self.get_available_artists(artists_path, start_time, end_time))

        return len(available_artists)


if __name__ == "__main__":

    pass

    # EVENTS_PATH = (
    #     "/home/z-y-h/Gigevate_project/"
    #     "cleaned-data/events_combined.csv"
    # )

    # BOOKINGS_PATH = (
    #     "/home/z-y-h/Gigevate_project/"
    #     "Gigevate-data (not cleaned)/"
    #     "gigevate-export/Bookings.csv"
    # )

    # ARTISTS_PATH = (
    #     "/home/z-y-h/Gigevate_project/"
    #     "cleaned-data/artists_combined.csv"
    # )

    # checker = AvailabilityChecker(
    #     EVENTS_PATH,
    #     BOOKINGS_PATH
    # )

    # # Check availability for a specific event (Id)
    # EVENT_ID = 102  # Not available test: 111

    # result = checker.check_all_artists(
    #     ARTISTS_PATH,
    #     EVENT_ID
    # )

    # print(result.head(20))

    # print("\nSummary:")
    # print(
    #     result["Available"]
    #     .value_counts()
    # )

    #    # Check availability for a custom time window
    #    # Available test: EventId: 112, Time: 2025-08-08 19:00:00+00 to 2025-08-09 02:00:00+00
    #    available_artists = checker.get_available_artists(
    #        ARTISTS_PATH,
    #        start_time="2025-08-08 19:00:00+00",
    #        end_time="2025-08-09 02:00:00+00"
    #    )

    # # Not Available test: EventID = 111, Time: 2024-10-22 14:00:00+00 to 2025-10-27 06:00:00+00
    # # Not Available test: EventID = 135, Time: 2024-07-19 23:00:00+00 to 2024-07-20 04:00:00+00
    # available_artists = checker.get_available_artists(
    #     ARTISTS_PATH,
    #     start_time="2024-07-19 23:00:00+00",
    #     end_time="2024-07-20 04:00:00+00"
    # )

    # print(available_artists.head(20))

    # print(
    #     f"\nTotal available artists: "
    #     f"{len(available_artists)}"
    # )

    # Count total available artists
    # count = checker.count_available_artists(
    #     ARTISTS_PATH,
    #     start_time,
    #     end_time
    # )
