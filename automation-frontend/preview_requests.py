import os
import json

# Path to the requests directory (relative to where this script is located)
REQUESTS_DIR = os.path.join(os.path.dirname(__file__), 'requests')

# Get all .json files from the requests directory
files = [f for f in os.listdir(REQUESTS_DIR) if f.endswith('.json')]

# Exit if no request files exist
if not files:
    print("No VM request files found.")
    exit()

# Print a summary list of request files
print("Available VM Requests:\n")

for i, filename in enumerate(sorted(files), start=1):
    filepath = os.path.join(REQUESTS_DIR, filename)
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            vm_name = data.get('vm_name', 'N/A')
            os_type = data.get('os', 'N/A')
            expiration = data.get('expiration', 'N/A')
            print(f"{i}. {filename} → VM: {vm_name}, OS: {os_type}, Exp: {expiration}")
    except Exception as e:
        print(f"{i}. {filename} → Error reading file: {e}")
