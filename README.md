# Gigevate recommendation prototype

Dit project is een prototype voor het matchen van artiesten aan evenementen. Het idee is simpel: gegevens uit een Gigevate-export worden opgeschoond en daarna gebruikt om artiesten te vergelijken op genre, afstand, prijs en beschikbaarheid.

De uitkomst is een ranglijst met artiesten. Je kunt die lijst in de terminal bekijken of via het lokale dashboard.

De oude uitleg over Git, SSH, branches en pull requests staat in [dev_instruction/README.md](dev_instruction/README.md).

## Hoe het project werkt

De brondata komt uit een CSV-export van Gigevate. De scripts `artist_datacleaning.py` en `event_datacleaning.py` combineren de losse tabellen tot twee bestanden:

- `cleaned-data/artists_combined.csv`
- `cleaned-data/events_combined.csv`

De recommendation engine leest deze bestanden in en gebruikt vier losse onderdelen:

- `genre_match.py` vergelijkt de genres van een event en een artiest;
- `location_score.py` berekent de afstand tussen de artiest en het event;
- `artist_fee_recommendations.py` controleert of de fee binnen het budget valt;
- `availability_check.py` kijkt of de artiest al een andere booking heeft.

`recommendation_engine.py` voegt deze scores samen en sorteert de artiesten. `recommendation_api.py` maakt de engine beschikbaar voor het dashboard in de map `web`.

## Bestanden in deze repository

De belangrijkste bestanden zijn:

- `artist_datacleaning.py`: maakt de gecombineerde artiestendataset;
- `event_datacleaning.py`: maakt de gecombineerde eventdataset;
- `venue_datacleaning.py`: maakt overzichten van organisatoren, venues en historische events;
- `recommendation_engine.py`: berekent de uiteindelijke ranking;
- `recommendation_api.py`: start de lokale API en het dashboard;
- `worldcities.csv`: lokale lijst met steden en coördinaten voor de afstandsberekening;
- `unmatched_locations.csv`: locaties die niet goed herkend konden worden;
- `web/`: HTML, JavaScript en CSS van het dashboard.

De mappen `gigevate-export/` en `cleaned-data/` en databestanden zoals CSV, Excel en databasebestanden staan in `.gitignore`. Ze blijven dus lokaal en worden niet naar GitHub gepusht.


## Data klaarzetten

De ruwe data hoort idealiter in deze structuur te staan:

     ArtistDetails.csv
     Artists.csv
     Bookings.csv
     Countries.csv
     Currencies.csv
     EventDetails.csv
     Events.csv
     Genres.csv
     LinkedGenres.csv

Er kunnen meer bestanden in de export staan, maar dit zijn de belangrijkste voor de huidige engine.

## Data opschonen

Voer de volgende scripts uit vanuit de root van het project:

```bash
.venv/bin/python artist_datacleaning.py
.venv/bin/python event_datacleaning.py
```

De scripts maken de map `cleaned-data/` automatisch aan.

`artist_datacleaning.py` combineert onder andere artiestprofielen, landen, genres, valuta en eerdere bookings. `event_datacleaning.py` combineert events met eventdetails en genres.

Er is ook een script voor venue- en organisatorgegevens:

```bash
.venv/bin/python venue_datacleaning.py
```

Dit script verwijst nog naar het oude pad `Gigevate-data (not cleaned)/gigevate-export/`. Pas eerst `BASE_DIR` bovenaan het bestand aan als je de huidige map `gigevate-export/` wilt gebruiken.

## Een recommendation uitvoeren

Gebruik een `EventId` uit `cleaned-data/events_combined.csv`:

```bash
.venv/bin/python recommendation_engine.py --event-id 111 --budget 1500 --hours 2 --top-n 10
```

Artiesten met een bookingconflict worden standaard niet getoond. Met deze optie neem je ze toch mee:

```bash
.venv/bin/python recommendation_engine.py --event-id 111 --budget 1500 --hours 2 --include-unavailable
```

Met `--save-csv` wordt het resultaat opgeslagen in `cleaned-data/`.

Je kunt de genrescore ook los testen:

```bash
.venv/bin/python genre_match.py --event-id 111 --top-n 15
```

## Dashboard starten

Start de lokale server:

```bash
.venv/bin/python recommendation_api.py
```


De API heeft drie endpoints:

- `GET /api/health` voor een simpele statuscontrole;
- `GET /api/options` voor genres, steden en eventtypes;
- `POST /api/recommendations` voor een nieuwe ranking.

Het dashboard verstuurt het formulier naar deze API en toont daarna de beste matches, de matchredenen en de fee-verdeling. Opgeslagen favorieten staan alleen in de browser. De knop voor een booking request is nog niet gekoppeld aan een database.

## Berekening van de score

Iedere deelscore ligt tussen 0 en 1. De standaardverdeling is:

- genre: 35%;
- locatie: 30%;
- fee: 25%;
- beschikbaarheid: 10%.

Deze gewichten staan in `DEFAULT_WEIGHTS` in `recommendation_engine.py`.

Bij genre krijgt een overeenkomst met een hoofdgenre een score van 1. Een overeenkomst met een subgenre krijgt 0,5.

Voor locatie worden plaatsnamen opgezocht in `worldcities.csv`. Daarna wordt de hemelsbrede afstand berekend. Een artiest in dezelfde stad scoort hoger dan een artiest op grote afstand. De berekening houdt nog geen rekening met reistijd of vervoer.

Voor de fee gebruikt de engine de gemiddelde booking fee maal het aantal uren. Een artiest binnen het budget krijgt de hoogste score. Bij een onbekende fee blijft de artiest in de lijst, maar met een lagere score. Verschillende valuta worden nog niet omgerekend.

Voor beschikbaarheid worden bestaande bookings vergeleken met de tijd van het event. Na een bestaande booking geldt standaard ook een buffer van acht uur.

## Data die de engine verwacht

Voor artiesten zijn vooral deze velden belangrijk:

```text
ArtistId, ArtistName, City, CountryName, CountryCode,
CurrentLocation, MainGenres, SubGenres, AvgBookingFee,
CurrencyCode, NumberOfBookings
```

De standaard scoreweging staat in `recommendation_engine.py`. Availability wordt standaard als hard filter gebruikt, dus niet als los percentage in de ranking:

```text
genre: 40%
location: 35%
fee: 25%
availability: hard filter
```

Als de kolomnamen van een nieuwe export veranderen, moeten de cleaning-scripts daarop worden aangepast.
