import pandas as pd
import glob
import os
import warnings
warnings.filterwarnings('ignore')


print("Combine csv data for artists")

# Load CSV files
print("\n loading files")
data_folder = '/Users/djenna/Gigevate_project/Gigevate-data (not cleaned)/gigevate-export/'


print("\n loading files")

artists = pd.read_csv(data_folder + 'Artists.csv')
print(f" * Artists: {len(artists)} rows")

currencies = pd.read_csv(data_folder + 'Currencies.csv')
print(f" * Currencies: {len(currencies)} rows")

genres = pd.read_csv(data_folder + 'Genres.csv')
print(f" * Genres: {len(genres)} rows")

countries = pd.read_csv(data_folder + 'Countries.csv')
print(f" * Countries: {len(countries)} rows")

bookings = pd.read_csv(data_folder + 'Bookings.csv')
print(f" * Bookings: {len(bookings)} rows")

linked_genres = pd.read_csv(data_folder + 'LinkedGenres.csv')
print(f" * LinkedGenres: {len(linked_genres)} rows")

artist_details = pd.read_csv(data_folder + 'ArtistDetails.csv')
print(f" * ArtistDetails: {len(artist_details)} rows")

# Rename some columns 

# Artists
artists_clean = artists[[
    'Id', 
    'StageName', 
    'City', 
    'Country', 
    'UserId', 
    'SpotifyURL']].copy()
artists_clean = artists_clean.rename(columns={
    'Id': 'ArtistId',
    'StageName': 'ArtistName'})

# Currencies
currencies_clean = currencies[[
    'Id', 
    'Name', 
    'Description']].copy()
currencies_clean = currencies_clean.rename(columns={
    'Id': 'CurrencyId',
    'Name': 'CurrencySymbol',
    'Description': 'CurrencyCode'})

# Genres
genres_clean = genres[[
    'Id', 
    'Name']].copy()
genres_clean = genres_clean.rename(columns={
    'Id': 'GenreId',
    'Name': 'GenreName'})

# Countries
countries_clean = countries[[
    'Id', 
    'Name', 
    'Code']].copy()
countries_clean = countries_clean.rename(columns={
    'Id': 'CountryId',
    'Name': 'CountryName',
    'Code': 'CountryCode'})

# Bookings
bookings_clean = bookings[[
    'ProposedBookingFee', 
    'ArtistId', 
    'CurrencyId']].copy()

# LinkedGenres
linked_genres_clean = linked_genres[[
    'ArtistId', 
    'GenreId', 
    'IsMainGenre']].copy()
# Converteer IsMainGenre naar boolean (True/False)
linked_genres_clean['IsMainGenre'] = linked_genres_clean['IsMainGenre'].map({'t': True, 'f': False})

# ArtistDetails
artist_details_clean = artist_details[[
    'ArtistId', 
    'StageName',
    'CurrentLocation', 
    'YearsOfExperience', 
    'CurrencyId', 
    'HourlyFeeRange'
]].copy()
artist_details_clean = artist_details_clean.rename(columns={
    'StageName': 'ArtistName_Details'})

# DATA COMBINEREN

# 1. Voeg Country namen toe aan Artists
artists_with_country = artists_clean.merge(
    countries_clean,
    left_on='Country',
    right_on='CountryId',
    how='left')
# Verwijder de dubbele ID kolom
artists_with_country = artists_with_country.drop('CountryId', axis=1)

# 2. Voeg ArtistDetails toe aan Artists
artists_complete = artists_with_country.merge(
    artist_details_clean,
    on='ArtistId',
    how='left')

# 3. Voeg Genres toe 
# Splits main genres en sub genres apart
main_genres = linked_genres_clean[linked_genres_clean['IsMainGenre'] == True].merge(
    genres_clean, on='GenreId', how='left')
sub_genres = linked_genres_clean[linked_genres_clean['IsMainGenre'] == False].merge(
    genres_clean, on='GenreId', how='left')

# Groepeer genres per artiest
main_genres_grouped = main_genres.groupby('ArtistId')['GenreName'].agg(lambda x: ', '.join(x)).reset_index()
main_genres_grouped = main_genres_grouped.rename(columns={'GenreName': 'MainGenres'})

