import os
import json
import yaml
import subprocess

# Path to the requests directory
REQUESTS_DIR = '/home/deploymentvm/Desktop/Automation_frontend/IaC-Automated-Network-Server-Deployment-for-Menards/automation-frontend/requests'

# Find the most recent request file
request_files = sorted(
    [f for f in os.listdir(REQUESTS_DIR) if f.endswith('.json')],
    reverse=True
)

if not request_files:
    print("No request files found.")
    exit(1)

latest_request = request_files[0]
request_path = os.path.join(REQUESTS_DIR, latest_request)

# Load the JSON data
with open(request_path, 'r') as f:
    request_data = json.load(f)

print(f"Loaded latest request: {latest_request}")
print(json.dumps(request_data, indent=4))

# Convert to vars.yaml format
vars_yaml_path = os.path.join(os.path.dirname(__file__), 'vars.yaml')
with open(vars_yaml_path, 'w') as f:
    yaml.dump(request_data, f)

print(f"Converted data saved to: {vars_yaml_path}")

# Run the Ansible playbook
try:
    playbook_path = '/home/deploymentvm/Desktop/IaC-Automated-Network-Server-Deployment-for-Menards/Ansible-Playbooks/CreateVM.yaml'
    subprocess.run(['ansible-playbook', playbook_path], check=True)
except subprocess.CalledProcessError as e:
    print("Error running Ansible playbook:", e)

