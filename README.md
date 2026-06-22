# Gigevate Project

## Step 1: Set up SSH if you do not have an SSH key yet

### 1. Create an SSH key

Replace the email address with your own GitHub email address:

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

Press Enter a few times to use the default location.

---

### 2. View your public key

```bash
cat ~/.ssh/id_ed25519.pub
```

Copy the full output.

---

### 3. Add the key to GitHub

Go to:

**GitHub -> Settings -> SSH and GPG keys -> New SSH key**

Give the key a name, for example `Laptop`, and paste the copied key.

Click **Add SSH key**.

---

### 4. Test the connection

```bash
ssh -T git@github.com
```

If everything works, you should see a message similar to:

```text
Hi username! You've successfully authenticated.
```

---

### 5. Clone the repository

```bash
git clone git@github.com:ScroopyNoopersSenior/Gigevate_project.git
```

## Step 1 if you already have an SSH key: clone the repository

Clone the repository to your computer:

```bash
git clone git@github.com:yourusername/Gigevate_project.git
cd Gigevate_project
```

---

## General workflow

Never work directly on the `main` branch.

Create a separate branch for every new task.

Examples:

```bash
git checkout -b feature/data-cleaning
git checkout -b feature/spotify-api
git checkout -b feature/recommendation-system
```

## Before you start working

Make sure you have the latest version of the repository:

```bash
git checkout main
git pull origin main
```

Then create a new branch, or continue on an existing branch with the same command:

```bash
git checkout -b feature/your-feature
```

## Save your changes

Add your changes:

```bash
git add .
```

Create a commit:

```bash
git commit -m "Short description of the change"
```

Push your branch to GitHub:

```bash
git push origin feature/your-feature
```

---

## Create a Pull Request

When you are done:

1. Go to GitHub.
2. Open the repository.
3. Click **Compare & Pull Request**.
4. Add a short description of what you changed.
5. Create the Pull Request.

After approval, the branch can be merged into `main`.

## After a merge

Everyone should pull the latest version:

```bash
git checkout main
git pull origin main
```

## Branch commands

Switch branches:

```bash
git checkout branch-name
```

Create a new branch or switch to an existing branch:

```bash
git checkout -b new-branch
```

Pull latest changes:

```bash
git pull
```

Push changes:

```bash
git push
```

Check status:

```bash
git status
```

## Useful notes

- Do not work directly on `main`.
- Create a separate branch for each main task.
- Create a Pull Request before merging code into `main`.
- Make sure the code works before opening a Pull Request.
- Use clear commit messages.

## Using the recommendation engine

The recommendation engine combines four filters:

- `availability_score`: checks whether an artist is available.
- `genre_score`: compares event genres with artist main/subgenres.
- `location_score`: calculates distance between the artist and the event location.
- `fee_score`: compares artist costs with the requested budget.

Example:

```bash
python3 recommendation_engine.py --event-id 111 --budget 1500 --hours 2 --top-n 10
```

By default, artists with a booking conflict are not shown. To include unavailable artists:

```bash
python3 recommendation_engine.py --event-id 111 --budget 1500 --hours 2 --include-unavailable
```

Save results as CSV:

```bash
python3 recommendation_engine.py --event-id 111 --budget 1500 --hours 2 --save-csv
```

The default score weights are defined in `recommendation_engine.py`:

```text
genre: 35%
location: 30%
fee: 25%
availability: 10%
```

## Run the match dashboard locally

The recommendation engine can also run as a local JSON API with a web interface.

One-time setup:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Start the server:

```bash
.venv/bin/python recommendation_api.py
```

Open the URL shown in the terminal. By default:

```text
http://127.0.0.1:8000
```

Main API endpoints:

```text
GET  /api/options
POST /api/recommendations
```

Example body for `POST /api/recommendations`:

```json
{
  "eventName": "ADE club night",
  "budgetMin": 500,
  "budgetMax": 2500,
  "genre": "Techno",
  "city": "Amsterdam",
  "country": "Netherlands",
  "eventDate": "2026-09-14",
  "startTime": "23:00",
  "hours": 2,
  "eventType": "Club night",
  "maxDistanceKm": 100,
  "onlyAvailable": true,
  "onlyWithinBudget": false,
  "topN": 50
}
```

