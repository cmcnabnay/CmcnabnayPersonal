import googlemaps
import pandas as pd
from urllib.parse import urlparse, unquote
from datetime import datetime, timedelta
import os
import re

API_KEY = #[KEY]

def parse_google_maps_url(url):
    parsed_url = urlparse(url)
    waypoints = []
    coordinates = {}
    
    if parsed_url.path.startswith('/maps/dir/'):
        path_segments = parsed_url.path.split('/')[3:]
        
        for segment in path_segments:
            decoded_segment = unquote(segment.replace('+', ' '))
            if decoded_segment.startswith('@'):
                break  # Stop processing waypoints once '@' is encountered
            if not decoded_segment.startswith('data='):
                waypoints.append(decoded_segment)
                
        for segment in path_segments:
            if segment.startswith('data'):
                coords_info = segment.split('!2m2!1d')
                coords_list = []

                for item in coords_info[1:]:  # Skip the first part as it's not needed
                    parts = item.split('!')
                    if len(parts) > 1:
                        longitude = float(parts[0])
                        latitude = float(parts[1].split('2d')[-1])
                        coords_list.append((latitude, longitude))

                if coords_list:  # Add the coordinates to the dictionary
                    for i in range(min(len(waypoints), len(coords_list))):
                        coordinates[waypoints[i]] = coords_list[i]

    return waypoints, coordinates

def get_address_from_coordinates(gmaps, coordinates):
    addresses = {}
    for waypoint, coords in coordinates.items():
        reverse_geocode_result = gmaps.reverse_geocode(coords)
        if reverse_geocode_result:
            addresses[waypoint] = reverse_geocode_result[0]['formatted_address']
        else:
            addresses[waypoint] = None
    return addresses

def load_stops_from_excel(file_path):
    df = pd.read_excel(file_path)
    stops = df['Address'].tolist()
    return stops

def strip_address_details(address):
    replacements = {
        'Road': 'Rd','Avenue': 'Ave','Street': 'St','Drive': 'Dr','Boulevard': 'Blvd','Northeast': 'NE','Northwest': 'NW','Southeast': 'SE','Southwest': 'SW',
    }

    # Replace full words with abbreviations
    for full_word, abbreviation in replacements.items():
        address = re.sub(r'\b{}\b'.format(full_word), abbreviation, address)

    # Split the address by commas and strip leading/trailing whitespace
    parts = [part.strip() for part in address.split(',')]
    # Remove the last part if it's a zip code (assumed to be a 5-digit number)
    if len(parts[-1]) == 5 and parts[-1].isdigit():
        parts.pop()
    # Join the remaining parts back into a single address
    stripped_address = ', '.join(parts)
    return stripped_address

def normalize_intersection(address):
    if '&' in address:
        parts = address.split('&')
        if len(parts) == 2:
            street1 = parts[0].strip()
            street2 = parts[1].strip()
            return (f"{street1} & {street2}", f"{street2} & {street1}")
    return (address, address)


def calculate_arrival_times(locations, addresses, stops, api_key):
    gmaps = googlemaps.Client(key=api_key)
    initial_departure_time = datetime.now().replace(hour=15, minute=0, second=0, microsecond=0)

    if initial_departure_time <= datetime.now():
        initial_departure_time += timedelta(days=1)

    departure_time = initial_departure_time
    accumulated_duration_seconds = 0

    idx = 0
    while idx < len(locations) - 1:
        start = locations[idx]
        end = locations[idx + 1]

        if '&' in start:
            start = strip_address_details(start)
            start_variants = normalize_intersection(strip_address_details(start))
            for addr in stops:
                for variant in start_variants:
                    if strip_address_details(addr) in variant or variant in strip_address_details(addr):
                        start = addr
        else:
            start = addresses.get(start, start)

        if '&' in end:
            end = strip_address_details(end)
            end_variants = normalize_intersection(strip_address_details(end))
            for addr in stops:
                for variant in end_variants:
                    if strip_address_details(addr) in variant or variant in strip_address_details(addr):
                        end = addr
        else:
            end = addresses.get(end, end)

        print(f"start: {start}")
        print(f"end: {end}")

        try:
            directions = gmaps.directions(start, end, departure_time=departure_time)

            if directions:
                route = directions[0]['legs'][0]
                duration_seconds = route['duration']['value']
                arrival_time = departure_time + timedelta(seconds=duration_seconds)

                is_start_stop = any(strip_address_details(addr) in start or start in strip_address_details(addr) for addr in stops)
                is_end_stop = any(strip_address_details(addr) in end or end in strip_address_details(addr) for addr in stops)

                if is_start_stop and is_end_stop:
                    print(f"From {locations[idx]} to {locations[idx + 1]}:")
                    print(f"   - Duration: {timedelta(seconds=duration_seconds)}")
                    print(f"   - Estimated Arrival Time: {arrival_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"   - Estimated Departure Time: {(arrival_time + timedelta(minutes=2)).strftime('%Y-%m-%d %H:%M:%S')}")
                    print()
                    departure_time = arrival_time + timedelta(minutes=2)
                    idx += 1  
                elif is_start_stop:
                    start_to_intermediate_duration = duration_seconds
                    print(f"start_to_intermediate_duration: {start_to_intermediate_duration}")
                    departure_time = arrival_time
                    idx += 1
                elif is_end_stop:
                    intermediate_to_end_duration = duration_seconds
                    print(f"From {locations[idx - 1]} to {locations[idx + 1]}:")
                    duration = start_to_intermediate_duration+intermediate_to_end_duration
                    print(f"   - Duration: {timedelta(seconds=(duration))}")
                    print(f"   - Estimated Arrival Time: {arrival_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"   - Estimated Departure Time: {(arrival_time + timedelta(minutes=2)).strftime('%Y-%m-%d %H:%M:%S')}")
                    print()
                    departure_time = arrival_time + timedelta(minutes=2)
                    idx += 1  # Move to the next stop pair
                else:
                    idx += 1 
                    departure_time = arrival_time  # Update departure time for the next leg

            else:
                print(f"No directions found from {start} to {end}.")

        except googlemaps.exceptions.ApiError as e:
            print(f"Error fetching directions from {start} to {end}: {e}")

    print("Reached the end of locations.")



if __name__ == "__main__":
    google_maps_url = 
    stops_file_path = os.path.join(os.getcwd(), 'Stops.xlsx')

    gmaps = googlemaps.Client(key=API_KEY)
    locations, coordinates = parse_google_maps_url(google_maps_url)
    print(f"coordinates: {coordinates}")
    print(f"locations: {locations}")

    stops = load_stops_from_excel(stops_file_path)

    if coordinates:
        addresses = get_address_from_coordinates(gmaps, coordinates)
        print(f"addresses: {addresses}")
        calculate_arrival_times(locations, addresses, stops, API_KEY)
    else:
        print("No valid coordinates found in the provided Google Maps URL.")
