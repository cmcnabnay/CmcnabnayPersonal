import os
import pandas as pd
from supabase import create_client, Client
import numpy as np

# Function to concatenate address columns
def concatenate_address(row, address_columns):
    return ' '.join(str(row[col]) for col in address_columns if not pd.isnull(row[col]))

# Function to get route id from routes table
def get_route_id(route_title, routes):
    if pd.isnull(route_title):
        return None
    matching_route = routes[routes['title'] == route_title]
    if not matching_route.empty:
        return matching_route.iloc[0]['id']
    return None

# Function to get school id from schools table
def get_school_id(school_name, schools):
    if pd.isnull(school_name):
        return None
    
    matching_school = schools[schools['name'] == school_name]
    if not matching_school.empty:
        #print(f"Matched school_name: {school_name}, school_id: {matching_school.iloc[0]['id']}")
        return matching_school.iloc[0]['id']
    else:
        return map_school_to_id(school_name)
        #print(f"No match found for school_name: {school_name}")
    return None

# Function to get organization id from organizations table
def get_organization_id(org_name, organizations):
    matching_org = organizations[organizations['organization_name'] == org_name]
    if not matching_org.empty:
        return matching_org.iloc[0]['id']
    return None

# Initialize Supabase client
url = 'https://xrbfefmwiymnnpujtcbg.supabase.co'
key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhyYmZlZm13aXltbm5wdWp0Y2JnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTY3NTk5MDM1OSwiZXhwIjoxOTkxNTY2MzU5fQ.OfjHIGQLNhkad_w6g2h4IjoK3t_xbKqa6KGKEBwjmOQ'
supabase: Client = create_client(url, key)

# Load tables from Supabase
routes = supabase.table('routes_old').select('*').execute().data
routes_df = pd.DataFrame(routes)

schools = supabase.table('schools').select('*').execute().data
schools_df = pd.DataFrame(schools)

organizations = supabase.table('organizations').select('*').execute().data
organizations_df = pd.DataFrame(organizations)

# Define file paths and corresponding column mappings
file_mappings = [
    {
        'file': os.path.join(os.getcwd(), 'Transportation Rosters', '2024-25 CC Transportation Roster 8-11.xlsx'),
        'grade_col': 'Grade',
        'address_cols': ['Address', 'City', 'State', 'Zip'],
        'route_col': 'Route',
        #'am_stop_col': 'AM Stop',
        #'pm_stop_col': 'PM Stop',
        'organization': 'Grand Rapids Catholic'
    },
    {
        'file': os.path.join(os.getcwd(), 'Transportation Rosters', '2024-25 WC Transportation Roster 8-11.xlsx'),
        'grade_col': 'Grade',
        'address_cols': ['Address', 'City', 'State', 'Zip'],
        'route_col': 'Route',
        #'am_stop_col': 'AM Stop',
        #'pm_stop_col': 'PM Stop',
        'organization': 'Grand Rapids Catholic'
    },
    {
        'file': os.path.join(os.getcwd(), 'Transportation Rosters', '2024-25 Elementary Transportation Roster 8-11.xlsx'),
        'grade_col': 'Grade',
        'address_cols': ['Address', 'City', 'State', 'Zip'],
        'route_col': 'Route',
        #'am_stop_col': 'AM Stop',
        #'pm_stop_col': 'PM Stop',
        'organization': 'Grand Rapids Catholic'
    },
    {
        'file': os.path.join(os.getcwd(), 'Transportation Rosters', 'Transportation 2024-25 (Responses).xlsx'),
        'name_col': 'Student Name',
        'grade_col': 'Grade',
        'address_col': 'Address',
        'organization': 'St Mary Catholic District'
    }
    ##### Example School District #####
    # {
    # 'file': os.path.join(os.getcwd(), 'Transportation Rosters', 'Name of file with student names'),
    # 'grade_col': 'Grade',
    # 'address_cols': ['Address', 'City', 'State', 'Zip'],
    # 'route_col': 'Route',
    # 'am_stop_col': 'AM Stop',
    # 'pm_stop_col': 'PM Stop',
    # 'organization': 'Name of School District as appears in organization_name of organizations table'
    # }
]

# Fetch all primary keys from the students table
primary_keys = supabase.table('students').select('id').execute().data

# Delete each row individually
supabase.table('students').delete().neq('organization_id', 3).execute()

# Reset the id sequence
supabase.rpc('reset_students_id_sequence').execute()

# Function to map School Campus to school ID
def map_school_to_id(school_name):
    print(f"school name: {school_name}")
    if pd.isnull(school_name):
        return None
    school_name = school_name.strip().lower()
    if "smcc" in school_name or "st. mary catholic central" in school_name or "st mary’s catholic central" in school_name:
        return get_school_id('St. Mary Catholic Central', schools_df)
    elif "mces" in school_name or "st. mary's" in school_name or "st mary" in school_name or "st.marys" in school_name or "st mary's" in school_name or "st. marys" in school_name:
        return get_school_id('St. Mary Middle School', schools_df)
    elif "catholic central" in school_name and any(word in school_name for word in ["st mary", "st.mary", "st.marys", "st mary's"]):
        return get_school_id('St. Mary Middle School', schools_df)
    elif "st stephen" in school_name:
        return get_school_id('St. Stephen Catholic School', schools_df)
    elif "st. john's" in school_name or "st john" in school_name or "st john's" in school_name or "st. john" in school_name:
        return get_school_id('St. John Elementary', schools_df)
    elif any(word in school_name for word in ["saint michael", "st. michael", "st. michael's", "st michael", "st michael's"]):
        return get_school_id('St. Michael Early Elementary', schools_df)
    elif "sta" == school_name or "st. anthony" == school_name:
        return get_school_id('St. Anthony of Padua', schools_df)
    elif "sta" == school_name:
        return get_school_id('St. Thomas', schools_df)
    elif "c" == school_name:
        return get_school_id('WCHS', schools_df)
    else:
        print(f"Unmapped school name: {school_name}")  # Print unmapped school names
        return None  # Handle cases where school name does not match expected format

