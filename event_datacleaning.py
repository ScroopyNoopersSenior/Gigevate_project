import pandas as pd
import os
import warnings
warnings.filterwarnings('ignore')

print("Combine csv data for events")

# Load CSV files
print("\n loading files")
data_folder = '/Users/djenna/Gigevate_project/Gigevate-data (not cleaned)/gigevate-export/'

events = pd.read_csv(data_folder + 'Events.csv')
print(f" * Events: {len(events)} rows")

genres = pd.read_csv(data_folder + 'Genres.csv')
print(f" * Genres: {len(genres)} rows")

linked_genres = pd.read_csv(data_folder + 'LinkedGenres.csv')
print(f" * LinkedGenres: {len(linked_genres)} rows")

event_details = pd.read_csv(data_folder + 'EventDetails.csv')
print(f" * EventDetails: {len(event_details)} rows")

# Rename some columns

# Events
events_clean = events[[
    'Id',
    'EventName',
    'OrganizerName',
    'DateTimeStart',
    'DateTimeEnd',
    'City',
    'Country',
    'StreetAddress',
    'OrganizerId',
    'PublicUserId'
]].copy()
events_clean = events_clean.rename(columns={
    'Id': 'EventId'
})

# Genres
genres_clean = genres[[
    'Id',
    'Name'
]].copy()
genres_clean = genres_clean.rename(columns={
    'Id': 'GenreId',
    'Name': 'GenreName'
})

# EventDetails - alleen actieve events
event_details_clean = event_details[[
    'EventId',
    'IsActive',
    'EventType'
]].copy()

# Filter alleen actieve events (t = True)
event_details_clean = event_details_clean[event_details_clean['IsActive'] == 't']
event_details_clean = event_details_clean.drop('IsActive', axis=1)

# LinkedGenres voor events (alleen main genres)
linked_genres_clean = linked_genres[[
    'EventId',
    'GenreId',
    'IsMainGenre'
]].copy()

# Verwijder rijen zonder EventId
linked_genres_clean = linked_genres_clean[linked_genres_clean['EventId'].notna()]

# Alleen main genres gebruiken (IsMainGenre = t)
linked_genres_clean = linked_genres_clean[linked_genres_clean['IsMainGenre'] == 't']

# Voeg genre namen toe
linked_genres_with_names = linked_genres_clean.merge(
    genres_clean, on='GenreId', how='left'
)

# Groepeer genres per event (als een event meerdere main genres heeft)
main_genres_grouped = linked_genres_with_names.groupby('EventId')['GenreName'].agg(lambda x: ', '.join(x)).reset_index()
main_genres_grouped = main_genres_grouped.rename(columns={'GenreName': 'MainGenres'})

print(f" Events met main genres: {len(main_genres_grouped)}")

# DATA COMBINEREN

# 1. Voeg EventDetails toe aan Events
events_with_details = events_clean.merge(
    event_details_clean,
    on='EventId',
    how='left'
)

# 2. Voeg genres toe aan events
events_complete = events_with_details.merge(main_genres_grouped, on='EventId', how='left')

# --- FINALE DATASET ---
final_columns = [
    'EventId',
    'EventName',
    'OrganizerName',
    'DateTimeStart',
    'DateTimeEnd',
    'City',
    'Country',
    'StreetAddress',
    'OrganizerId',
    'PublicUserId',
    'EventType',
    'MainGenres'
]

existing_columns = [col for col in final_columns if col in events_complete.columns]
final_dataset = events_complete[existing_columns]

# DATA CLEANING
text_columns = ['MainGenres', 'EventType', 'StreetAddress']
for col in text_columns:
    if col in final_dataset.columns:
        final_dataset[col] = final_dataset[col].fillna('-')

# Verwijder duplicaten
before_dedup = len(final_dataset)
final_dataset = final_dataset.drop_duplicates(subset=['EventId'])

# OPSLAAN
output_folder = '/Users/djenna/Gigevate_project/cleaned-data'
os.makedirs(output_folder, exist_ok=True)

output_file = os.path.join(output_folder, 'events_combined.csv')
final_dataset.to_csv(output_file, index=False, encoding='utf-8')

print("\n")
print("Data is combined")
print(f"Output file: {output_file}")
print(f"Amount of events in file: {len(final_dataset)}")

print("\n columns in dataset:")
for i, col in enumerate(final_dataset.columns, 1):
    print(f"  {i}. {col}")

print("\n Eerste 5 events met genres:")
events_with_genres = final_dataset[final_dataset['MainGenres'] != '-'].head(5)
if len(events_with_genres) > 0:
    for _, row in events_with_genres.iterrows():
        print(f"  - {row['EventName']}: {row['MainGenres']}")
else:
    print("  Geen events met genres gevonden")