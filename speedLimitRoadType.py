import requests
import pandas as pd
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from rapidfuzz import fuzz
import json
import os
from functools import partial
import sys

# Define bounding box coordinates
bounding_box_1 = (42.570376, -86.372750, 43.265014, -85.287797)
bounding_box_2 = (41.743673, -83.807512, 42.313228, -83.18)

# Google Maps Geocoding API key
google_api_key = "AIzaSyDUZVelPmEmOGYeOWRaiy4dVCt-gLnEgWY"

# Directional and suffix dictionaries for normalization
directional_dict = {
    'north': 'n', 'south': 's', 'east': 'e', 'west': 'w',
    'northeast': 'ne', 'northwest': 'nw', 'southeast': 'se', 'southwest': 'sw'
}

# Updated street suffixes with common abbreviations and expansions
street_suffixes = {
    'drive': 'dr', 'court': 'ct', 'street': 'st', 'road': 'rd', 'avenue': 'ave', 'boulevard': 'blvd',
    'lane': 'ln', 'terrace': 'ter', 'place': 'pl', 'circle': 'cir', 'trail': 'trl', 'way': 'way'
}

# Function to normalize street names
def normalize_street_name(street_name):
    street_name = street_name.lower()
    street_name = re.sub(r'[^\w\s]', '', street_name)  # Remove punctuation
    street_name = re.sub(r'\s+', ' ', street_name).strip()  # Normalize whitespace
    
    # Replace full suffixes with abbreviations
    for full, abbr in street_suffixes.items():
        street_name = re.sub(rf'\b{full}\b', abbr, street_name)
    
    # Replace directional full names with abbreviations
    for full, abbr in directional_dict.items():
        street_name = re.sub(rf'\b{full}\b', abbr, street_name)
    
    return street_name.strip()

# Function to read addresses from multiple Excel files
def read_addresses_from_excels(files):
    addresses = []
    replacement_address_1 = "2621 Deborah Dr Monroe, MI 48162"
    replacement_address_2 = "14495 S. Telegraph Rd. Monroe MI 48133"
    special_address = "9956 Strasburg Rd. Erie MI 48133"
    
    for file in files:
        df = pd.read_excel(file)
        if "2024-25 Transportation Roster" in df.columns:
            address_column = df.apply(lambda row: f"{row['Address']}, {row['City']}, {row['State']}", axis=1)
        else:
            address_column = df['Address']
        
        for address in address_column:
            # Check for special conditions and handle them
            if "*DIFFERENT ADDRESS FOR DROP OFF BELOW*" in address:
                addresses.append(replacement_address_1)
            elif address.strip() == special_address:
                addresses.append(replacement_address_2)
            elif " and " in address:
                split_addresses = address.split(" and ")
                addresses.extend(split_addresses)
            else:
                addresses.append(address)
                
    return addresses

# Function to get geographical coordinates using Google Maps Geocoding API
def get_geocode(address):
    geocoding_api_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": google_api_key}
    response = requests.get(geocoding_api_url, params=params)
    data = response.json()

    if data["status"] == "OK":
        location = data["results"][0]["geometry"]["location"]
        return location["lat"], location["lng"]
    return None, None

# Function to get street name using Google Maps Geocoding API
def get_street_name(address):
    geocoding_api_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": google_api_key}
    response = requests.get(geocoding_api_url, params=params)
    data = response.json()
    
    if data["status"] == "OK":
        for component in data["results"][0]["address_components"]:
            types = component["types"]
            if "route" in types:
                return component["long_name"]
            elif "intersection" in types:
                # Handle intersection case: extract the first street name
                intersection_name = component["long_name"]
                streets = intersection_name.split(" & ")
                
                # Normalize street names
                normalized_streets = [normalize_street_name(street) for street in streets]
                
                # Get the first street from the address format in Excel sheet and normalize it
                original_streets = address.split(",")[0].split(" & ")
                normalized_original_streets = [normalize_street_name(street) for street in original_streets]
                
                # Compare both possible orders
                if normalized_streets[0] == normalized_original_streets[0]:
                    return streets[0]
                elif normalized_streets[1] == normalized_original_streets[0]:
                    return streets[1]
                
                # Default to the first street in the intersection_name
                return streets[0]
    return None

