

# Gigevate Project

#Stap 1 Repository clonen

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