# Process each file
students_data = []
for mapping in file_mappings:
    df = pd.read_excel(mapping['file'], header=0, dtype=str)
    df.reset_index(drop=True, inplace=True)
    
    organization_id = get_organization_id(mapping['organization'], organizations_df)

    if mapping['file'] == os.path.join(os.getcwd(), 'Transportation Rosters', 'Transportation 2024-25 (Responses).xlsx'):
        # Process Transportation 2024-25 (Responses).xlsx
        for idx, row in df.iterrows():
            try:
                name = row[mapping['name_col']]
                school_id = map_school_to_id(row['School Campus'])
                
                grade = row[mapping['grade_col']]
                if pd.isnull(grade) or (isinstance(grade, str) and grade.strip().lower() == 'nan'):  # Check for NaN explicitly
                    grade_value = 'Unknown'
                elif grade == 'K':
                    grade_value = 'K'
                else:
                    try:
                        grade_value = int(grade)
                    except ValueError:
                        grade_value = 'Unknown'  # Load 'Unknown' for missing or non-numeric grades
                primary_address = row[mapping['address_col']]

                # Set default values ('TBD') for missing columns
                #am_stop = 'TBD'
                #pm_stop = 'TBD'
                route = None  # No route information

                student_record = {
                    'name': name.strip(),
                    'school': school_id,
                    'grade': grade_value,
                    'primary_address': primary_address,
                    'organization_id': organization_id,
                    'route': route,
                    #'am_stop': am_stop,
                    #'pm_stop': pm_stop,
                    }
                #print(student_record)
                student_record = {k: v.item() if isinstance(v, np.int64) else v for k, v in student_record.items()}
                students_data.append(student_record)
            except KeyError as e:
                print(f"KeyError: {e} in file {mapping['file']}")
                continue
    elif mapping['file'] == os.path.join(os.getcwd(), 'Transportation Rosters', '2024-25 Elementary Transportation Roster 8-11.xlsx'):
        # Process 2024-25 Elementary Transportation Roster
        previous_address = None
        for idx, row in df.iterrows():
            try:
                # Check if 'First Name' column is empty (column C)
                if pd.isnull(row['First Name']):
                    break  # Stop processing further rows if a blank cell in 'First Name' column is encountered

                # Continue only if the row is not entirely empty
                if not row.isnull().all():
                    name = row['First Name'] + ' ' + row['Last Name']  
                    school = row['School']
                    grade = row[mapping['grade_col']]
                    if grade == 'K':
                        grade_value = 'K'
                    else:
                        try:
                            grade_value = int(grade)
                        except ValueError:
                            grade_value = 'Unknown'  # Load 'Unknown' for missing or non-numeric grades

                    primary_address = concatenate_address(row, mapping['address_cols'])

                    if primary_address == '':
                        primary_address = previous_address

                    previous_address = primary_address
                    
                    route = get_route_id(row[mapping['route_col']], routes_df)
                    school_id = get_school_id(school, schools_df)

                    #am_stop = "N/A" if pd.isnull(row[mapping['am_stop_col']]) or row[mapping['am_stop_col']] == '' else 'TBD'
                    #pm_stop = "N/A" if pd.isnull(row[mapping['pm_stop_col']]) or row[mapping['pm_stop_col']] == '' else 'TBD'

                    student_record = {
                        'name': name,
                        'school': school_id,
                        'grade': grade_value,
                        'primary_address': primary_address,
                        'organization_id': organization_id,
                        'route': route,
                        #'am_stop': am_stop,
                        #'pm_stop': pm_stop
                    }

                    student_record = {k: v.item() if isinstance(v, np.int64) else v for k, v in student_record.items()}
                    students_data.append(student_record)
            except KeyError as e:
                print(f"KeyError: {e} in file {mapping['file']}")
                continue
    else:
        # Process other rosters (CC, WC)
        for idx, row in df.iterrows():
            try:
                name = row['Name']
                school = row['School']
                grade = row[mapping['grade_col']]
                if grade == 'K':
                    grade_value = 'K'
                else:
                    try:
                        grade_value = int(grade)
                    except ValueError:
                        grade_value = 'Unknown'  # Load 'Unknown' for missing or non-numeric grades

                primary_address = concatenate_address(row, mapping['address_cols'])
                route = get_route_id(row[mapping['route_col']], routes_df)
                school_id = get_school_id(school, schools_df)

                #am_stop = "N/A" if pd.isnull(row[mapping['am_stop_col']]) or row[mapping['am_stop_col']] == '' else 'TBD'
                #pm_stop = "N/A" if pd.isnull(row[mapping['pm_stop_col']]) or row[mapping['pm_stop_col']] == '' else 'TBD'

                student_record = {
                    'name': name,
                    'school': school_id,
                    'grade': grade_value,
                    'primary_address': primary_address,
                    'organization_id': organization_id,
                    'route': route,
                    #'am_stop': am_stop,
                    #'pm_stop': pm_stop
                }

                student_record = {k: v.item() if isinstance(v, np.int64) else v for k, v in student_record.items()}
                students_data.append(student_record)
            except KeyError as e:
                print(f"KeyError: {e} in file {mapping['file']}")
                continue

# Insert data into Supabase students table
supabase.table('students').insert(students_data).execute()

print("Data successfully loaded into Supabase students table.")
