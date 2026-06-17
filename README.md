

# Gigevate Project

#stap 1 als je geen ssh key hebt
## SSH instellen (alleen als je nog geen SSH-key hebt)

### 1. Maak een SSH-key aan

Vervang het e-mailadres door je eigen GitHub e-mailadres:

```bash
ssh-keygen -t ed25519 -C "jouw_email@example.com"
```

Druk vervolgens een paar keer op Enter om de standaardlocatie te gebruiken.

---

### 2. Bekijk je publieke sleutel

```bash
cat ~/.ssh/id_ed25519.pub
```

Kopieer de volledige output.

---

### 3. Voeg de sleutel toe aan GitHub

Ga naar:

**GitHub → Settings → SSH and GPG keys → New SSH key**

Geef de sleutel een naam (bijvoorbeeld "Laptop") en plak de gekopieerde sleutel.

Klik op **Add SSH key**.

---

### 4. Test de verbinding

```bash
ssh -T git@github.com
```

Als alles goed werkt krijg je een bericht vergelijkbaar met:

```text
Hi gebruikersnaam! You've successfully authenticated.
```

---

### 5. Clone de repository

```bash
git clone git@github.com:ScroopyNoopersSenior/Gigevate_project.git
```


#Stap 1 als je wel ssh key hebt Repository clonen

Clone de repository naar je eigen computer:


git clone git@github.com:jegebruikersnaam/Gigevate_project.git
cd Gigevate_project

---

## Algemene werkwijze

Werk nooit direct op de `main` branch.

Voor iedere nieuwe taak maak je een eigen branch aan.

Voorbeelden:

git checkout -b feature/data-cleaning

git checkout -b feature/spotify-api

git checkout -b feature/recommendation-system


## Voordat je begint met werken

Zorg altijd dat je de nieuwste versie van de repository hebt:

git checkout main
git pull origin main

Maak daarna een nieuwe branch of ga verder in een al bestaande branch(zelfde command):

git checkout -b feature/jouw-feature


## Wijzigingen opslaan

Voeg je wijzigingen toe:

git add .

Maak een commit:

git commit -m "Korte beschrijving van wijziging"

Push je branch naar GitHub:

git push origin feature/jouw-feature

---

## Pull Request maken

Wanneer je klaar bent:

1. Ga naar GitHub.
2. Open de repository.
3. Klik op **Compare & Pull Request**.
4. Voeg een korte beschrijving toe van wat je hebt gedaan.
5. Maak de Pull Request aan.

Na goedkeuring kan de branch worden gemerged naar `main`.

## Na een merge

Iedereen haalt vervolgens de nieuwste versie op:

git checkout main
git pull origin main

## Branch

Wissel van branch:

git checkout branchnaam

Nieuwe branch maken of naar bestaande branch gaan:

git checkout -b nieuwe-branch

Laatste wijzigingen ophalen:

git pull

Wijzigingen uploaden:

git push

Status bekijken:

git status

## Handig

- Werk niet direct op `main`.
- Maak voor iedere hoofdtaak een aparte branch.
- Maak een Pull Request voordat code naar `main` gaat.
- Zorg dat code werkt voordat je een Pull Request indient.
- Geef commits duidelijke namen.

## Recommendation engine gebruiken

De recommendation engine combineert vier filters:

- `availability_score`: controleert of een artiest beschikbaar is.
- `genre_score`: vergelijkt eventgenres met de main/subgenres van artiesten.
- `location_score`: berekent afstand tussen artiest en eventlocatie.
- `fee_score`: vergelijkt artiestkosten met het opgegeven budget.

Voorbeeld:

```bash
python3 recommendation_engine.py --event-id 111 --budget 1500 --hours 2 --top-n 10
```

Standaard worden artiesten met een booking conflict niet getoond. Wil je ze wel in de output zien:

```bash
python3 recommendation_engine.py --event-id 111 --budget 1500 --hours 2 --include-unavailable
```

Resultaten opslaan als CSV:

```bash
python3 recommendation_engine.py --event-id 111 --budget 1500 --hours 2 --save-csv
```

De standaard scoreweging staat in `recommendation_engine.py`:

```text
genre: 35%
location: 30%
fee: 25%
availability: 10%
```