def find_node_by_id(node_id, nodes_dict):
    return nodes_dict.get(node_id)

def get_best_match(osm_data, normalized_street_name):
    best_score = 0
    best_osm_street_name = ""
    for element in osm_data['elements']:
        if 'tags' in element and 'name' in element['tags']:
            osm_street_name = element['tags']['name']
            normalized_osm_street_name = normalize_street_name(osm_street_name)
            score = fuzz.ratio(normalized_osm_street_name, normalized_street_name)
            if score > best_score:
                best_score = score
                best_osm_street_name = osm_street_name
    return best_osm_street_name

# Function to get maxspeed and road type using OpenStreetMap Overpass API
def get_osm_data(bounding_box_1, bounding_box_2):
    def fetch_data(bounding_box):
        overpass_url = "http://overpass-api.de/api/interpreter"
        overpass_query = f"""
        [out:json];
        way({bounding_box[0]},{bounding_box[1]},{bounding_box[2]},{bounding_box[3]});
        out body;
        >;
        out skel qt;
        """
        response = requests.get(overpass_url, params={'data': overpass_query})
        return response.json()
    
    data_1 = fetch_data(bounding_box_1)
    data_2 = fetch_data(bounding_box_2)
    
    return {'bounding_box_1': data_1, 'bounding_box_2': data_2}

def match_street_data(street_name, osm_data, lat, lng):
    min_diff = float('inf')
    result = None
    
    # Determine which bounding box to use based on lat and lng
    if (bounding_box_1[0] < lat < bounding_box_1[2] and bounding_box_1[1] < lng < bounding_box_1[3]):
        data_to_use = osm_data['bounding_box_1']
    elif (bounding_box_2[0] < lat < bounding_box_2[2] and bounding_box_2[1] < lng < bounding_box_2[3]):
        data_to_use = osm_data['bounding_box_2']

    normalized_street_name = normalize_street_name(street_name)
    print(f"normalized street name: {normalized_street_name}")
    best_match = get_best_match(data_to_use, normalized_street_name)
    print(f"best match: {best_match}")
    
    normalized_best_match = None
    if best_match == "Alberta Drive":
        normalized_best_match = "baretta"
    elif best_match == "Aten Road":
        normalized_best_match = "alt rd"
    elif best_match == "Pine Ridge Road":
        normalized_best_match = "south point ridge"
    elif best_match == "Applewood Drive Northeast":
        normalized_best_match = "applewood dr"
    elif best_match == "Ranger Drive":
        normalized_best_match = "tanager"
    else:
        normalized_best_match = normalize_street_name(best_match)

    nodes_dict = {element['id']: element for element in data_to_use['elements'] if element['type'] == 'node'}
    
    for element in data_to_use['elements']:
        if 'tags' in element and 'name' in element['tags']:
            osm_street_name = element['tags']['name']
            normalized_osm_street_name = normalize_street_name(osm_street_name)
            
            if normalized_best_match == "south pointe ridge":
                maxspeed = "Unknown"
                road_type = "unclassified"
                osm_street_name = "South Point Ridge"
                result = (maxspeed, road_type, osm_street_name, "N/A")
            
            if normalized_osm_street_name == normalized_street_name or normalized_osm_street_name == normalized_best_match:
                #print(f"normalized osm street name: {normalized_osm_street_name}")
                if 'nodes' in element:
                    for node_id in element['nodes']:
                        node = find_node_by_id(node_id, nodes_dict)
                        if node:
                            node_lat = node['lat']
                            diff_lat = abs(node_lat - lat)
                            node_lon = node['lon']
                            diff_lon = abs(node_lon - lng)
                            total_diff = diff_lat + diff_lon

                            if total_diff < min_diff:
                                min_diff = total_diff
                                maxspeed = element['tags'].get('maxspeed', 'Unknown')
                                road_type = element['tags'].get('highway', 'Unknown')
                                result = (maxspeed, road_type, osm_street_name, min_diff)

                        if min_diff > .05:
                            if normalized_osm_street_name == "marion dr":
                                maxspeed  = "Unknown"
                                road_type = "residential"
                                osm_street_name = "Special Case"
                            else:
                                maxspeed = "road not found"
                                road_type = "road not found"
                            result = (maxspeed, road_type, osm_street_name, min_diff)

                        print(f"Min Diff: {min_diff}")

    return result if result else ('Unknown', 'Unknown', 'Unknown', 'Unknown')