## Integration into an existing website

This project is a prototype that a site developer can convert into a real backend integration. The recommendation engine itself is separate from the HTML interface. The developer's main task is to replace the current CSV-based data input with data from the existing website/database, while preserving the same column names and formats.

### Important files

- `recommendation_engine.py`: the central engine. Combines genre, location, fee and availability into a final score.
- `recommendation_api.py`: local JSON API for the web interface. This is where form data is converted into `RecommendationEngine.recommend_for_form(...)`.
- `web/index.html`, `web/styles.css`, `web/app.js`: local frontend. It only calls `/api/options` and `/api/recommendations`.
- `genre_match.py`: genre score.
- `location_score.py`: location/distance score using `worldcities.csv`.
- `artist_fee_recommendations.py`: fee/budget score.
- `availability_check.py`: availability check based on existing bookings.
- `artist_datacleaning.py`, `event_datacleaning.py`, `venue_datacleaning.py`: scripts used to clean the current export CSV files.

### Where the CSV files are loaded

The default paths are defined in `recommendation_engine.py`:

```python
DEFAULT_ARTISTS_CSV = BASE_DIR / "cleaned-data" / "artists_combined.csv"
DEFAULT_EVENTS_CSV = BASE_DIR / "cleaned-data" / "events_combined.csv"
DEFAULT_BOOKINGS_CSV = BASE_DIR / "Gigevate-data (not cleaned)" / "gigevate-export" / "Bookings.csv"
```

These files are loaded in `RecommendationEngine.__init__`:

```python
self.artists = pd.read_csv(artists_path)
self.events = pd.read_csv(events_path)
```

The individual scorers also use the same data:

- `GenreScorer(artists_path, events_path)`
- `AvailabilityChecker(events_path, bookings_path)`
- `LocationScorer(...)`, which uses artist/event location columns plus `worldcities.csv`
- `FeeScorer(...)`, which uses fee and currency columns from the artist rows

For a real site, there are two practical integration options:

1. Temporarily keep generating CSV files from the site/database and pass those paths into `RecommendationEngine(...)`.
2. Later replace `pd.read_csv(...)` with database queries or ORM results, as long as the resulting tables/dataframes contain the same columns.

### Minimum artist columns

`cleaned-data/artists_combined.csv` must contain at least these columns:

```text
ArtistId
ArtistName
City
CountryName
CountryCode
CurrentLocation
MainGenres
SubGenres
AvgBookingFee
NumberOfBookings
CurrencyCode
```

Recommended extra columns:

```text
SpotifyURL
YearsOfExperience
HourlyFeeRange
MinBookingFee
MaxBookingFee
CurrencySymbol
```

Important cleaning rules:

- `ArtistId` must be unique.
- `ArtistName` must not be empty.
- `MainGenres` and `SubGenres` are comma-separated strings, for example `Techno, House`.
- `AvgBookingFee`, `MinBookingFee`, `MaxBookingFee` and `HourlyFeeRange` must be numeric or empty/NA.
- `CurrencyCode` should be a comparable code such as `EUR`, `USD` or `GBP`. `CurrencySymbol` may also exist, but `CurrencyCode` is preferred for production data.
- `City` and `CurrentLocation` should be real city names where possible. Invalid values such as `-`, `unknown`, `test` and `n/a` should be cleaned to empty.
- `CountryName` should be a country name, for example `Netherlands`.
- `CountryCode` should preferably be ISO2, for example `NL`, `DE` or `GB`.

Use `artist_datacleaning.py` for this. Important: check the output path in that script before running it, because older versions may contain a local absolute path.

### Minimum event columns

`cleaned-data/events_combined.csv` must contain at least these columns:

```text
EventId
EventName
DateTimeStart
DateTimeEnd
City
Country
EventType
MainGenres
```

Recommended extra columns:

```text
OrganizerName
StreetAddress
OrganizerId
PublicUserId
```

Important cleaning rules:

- `EventId` must be unique.
- `DateTimeStart` and `DateTimeEnd` must be parseable by pandas, preferably ISO-like with timezone, for example `2026-09-14 23:00:00+00`.
- If `DateTimeEnd` is missing in form data, the API creates an end time based on `hours`.
- `City` and `Country` are used for distance calculation.
- `MainGenres` is comma-separated, for example `Techno`.
- `EventType` is currently mostly used as a form option; the current score uses genre, location, fee and availability.

