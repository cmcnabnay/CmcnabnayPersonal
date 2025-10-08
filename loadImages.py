import os
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

# Initialize the Supabase client
url = "https://xrbfefmwiymnnpujtcbg.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhyYmZlZm13aXltbm5wdWp0Y2JnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTY3NTk5MDM1OSwiZXhwIjoxOTkxNTY2MzU5fQ.OfjHIGQLNhkad_w6g2h4IjoK3t_xbKqa6KGKEBwjmOQ"
options = ClientOptions(
    schema="public",
    headers={"Content-Type": "application/json"}
)
supabase: Client = create_client(url, key, options)

# Retrieve the list of images from the bucket
bucket_name = "images"
all_images = []

try:
    # Fetch all images without pagination
    response = supabase.storage.from_(bucket_name).list()
    if response and isinstance(response, list):
        all_images.extend(response)
        print(f"Total images fetched: {len(all_images)}")
    else:
        print("Unexpected response format or no response received.")
except Exception as e:
    print(f"An error occurred while listing objects: {e}")

# Construct the base URL for accessing images
base_image_url = f"{url}/storage/v1/object/public/{bucket_name}/"

print(all_images)
# Iterate through the complete list of images and update the database
for image in all_images:
    image_name = image['name']
    image_url = f"{base_image_url}{image_name}"
    
    # Extract the stop identifier from the image filename
    filename_parts = os.path.splitext(image_name)[0].split('_')
    if len(filename_parts) > 1:
        address_parts = ' '.join(filename_parts[:-1])
    else:
        address_parts = filename_parts[0]
    
    stop_identifier = address_parts
    print(f"Stop Identifier: {stop_identifier}")
    
    try:
        # Update the stops table where address matches
        update_result = supabase.table('stops').update({'image_link': image_url}).ilike('address', f'%{stop_identifier}%').execute()
        
        # Print the type and content of update_result for debugging
        print(f"Update result type: {type(update_result)}")
        print(f"Update result content: {update_result}")

        if isinstance(update_result, dict) and 'error' in update_result:
            print(f"Failed to update rows for address: {stop_identifier}. Error: {update_result['error']}")
        elif isinstance(update_result, dict) and 'data' in update_result:
            updated_rows = update_result.get('data')
            if updated_rows:
                print(f"Successfully updated rows for address: {stop_identifier}. Updated rows: {updated_rows}")
            else:
                print(f"No rows were updated for address: {stop_identifier}. This could indicate a mismatch in the address format.")
        else:
            print(f"Unexpected update result format for address: {stop_identifier}.")
    
    except Exception as e:
        print(f"An error occurred while updating rows for address: {stop_identifier}. Error: {e}")

print("Image links update process completed.")
