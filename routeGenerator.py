import pandas as pd
import os
import requests
import webbrowser
from sklearn.cluster import KMeans
import googlemaps

# Replace with your Google Maps API key
GOOGLE_MAPS_API_KEY = "AIzaSyDUZVelPmEmOGYeOWRaiy4dVCt-gLnEgWY"

FINAL_DESTINATION = "St Mary Catholic Central Monroe, MI"
SPECIAL_ADDRESS_1 = "11251 Harold Drive Luna Pier MI 48157"
SPECIAL_ADDRESS_2 = "12276 Laginess Rd LaSalle, MI 48145"
REPLACEMENT_ADDRESS_1 = "2621 Deborah Dr Monroe, MI 48162"
REPLACEMENT_ADDRESS_2 = "14495 S. Telegraph Rd. Monroe MI 48133"
SPECIAL_ADDRESS = "9956 Strasburg Rd. Erie MI 48133"

def geocode_address(address):
    base_url = 'https://maps.googleapis.com/maps/api/geocode/json'
    params = {
        'address': address,
        'key': GOOGLE_MAPS_API_KEY
    }
    try:
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'OK':
                location = data['results'][0]['geometry']['location']
                return (location['lat'], location['lng'])
            else:
                print(f"Failed to geocode address '{address}'. Status: {data['status']}")
        else:
            print(f"Failed to geocode address '{address}'. Status code: {response.status_code}")
    except Exception as e:
        print(f"Exception occurred while geocoding address '{address}': {str(e)}")
    return None

def read_addresses(file_path):
    addressesAM = {}
    addressesPM = {}

    df = pd.read_excel(file_path, dtype=str)
    address_column = df['Address']
    ridership_column = df['Ridership Option']
    print(ridership_column)

    for address, ridership in zip(address_column, ridership_column):
        if "Both" in ridership:
            if "*DIFFERENT ADDRESS FOR DROP OFF BELOW*" in address:
                address = REPLACEMENT_ADDRESS_1
            elif address.strip() == SPECIAL_ADDRESS:
                address = REPLACEMENT_ADDRESS_2
            elif " and " in address:
                split_addresses = address.split(" and ")
                for addr in split_addresses:
                    addressesAM[addr] = addressesAM.get(addr, 0) + 1
                    addressesPM[addr] = addressesPM.get(addr, 0) + 1
                continue
            addressesAM[address] = addressesAM.get(address, 0) + 1
            addressesPM[address] = addressesPM.get(address, 0) + 1

        elif "AM Only" in ridership:
            if "*DIFFERENT ADDRESS FOR DROP OFF BELOW*" in address:
                address = REPLACEMENT_ADDRESS_1
            elif address.strip() == SPECIAL_ADDRESS:
                address = REPLACEMENT_ADDRESS_2
            elif " and " in address:
                split_addresses = address.split(" and ")
                for addr in split_addresses:
                    addressesAM[addr] = addressesAM.get(addr, 0) + 1
                continue
            addressesAM[address] = addressesAM.get(address, 0) + 1

        elif "PM Only" or "PM only" in ridership:
            if "5518 Wimbledon Park" in address:
                address = REPLACEMENT_ADDRESS_1
            elif address.strip() == SPECIAL_ADDRESS:
                address = REPLACEMENT_ADDRESS_2
            elif " and " in address:
                split_addresses = address.split(" and ")
                for addr in split_addresses:
                    addressesPM[addr] = addressesPM.get(addr, 0) + 1
                continue
            addressesPM[address] = addressesPM.get(address, 0) + 1

    # Ensure REPLACEMENT_ADDRESS_1 is included in addressesPM for "PM Only" ridership
    #addressesPM[REPLACEMENT_ADDRESS_1] = addressesPM.get(REPLACEMENT_ADDRESS_1, 0)

    return addressesAM, addressesPM


def geocode_addresses(addresses):
    coords = {}
    for address in addresses:
        location = geocode_address(address)
        if location:
            coords[address] = location
        else:
            print(f"Failed to geocode address '{address}' using Google Maps API.")
    return coords

def cluster_addresses(coords, addresses, num_clusters):
    max_passengers_per_route = 9
    coords_list = list(coords.values())
    if not coords_list:
        return [[]]

    kmeans = KMeans(n_clusters=num_clusters, random_state=0)
    labels = kmeans.fit_predict(coords_list)

    groups = [[] for _ in range(num_clusters)]
    passenger_count = [0] * num_clusters
    for i, label in enumerate(labels):
        address = list(coords.keys())[i]
        num_passengers = addresses[address]
        if passenger_count[label] + num_passengers <= max_passengers_per_route or passenger_count[label] == 0:
            groups[label].append(address)
            passenger_count[label] += num_passengers
        else:
            for j in range(num_clusters):
                if passenger_count[j] + num_passengers <= max_passengers_per_route:
                    groups[j].append(address)
                    passenger_count[j] += num_passengers
                    break
            else:
                groups[label].append(address)
                passenger_count[label] += num_passengers

    return groups

def calculate_travel_duration(origin, destination, gmaps):
    try:
        directions_result = gmaps.directions(origin, destination, mode="driving", departure_time="now")
        if directions_result:
            route = directions_result[0]
            return route['legs'][0]['duration']['value']  # Duration in seconds
        else:
            print(f"Failed to get directions from {origin} to {destination}")
            return float('inf')  # Return a very large number indicating failure
    except Exception as e:
        print(f"Exception occurred while calculating duration from {origin} to {destination}")
        print(e)
        return float('inf') 

