import pandas as pd
import json
from supabase import create_client, Client
import os
import uuid  # Import the uuid module

# Initialize Supabase client
url = 'https://xrbfefmwiymnnpujtcbg.supabase.co'
key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhyYmZlZm13aXltbm5wdWp0Y2JnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTY3NTk5MDM1OSwiZXhwIjoxOTkxNTY2MzU5fQ.OfjHIGQLNhkad_w6g2h4IjoK3t_xbKqa6KGKEBwjmOQ'
supabase: Client = create_client(url, key)

# Fetch IDs from profiles table
profiles = supabase.table('profiles').select('*').execute().data
profiles_df = pd.DataFrame(profiles)

locations = supabase.table('locations').select('*').execute().data
locations_df = pd.DataFrame(locations)

vehicles = supabase.table('vehicles').select('*').execute().data
vehicles_df = pd.DataFrame(vehicles)

# Fetch organization data from Supabase
organizations = supabase.table('organizations').select('*').execute().data
organizations_df = pd.DataFrame(organizations)

# Read the Excel file
file_name = 'Driver Information (Responses).xlsx'
current_directory = os.getcwd()
file_path = os.path.join(current_directory, file_name)
df = pd.read_excel(file_path)

print("Columns in the Excel file:")
print(df.columns)

# Function to fetch vehicle ID based on description and school district
def get_vehicle_id(vehicle_description, vehicles, school_district):
    if pd.isnull(vehicle_description):
        return None
    
    if school_district == 'Grand Rapids Catholic':
        mapped_description = f'GRC {vehicle_description}'
    elif school_district == "St Mary's Catholic Central":
        mapped_description = f'SMCC {vehicle_description}'
    else:
        mapped_description = vehicle_description
    
    # Find the vehicle in the vehicles table
    matching_vehicle = vehicles[vehicles['description'] == mapped_description]
    if not matching_vehicle.empty:
        return int(matching_vehicle.iloc[0]['id'])
    
    return None

# Function to fetch location ID based on description
def get_location_id(location_name, locations):
    if pd.isnull(location_name):
        return None
    matching_route = locations[locations['description'] == location_name]
    if not matching_route.empty:
        return int(matching_route.iloc[0]['id'])
    return None

def get_organization_id(organization_name, organization_mapping):
    return organization_mapping.get(organization_name, None)

organization_mapping = {row['organization_name']: row['id'] for _, row in organizations_df.iterrows()}

def get_user_id(driver_name, profiles_df):
    if pd.isnull(driver_name):
        return None
    
    # Create a full name column
    profiles_df['full_name'] = profiles_df['fname'] + ' ' + profiles_df['lname']
    
    # Filter the DataFrame for matching full name
    matching_profiles = profiles_df[profiles_df['full_name'] == driver_name]
    
    if matching_profiles.empty:
        print(f"No matching profile found for driver name: {driver_name}")
        return None
    
    for index, profile in matching_profiles.iterrows():
        if "driver" in profile['roles']:
            return profile['user_id']
    
    print(f"No 'driver' role found for driver name: {driver_name}")
    return None

# Define the days of the week and their corresponding columns in the Excel file
days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
availability_columns = [f'{day} Availability' for day in days_of_week]

# Function to parse availability strings
def parse_availability(availability_str):
    slots = availability_str.split(', ')
    return {
        'am': 'AM' in slots,
        'pm': 'PM' in slots,
        'midday': 'Midday' in slots,
        'evening': 'Evening' in slots
    }

# Transform the data
data_to_insert = []
for _, row in df.iterrows():
    home_location_description = row['Home Location']
    home_location_id = get_location_id(home_location_description, locations_df)

    organization_name = row['School District']
    organization_id = get_organization_id(organization_name, organization_mapping)

    primary_vehicle_description = row['Primary Vehicle']
    primary_vehicle_id = None
    if primary_vehicle_description and organization_id:
        primary_vehicle_id = get_vehicle_id(primary_vehicle_description, vehicles_df, organization_name)

    driver_name = row['Driver Name']
    driver_id = get_user_id(driver_name, profiles_df)

    if home_location_id is not None and organization_id is not None:
        weekly_availability = {
            day: parse_availability(row[day_col] if pd.notnull(row[day_col]) else '') 
            for day, day_col in zip(days_of_week, availability_columns)
        }

        capabilities = row['Capabilities'].split(', ') if pd.notnull(row['Capabilities']) else []

        driver_data = {
            'name': row['Driver Name'],
            'license': row['License Type'],
            'home_location': home_location_id,
            'vehicle_primary': primary_vehicle_id,
            'capabilities': capabilities,
            'weekly_availability': json.dumps(weekly_availability),
            'id': driver_id, 
            'organization_id': organization_id
        }
        
        data_to_insert.append(driver_data)
    else:
        if home_location_id is None:
            print(f"Location '{home_location_description}' not found.")
        if organization_id is None:
            print(f"Organization '{organization_name}' not found.")

# Insert data into Supabase
for driver in data_to_insert:
    # Insert the driver data into Supabase
    response = supabase.table('drivers').insert(driver, returning='representation').execute()
    if 'error' in response:
        print(f"Error inserting data: {response['error']['message']}")

print("Data inserted successfully.")