sub_genres_grouped = sub_genres.groupby('ArtistId')['GenreName'].agg(lambda x: ', '.join(x)).reset_index()
sub_genres_grouped = sub_genres_grouped.rename(columns={'GenreName': 'SubGenres'})

# Voeg genres toe aan artists
artists_complete = artists_complete.merge(main_genres_grouped, on='ArtistId', how='left')
artists_complete = artists_complete.merge(sub_genres_grouped, on='ArtistId', how='left')

# 4. Voeg Bookings toe 
# Bereken gemiddelde, minimum en maximum booking fee per artiest
booking_stats = bookings_clean.groupby('ArtistId').agg({
    'ProposedBookingFee': ['mean', 'min', 'max', 'count']
}).reset_index()
booking_stats.columns = ['ArtistId', 'AvgBookingFee', 'MinBookingFee', 'MaxBookingFee', 'NumberOfBookings']

# Voeg valuta info toe aan bookings (meest voorkomende valuta per artiest)
most_common_currency = bookings_clean.groupby('ArtistId')['CurrencyId'].agg(
    lambda x: x.mode().iloc[0] if not x.mode().empty else None
).reset_index()
most_common_currency.columns = ['ArtistId', 'MostUsedCurrencyId']

# Voeg valuta naam toe
most_common_currency = most_common_currency.merge(
    currencies_clean, left_on='MostUsedCurrencyId', right_on='CurrencyId', how='left'
)
most_common_currency = most_common_currency[['ArtistId', 'CurrencySymbol', 'CurrencyCode']]

# Voeg alles toe aan artists
artists_complete = artists_complete.merge(booking_stats, on='ArtistId', how='left')
artists_complete = artists_complete.merge(most_common_currency, on='ArtistId', how='left')


# --- FINALE DATASET ---
# Selecteer de uiteindelijke kolommen in logische volgorde
final_columns = [
    'ArtistId',
    'ArtistName',
    'City',
    'CountryName',
    'CountryCode',
    'UserId',
    'SpotifyURL',
    'CurrentLocation',
    'YearsOfExperience',
    'HourlyFeeRange',
    'MainGenres',
    'SubGenres',
    'AvgBookingFee',
    'MinBookingFee',
    'MaxBookingFee',
    'NumberOfBookings',
    'CurrencySymbol',
    'CurrencyCode']

# Alleen kolommen die bestaan toevoegen
existing_columns = [col for col in final_columns if col in artists_complete.columns]
final_dataset = artists_complete[existing_columns]

# DATA CLEANING 
# Vervang NaN waarden door '-' voor tekst kolommen
text_columns = ['MainGenres', 'SubGenres', 'CurrentLocation', 'HourlyFeeRange']
for col in text_columns:
    if col in final_dataset.columns:
        final_dataset[col] = final_dataset[col].fillna('-')

# Doe NaN bij deze colommen want anders lijkt het alsof een artiest 0 euro kost om te boeken
# Alleen de booking fees mogen NaN blijven (geen data = geen fee)
booking_fee_columns = ['AvgBookingFee', 'MinBookingFee', 'MaxBookingFee']
for col in booking_fee_columns:
    if col in final_dataset.columns:
        final_dataset[col] = final_dataset[col].fillna(pd.NA)

# YearsOfExperience en NumberOfBookings kunnen gewoon 0 zijn
if 'YearsOfExperience' in final_dataset.columns:
    final_dataset['YearsOfExperience'] = final_dataset['YearsOfExperience'].fillna(0)
    
if 'NumberOfBookings' in final_dataset.columns:
    final_dataset['NumberOfBookings'] = final_dataset['NumberOfBookings'].fillna(0)

# Verwijder complete duplicates
before_dedup = len(final_dataset)
final_dataset = final_dataset.drop_duplicates(subset=['ArtistId'])

# OPSLAAN
output_file = '/Users/djenna/Gigevate_project/cleaned-data/artists_combined.csv'
final_dataset.to_csv(output_file, index=False, encoding='utf-8')

print("\n")
print("Data is combined")
print(f"Output file: {output_file}")
print(f"Amount of artists in file: {len(final_dataset)}")

print("\n columns in dataset:")
for i, col in enumerate(final_dataset.columns, 1):
    print(f"  {i}. {col}")