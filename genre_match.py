import pandas as pd
import os
import warnings
warnings.filterwarnings('ignore')

print("Recommendation Engine: Match Artists to Events based on Genres")

#Loading data
data_folder = '/Users/djenna/Gigevate_project/cleaned-data/'
output_folder = '/Users/djenna/Gigevate_project/outputs/'

artists = pd.read_csv(data_folder + 'artists_combined.csv')
events = pd.read_csv(data_folder + 'events_combined.csv')

# Only fill text columns, NOT numeric ones
artists['MainGenres'] = artists['MainGenres'].fillna('-')
artists['SubGenres'] = artists['SubGenres'].fillna('-')
artists['City'] = artists['City'].fillna('Unknown')

events['MainGenres'] = events['MainGenres'].fillna('-')
events['EventName'] = events['EventName'].fillna('Unknown')
events['OrganizerName'] = events['OrganizerName'].fillna('Unknown')
events['City'] = events['City'].fillna('Unknown')
events['DateTimeStart'] = events['DateTimeStart'].fillna('Unknown')

#Prepare artist data
artist_data = []
for idx, row in artists.iterrows():
    main_genres = []
    sub_genres = []
    
    if pd.notna(row['MainGenres']) and row['MainGenres'] != '-':
        main_genres = [g.strip() for g in row['MainGenres'].split(',')]
    
    if pd.notna(row['SubGenres']) and row['SubGenres'] != '-':
        sub_genres = [g.strip() for g in row['SubGenres'].split(',')]
    
    fee = row['AvgBookingFee'] if pd.notna(row['AvgBookingFee']) else None
    experience = row['YearsOfExperience'] if pd.notna(row['YearsOfExperience']) else None
    
    artist_data.append({
        'artist_id': row['ArtistId'],
        'artist_name': row['ArtistName'],
        'city': row['City'] if row['City'] != '-' else 'Unknown',
        'avg_booking_fee': fee,
        'years_experience': experience,
        'main_genres': main_genres,
        'sub_genres': sub_genres
    })

# Prepare event data
event_data = []
for idx, row in events.iterrows():
    main_genres = []
    
    if pd.notna(row['MainGenres']) and row['MainGenres'] != '-':
        main_genres = [g.strip() for g in row['MainGenres'].split(',')]
    
    event_data.append({
        'event_id': row['EventId'],
        'event_name': row['EventName'] if row['EventName'] != '-' else 'Unknown',
        'organizer': row['OrganizerName'] if row['OrganizerName'] != '-' else 'Unknown',
        'city': row['City'] if row['City'] != '-' else 'Unknown',
        'event_date': row['DateTimeStart'] if row['DateTimeStart'] != 'Unknown' else 'No date',
        'main_genres': main_genres
    })

#check if event has genres 
#calculate match score with artiest (1 for main genre match 0.5 for sub genre match, 0 for no match)
def calculate_match_score(artist, event):
    """
    Bereken match score tussen 0 en 1
    Main genre match = 1.0
    Sub genre match = 0.5
    Geen match = 0
    """
    if not event['main_genres']:
        return 0
    
    best_score = 0
    
    for event_genre in event['main_genres']:
        if event_genre in artist['main_genres']:
            best_score = max(best_score, 1.0)
        elif event_genre in artist['sub_genres']:
            best_score = max(best_score, 0.5)
    
    return best_score

def recommend_artists_for_event(event_id, top_n=10):
    #Find event (check if event exsists)
    event = next((e for e in event_data if e['event_id'] == event_id), None)
    if not event:
        print(f"Event with ID {event_id} not found")
        return None, []
    
    if not event['main_genres']:
        print(f"Event '{event['event_name']}' has no genres")
        return event, []
    
    #Calculate scores for all artists
    #Add scores higer than 0 to a list
    #the list then contains the dictionaries of the artists
    recommendations = []
    for artist in artist_data:
        score = calculate_match_score(artist, event)
        if score > 0:
            recommendations.append({
                'artist_id': artist['artist_id'],
                'artist_name': artist['artist_name'],
                'match_score': score,
                'artist_city': artist['city'],
                'artist_main_genres': ', '.join(artist['main_genres']) if artist['main_genres'] else '-',
                'artist_sub_genres': ', '.join(artist['sub_genres']) if artist['sub_genres'] else '-',
                'avg_booking_fee': artist['avg_booking_fee'],
                'years_experience': artist['years_experience']})
    
    #Sort by score (highest scorefirst)
    recommendations.sort(key=lambda x: x['match_score'], reverse=True)
    
    return event, recommendations[:top_n]