def load_addresses_from_excel():
    path = os.getcwd()
    #Read addresses from excel file
    stops_file = [os.path.join(path, 'Stops.xlsx')]  
    #stops_file = [os.path.join(os.getcwd(), 'Transportation Rosters', 'Test.xlsx')]
    addresses = read_addresses_from_excels(stops_file)
    print(f"Addresses read from Excel files: {addresses}")
    return addresses

def load_address_from_input():
    # Manual entry of multiple addresses
    addresses = []
    while True:
        manual_address = input("Enter address (or type 'done' to finish): ")
        if manual_address.lower() == 'done':
            break
        addresses.append(manual_address)
    print(f"Addresses input: {addresses}")
    return addresses

def main():
    addresses_from_loadStops = sys.argv[1:]
    if addresses_from_loadStops:
        addresses = addresses_from_loadStops
    else:
        addresses_source = input("Enter 'excel' to load from Excel, 'input' for manual input: ")
        if addresses_source == 'excel':
            addresses = load_addresses_from_excel()
        elif addresses_source == 'input':
            addresses = load_address_from_input()
        else:
            raise ValueError("Invalid input source specified.")
        
    
    # Assuming bounding_box_1 and bounding_box_2 are defined somewhere
    
    osm_data = get_osm_data(bounding_box_1, bounding_box_2)
    
    results = []
    filtered_results = []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit tasks for geocoding each address
        future_to_address = {executor.submit(get_geocode, address): address for address in addresses}
        
        for future in as_completed(future_to_address):
            address = future_to_address[future]
            try:
                lat, lng = future.result()
                print(f"{address}: lat={lat}, lng={lng}")
                
                if lat and lng:
                    street_name = get_street_name(address)
                    print(f"street name: {street_name}")
                    
                    if street_name:
                        maxspeed, road_type, normalized_osm, min_diff = match_street_data(street_name, osm_data, lat, lng)
                        results.append((address, normalized_osm, maxspeed, road_type, min_diff))
                        
                        if maxspeed != 'Unknown':
                            try:
                                if int(maxspeed) > 25:
                                    filtered_results.append((address, street_name, maxspeed, road_type))
                            except ValueError:
                                pass  # Ignore if maxspeed is not a number
                        
                        if road_type != 'residential':
                            filtered_results.append((address, street_name, maxspeed, road_type))
                    else:
                        results.append((address, 'Street name not found', 'Unknown', 'Unknown', 'N/A'))
                else:
                    results.append((address, 'Geocode not found', 'Unknown', 'Unknown', 'N/A'))
            
            except Exception as e:
                print(f"Error processing address {address}: {e}")
                results.append((address, 'Error', 'Unknown', 'Unknown', 'N/A'))
    
    # Print results for debugging or further processing
    for result in results:
        print(f"Address: {result[0]}, OSM Street Name: {result[1]}, Maxspeed: {result[2]}, Road Type: {result[3]}, Difference: {result[4]}")

    results_df = pd.DataFrame(results, columns=['Address', 'OSM Street Name', 'Maxspeed', 'Road Type', 'Difference'])
    results_df.to_excel('stop_speedLimit_roadType_results.xlsx', index=False)
    print("All results saved to stop_speedLimit_roadType_results.xlsx")

    # Save filtered results to CSV
    filtered_df = pd.DataFrame(filtered_results, columns=['Address', 'Street Name', 'Maxspeed', 'Road Type'])
    filtered_df.to_excel('stops_for_review.xlsx', index=False)
    print("Filtered results saved to filtered_addresses")

# Run the main function
if __name__ == "__main__":
    main()
