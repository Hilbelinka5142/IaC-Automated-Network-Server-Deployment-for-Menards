import os
import json
import yaml
import subprocess
import time
import platform
import tempfile
from pathlib import Path

# Path to the requests/playbook directory
base_dir = os.path.dirname(__file__)
ansible_dir = os.path.expanduser("~/Desktop/IaC-Automated-Network-Server-Deployment-for-Menards/Ansible-Playbooks")
firewall_dir = os.path.expanduser("/home/deploymentvm/Desktop/Ansible/Firewall")
frontend_dir = os.path.expanduser("/home/deploymentvm/Desktop/Automation_frontend/IaC-Automated-Network-Server-Deployment-for-Menards/automation-frontend")
playbooks = {
    'webserver': [os.path.join(ansible_dir, 'CreateVM.yaml'), (ansible_dir, 'CreateDNS.yaml')],
    'request': [os.path.join(base_dir, 'requests')],
    'firewall': [os.path.join(firewall_dir, 'fortinet_policy_change.yaml')],
    'inventory': {
        'webserver': os.path.join(ansible_dir, 'inventory'),
        'firewall': os.path.join(firewall_dir, 'inventory.ini')
    }
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
def runPlaybook(playbook, inventoryPath):
	try:
		results = subprocess.run(
			["ansible-playbook", playbook, '-i', inventoryPath],
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
    system_platform = platform.system()                 #TODO: maybe change if I can just grab data from the front end for what operating system they chose to boot. need to get VM data

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

# Gets custom inputs and creates unattend.iso file for Windows machine
def generate_autounattend_iso(xml_template_path, yaml_input_path, output_iso_path):
    # Read external input (e.g., a password, username, etc.) from the YAML file
    with open(yaml_input_path, "r") as f:
        input_data = yaml.safe_load(f)

    # Print the input data to verify it has been loaded correctly
    print("Loaded input data:", input_data)

    # Read the XML template
    with open(xml_template_path, "r") as f:
        xml_content = f.read()

    # Replace placeholders in the XML template with values from the YAML input
    for key, value in input_data.items():
        # Replace all occurrences of 'key' in the XML with the corresponding 'value'
        xml_content = xml_content.replace(f"{{{{ {key} }}}}", str(value))

    # Create a temporary directory to stage ISO contents
    with tempfile.TemporaryDirectory() as temp_dir:
        xml_path = Path(temp_dir) / "autounattend.xml"

        # Write the updated XML content to a new file
        with open(xml_path, "w") as f:
            f.write(xml_content)

        # Generate ISO using genisoimage or mkisofs
        subprocess.run([
            "genisoimage", "-o", output_iso_path, "-quiet", "-V", "AUTOUNATTEND", "-J", "-r", str(xml_path)
        ], check=True)

        print(f"autounattend ISO created: {output_iso_path}")


# Main function that runs playbook function and checks vm status
def createVM():
    print("Starting VM creation...")

    # Get the IP of the new VM
    ip_file_path = os.path.join(ansible_dir, '/tmp/vmip.txt')
    vmIP = ""

    #creates unattend ISO 
    generate_autounattend_iso(
        os.path.join(ansible_dir, 'autounattendTEMPLATE.xml'), 
        os.path.join(frontend_dir, 'vars.yaml'),
        os.path.join(ansible_dir, 'unattend.iso')
    )

    #runs the webserver playbook
    if not runPlaybook(playbooks["webserver"][0], playbooks["inventory"]["webserver"]):
        return #stops if playbook fails

    #runs the firewall playbook
    if not runPlaybook(playbooks["firewall"][0], playbooks["inventory"]["firewall"]):
        return #stops if playbook fails


    #runs the DNS playbook  
    #if not runPlaybook(playbooks["webserver"][1], playbooks["inventory"]["webserver"]):             #TODO: need to make sure playbook collects correct VM data once it boots
    #    return #stops if playbook fails

    if os.path.exists(ip_file_path):
        with open(ip_file_path, 'r') as f:
            vmIP = f.read().strip()

    if not vmIP:
        print("Failed to retrieve VM IP.")
        

    while not checkServerStatus(vmIP):
        print("Waiting for VM to come online...")
        time.sleep(10)  # waits 10 seconds before retrying

    print(f"Your VM was successfully created with the IP address of: {vmIP}")

createVM()



"""
Code to Create xml file, convert it into ISO to use for windows auto install



def generate_autounattend_iso(xml_template_path, outside_input_path, output_iso_path):
    # Read external input (e.g., a password, username, etc.)
    with open(outside_input_path, "r") as f:
        outside_input = f.read()

    # Replace placeholder in autounattend XML
    with open(xml_template_path, "r") as f:
        xml_content = f.read().replace("OUTSIDE INPUT", outside_input)

    # Create a temporary directory to stage ISO contents
    with tempfile.TemporaryDirectory() as temp_dir:
        xml_path = Path(temp_dir) / "autounattend.xml"

        with open(xml_path, "w") as f:
            f.write(xml_content)

        # Generate ISO using genisoimage or mkisofs
        subprocess.run([
            "genisoimage", "-o", output_iso_path, "-quiet", "-V", "AUTOUNATTEND", "-J", "-r", str(xml_path)
        ], check=True)

        print(f"autounattend ISO created: {output_iso_path}")




Calling the function********        

generate_autounattend_iso(
    xml_template_path="~/Desktop/IaC-Automated-Network-Server-Deployment-for-Menards/xml/autounattend_template.xml",
    outside_input_path="input.txt",                                                                                     TODO: this will come from the input from the frontend
    output_iso_path="~/Desktop/IaC-Automated-Network-Server-Deployment-for-Menards/xml/autounattend.iso"
)



"""
