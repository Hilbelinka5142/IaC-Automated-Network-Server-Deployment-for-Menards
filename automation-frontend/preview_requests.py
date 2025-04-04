import os
import json
import yaml
import subprocess
import time
import platform

# Path to the requests/playbook directory
base_dir = os.path.dirname(__file__)
ansible_dir = os.path.expanduser("~/Desktop/IaC-Automated-Network-Server-Deployment-for-Menards/Ansible-Playbooks")
playbooks = {
    'webserver': [os.path.join(ansible_dir, 'CreateVM.yaml')], # TODO Add file path for firewall playbook for creating SSH, HTTPS, and RDP policies
    'request': [os.path.join(base_dir, 'requests')],
    'inventory': [os.path.join(ansible_dir, 'inventory')]
}

# Find the most recent request file
request_files = sorted(
    [f for f in os.listdir(playbooks["request"][0]) if f.endswith('.json')],
    reverse=True
)

if not request_files:
    print("No request files found.")
    exit(1)

latest_request = request_files[0]
request_path = os.path.join(playbooks["request"][0], latest_request)

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

# Function for running a playbook
def runPlaybook(playbook):
	try:
		results = subprocess.run(
			["ansible-playbook", playbook, '-i', playbooks['inventory'][0]],
			check=True,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE
	    )
		print(f"Playbook {playbook} executed successfully!")
		print(results.stdout.decode())
	except subprocess.CalledProcessError as e:
		print(f"Error while executing playbook {playbook}:")
		print("STDOUT:")
		print(e.stdout.decode())
		print("STDERR:")
		print(e.stdout.decode())
		return False
	return True

# Checks the status of the VM
def checkServerStatus(ipAddress):
    # Get's the current operating system
    system_platform = platform.system()# TODO maybe change if I can just grab data from the front end for what operating system they chose to boot

    if system_platform == "Linux":
        ping_command = ["ping", "-c", "4", ipAddress]
    elif system_platform == "Windows":
        ping_command = ["ping", "-n", "4", ipAddress]
    else:
        print(f"Unsupported platform: {system_platform}")
        return False

    try:
        result = subprocess.run(
            ping_command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print(f"Server at {ipAddress} is up!")
        return True
    except subprocess.CalledProcessError:
        print(f"Server at {ipAddress} is not reachable.")
        return False

# Main function that runs playbook function and checks vm status
def createVM():
	print("Starting VM creation...")
	
	#runs the webserver playbook
	if not runPlaybook(playbooks["webserver"][0]):
		return #stops if playbook fails
	
	#runs the firewall playbook
	#if not runPlaybook(playbooks["webserver"][1]):
		#return #stops if playbook fails
	
	# Get's the Ip of the new VM
	vmIP = ""

	while not checkServerStatus(vmIP):
		print("Waiting for VM to come online...")
		time.sleep(10) #waits 10 seconds before retrying

	print(f"Your VM was successfully created with the IP address of: {vmIP}")
	
createVM()