def search_event_by_name(search_term):
    search_term = search_term.lower()
    results = []
    for event in event_data:
        if search_term in event['event_name'].lower():
            results.append(event)
    return results

# Interactive loop
while True:
    print("1. Search event by name")
    print("2. Enter event ID directly")
    print("3. Quit")
    
    choice = input("Choose option (1-3): ")
    
    if choice == '3':
        print("Goodbye!")
        break
    
    elif choice == '1':
        search_term = input("Enter event name (or part of name): ")
        results = search_event_by_name(search_term)
        
        if not results:
            print(f"No events found with '{search_term}'")
            continue
        
        print(f"\nFound {len(results)} events:")
        for i, event in enumerate(results[:10], 1):
            genres = ', '.join(event['main_genres']) if event['main_genres'] else 'No genres'
            print(f"{i}. ID: {event['event_id']} - {event['event_name']} - {genres}")
        
        if len(results) > 10:
            print(f"... and {len(results) - 10} more")
        
        try:
            idx = int(input("\nSelect number from list (or 0 to cancel): "))
            if idx == 0:
                continue
            event = results[idx - 1]
            event_id = event['event_id']
        except (ValueError, IndexError):
            print("Invalid selection")
            continue
    
    elif choice == '2':
        try:
            event_id = int(input("Enter Event ID: "))
        except ValueError:
            print("Please enter a valid number")
            continue
    
    else:
        print("Invalid choice")
        continue
    
    # Get recommendations
    event, recommendations = recommend_artists_for_event(event_id, top_n=15)
    
    if not event:
        continue
    
    if not recommendations:
        print(f"\nNo matching artists found for event '{event['event_name']}'")
        continue
    
    # Print results
    print(f"\n")
    print(f"Event: {event['event_name']} (ID: {event['event_id']})")
    print(f"Event Genres: {', '.join(event['main_genres'])}")
    print(f"Location: {event['city']}")
    print(f"Organizer: {event['organizer']}")
    print(f"Date: {event['event_date']}")
    
    print("\nArtist Recommendations:")
    print("-" * 110)
    print(f"{'#':<3} {'Score':<8} {'Artist Name':<25} {'Main Genres':<20} {'Sub Genres':<20} {'Fee':<12} {'Exp':<6} {'City':<12}")
    print("-" * 110)
    
    for i, rec in enumerate(recommendations, 1):
        main_genres_display = rec['artist_main_genres'][:19] if len(rec['artist_main_genres']) > 19 else rec['artist_main_genres']
        sub_genres_display = rec['artist_sub_genres'][:19] if len(rec['artist_sub_genres']) > 19 else rec['artist_sub_genres']
        
        # Fee display
        if rec['avg_booking_fee'] is None or rec['avg_booking_fee'] == 0:
            fee_str = 'Unknown'
        else:
            fee_str = f"EUR {rec['avg_booking_fee']:.0f}"
        
        # Experience display
        if rec['years_experience'] is None:
            exp_str = '?'
        else:
            exp_str = f"{rec['years_experience']:.0f}"
        
        print(f"{i:<3} {rec['match_score']:<8.1f} {rec['artist_name']:<25} {main_genres_display:<20} {sub_genres_display:<20} {fee_str:<12} {exp_str:<6} {rec['artist_city']:<12}")
    
    print("\nLegend:")
    print("  Score 1.0 = Artist's MAIN genre matches event genre")
    print("  Score 0.5 = Artist's SUB genre matches event genre")
    print("  Fee = 'Unknown' means no booking fee data available")
    print("  Exp = Years of experience, '?' means unknown")
    
    # Option to save to file
    save = input("\nSave recommendations to CSV? (y/n): ")
    if save.lower() == 'y':
        export_df = pd.DataFrame([{
            'artist_id': r['artist_id'],
            'artist_name': r['artist_name'],
            'match_score': r['match_score'],
            'artist_main_genres': r['artist_main_genres'],
            'artist_sub_genres': r['artist_sub_genres'],
            'avg_booking_fee': r['avg_booking_fee'],
            'years_experience': r['years_experience'],
            'artist_city': r['artist_city']
        } for r in recommendations])
        
        output_file = os.path.join(output_folder, f'recommendations_event_{event_id}.csv')
        export_df.to_csv(output_file, index=False)
        print(f"Saved to {output_file}")