Use `event_datacleaning.py` for this.

### Minimum booking columns

The availability check uses the raw bookings export:

```text
Gigevate-data (not cleaned)/gigevate-export/Bookings.csv
```

Required minimum columns:

```text
EventId
ArtistId
```

The availability checker joins `Bookings.csv` to `events_combined.csv` through `EventId`, then uses `DateTimeStart` and `DateTimeEnd` from the booked event to find conflicts. An artist is unavailable if an existing booking overlaps with the requested event, including the configured buffer.

### What data the form/API requests

The frontend sends this to `POST /api/recommendations`:

```text
eventName
budgetMin
budgetMax
genre
city
country
eventDate
startTime
hours
eventType
maxDistanceKm
onlyAvailable
onlyWithinBudget
topN
```

In `recommendation_api.py`, this is converted into the event data expected by the engine:

```text
EventName
City
Country
MainGenres
EventType
DateTimeStart
DateTimeEnd
```

The engine actively uses:

- `MainGenres` for genre matching.
- `City` and `Country` for location/distance matching.
- `DateTimeStart` and `DateTimeEnd` for availability.
- `budgetMax`, `hours` and currency for fee scoring.

`budgetMin` is only used for dashboard display and fee distribution labels. The actual fee score currently compares against `budgetMax`.

### What the site receives back

`POST /api/recommendations` returns JSON with:

```text
summary
recommendations
event
filters
```

Each recommendation includes, among other fields:

```text
rank
ArtistId
ArtistName
final_score
available
genre_score
location_score
distance_km
fee_score
total_fee
budget_margin
budget_check
genre_reason
location_reason
fee_reason
MainGenres
SubGenres
AvgBookingFee
NumberOfBookings
SpotifyURL
```

These are the fields the frontend can display. If the site wants to display additional UI elements, those values must come from this response or be explicitly added to the engine/API.

### Production work still required

The dashboard is a recommendation prototype, not a complete booking application. The recommendation form, filters, summary, ranking, match reasons and fee distribution are connected to the local recommendation API. The developer integrating this repository into an existing site must still implement the following product features:

- **Create booking request:** the button is currently visual only. Connect it to the site's booking workflow, pass the selected `ArtistId` and event data, validate the request on the server and show success/error states.
- **View favorites:** the button is currently visual only. It does not open a favorites page or filter the ranking.
- **Save favorites:** clicking the heart works locally, but artist IDs are stored only in browser `localStorage`. Replace or supplement this with authenticated database storage so favorites follow the user across devices and browsers.
- **New event:** the button currently only focuses the event-name field. The existing site must decide whether it should clear the form, open an event editor or create/load a persisted event.
- **Artist details and selection:** ranking rows display recommendation data but do not open an artist profile or maintain a selected artist for a booking request. Add links or selection behavior using `ArtistId`.
- **User accounts and authorization:** the prototype has no login, ownership checks or permissions. Use the existing site's authentication and verify server-side that a user may view an event and create a booking.
- **Persistent events and bookings:** submitted form data is not saved. Store events and booking requests in the site's database and ensure confirmed/pending bookings are included in the availability data used by the engine.
- **Production API security:** add authentication, authorization, request validation, rate limiting, logging and the site's normal CSRF/CORS policy. The local API currently allows CORS from every origin for development.
- **Production deployment:** run the recommendation API behind the site's normal application server or internal service layer. Do not rely on Python's development `ThreadingHTTPServer` in production.
- **Loading and error UX:** the prototype shows a basic status message. Integrate the site's notification, retry and form-validation patterns.

Currently working in the prototype:

- Loading genres, cities and event types from the engine data.
- Submitting the form to `POST /api/recommendations`.
- Applying availability, budget and distance filters supported by the engine.
- Rendering recommendation scores, reasons, fees and summary counts.
- Showing more recommendation rows.
- Clearing the form fields.
- Saving and removing favorites in the current browser only.

### Important limitation

The current engine only produces artist recommendations. Venue matching is not part of the current recommendation engine. If the existing site also needs to rank venues, a separate venue scorer/API should be added. Do not use hardcoded venue scores in production.
