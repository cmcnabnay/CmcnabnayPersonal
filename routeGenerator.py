import pandas as pd
import os
import requests
import webbrowser
from sklearn.cluster import KMeans
import googlemaps

# Replace with your Google Maps API key
GOOGLE_MAPS_API_KEY = #[KEY]

FINAL_DESTINATION = "St Mary Catholic Central Monroe, MI"
SPECIAL_ADDRESS_1 = 
SPECIAL_ADDRESS_2 = 
REPLACEMENT_ADDRESS_1 = 
REPLACEMENT_ADDRESS_2 = 
SPECIAL_ADDRESS = 

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
in group if addr != REPLACEMENT_ADDRESS_1]
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