def optimize_route_order_am(addresses, gmaps):
    if not addresses:
        return []

    addresses.append(FINAL_DESTINATION)
    
    start = max(addresses[:-1], key=lambda addr: calculate_travel_duration(addr, FINAL_DESTINATION, gmaps))
    unvisited = set(addresses) - {start, FINAL_DESTINATION}
    route = [start]

    while unvisited:
        last = route[-1]
        nearest = min(unvisited, key=lambda addr: calculate_travel_duration(last, addr, gmaps))
        route.append(nearest)
        unvisited.remove(nearest)

    route.append(FINAL_DESTINATION)
    return route

def optimize_route_order_pm(addresses, gmaps):
    if not addresses:
        return []

    addresses.insert(0, FINAL_DESTINATION)
    
    unvisited = set(addresses) - {FINAL_DESTINATION}
    route = [FINAL_DESTINATION]

    while unvisited:
        last = route[-1]
        nearest = min(unvisited, key=lambda addr: calculate_travel_duration(last, addr, gmaps))
        route.append(nearest)
        unvisited.remove(nearest)

    return route

def create_google_maps_url(address_group):
    base_url = "https://www.google.com/maps/dir/"
    addresses_str = '/'.join(address.replace(' ', '+') for address in address_group)
    url = f"{base_url}{addresses_str}"
    return url

def main():
    file_path = os.path.join(os.getcwd(), 'Transportation Rosters', 'Transportation 2024-25 (Responses).xlsx')
    
    addresses_am, addresses_pm = read_addresses(file_path)
    print(f"addresses AM: {addresses_am}")
    print(f"addresses PM: {addresses_pm}")

    coords_am = geocode_addresses(addresses_am)
    coords_pm = geocode_addresses(addresses_pm)
    
    address_groups_am = cluster_addresses(coords_am, addresses_am, num_clusters=4)
    address_groups_pm = cluster_addresses(coords_pm, addresses_pm, num_clusters=5)
    
    gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

    def process_groups(groups, gmaps, am_pm):
        optimized_routes = []
        variations = []

        for group in groups:
            if am_pm == "AM":
                if SPECIAL_ADDRESS_1 in group and SPECIAL_ADDRESS_2 in group:
                    group1 = [addr for addr in group if addr != SPECIAL_ADDRESS_2]
                    group2 = [addr for addr in group if addr != SPECIAL_ADDRESS_1]
                    variations.append((group1, group2))
                    optimized_routes.append(optimize_route_order_am(group1, gmaps))
                    optimized_routes.append(optimize_route_order_am(group2, gmaps))
                else:
                    optimized_routes.append(optimize_route_order_am(group, gmaps))

                if REPLACEMENT_ADDRESS_1 in group:
                    group1 = [addr for addr in group if addr != REPLACEMENT_ADDRESS_1]
                    variations.append((group1, group))
                    optimized_routes.append(optimize_route_order_am(group1, gmaps))
                    optimized_routes.append(optimize_route_order_am(group, gmaps))

            else:  # PM routes
                if SPECIAL_ADDRESS_1 in group and SPECIAL_ADDRESS_2 in group:
                    group1 = [addr for addr in group if addr != SPECIAL_ADDRESS_2]
                    group2 = [addr for addr in group if addr != SPECIAL_ADDRESS_1]
                    variations.append((group1, group2))
                    optimized_routes.append(optimize_route_order_pm(group1, gmaps))
                    optimized_routes.append(optimize_route_order_pm(group2, gmaps))

                elif REPLACEMENT_ADDRESS_1 in group:
                    group1 = [addr for addr in group if addr != REPLACEMENT_ADDRESS_1]
                    variations.append((group1, group))
                    optimized_routes.append(optimize_route_order_pm(group1, gmaps))
                    optimized_routes.append(optimize_route_order_pm(group, gmaps))

                else:
                    optimized_routes.append(optimize_route_order_pm(group, gmaps))


        return optimized_routes, variations

    optimized_order_am, variations_am = process_groups(address_groups_am, gmaps, "AM")
    print(f"variations am {variations_am}")
    optimized_order_pm, variations_pm = process_groups(address_groups_pm, gmaps, "PM")
    print(f"variations pm {variations_pm}")

    maps_urls_am = [create_google_maps_url(group) for group in optimized_order_am]
    maps_urls_pm = [create_google_maps_url(group) for group in optimized_order_pm]

    def name_routes(maps_urls, variations, am_pm):
        route_names = []
        route_count = 0  # Initialize route count
        
        for i, url in enumerate(maps_urls):
            route_number = (route_count) + 1
            
            if variations and i < len(variations) * 2:
                variation_index = i % len(variations)
                if len(variations[variation_index]) > 1:
                    variation_number = (i % 2) + 1
                    route_name = f"Route {route_number} ({variation_number}) {am_pm}"
                else:
                    route_name = f"Route {route_number} {am_pm}"
            else:
                route_name = f"Route {route_number} {am_pm}"
            
            route_names.append((route_name, url))
            route_count += 1
        
        return route_names

    named_routes_am = name_routes(maps_urls_am, variations_am, "AM")
    named_routes_pm = name_routes(maps_urls_pm, variations_pm, "PM")

    for route_name, url in named_routes_am:
        print(f"{route_name}: {url}")
        #webbrowser.open_new_tab(url)

    for route_name, url in named_routes_pm:
        print(f"{route_name}: {url}")
        #webbrowser.open_new_tab(url)

if __name__ == "__main__":
    main()
