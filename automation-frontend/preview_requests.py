import os
import json
import yaml
import subprocess
import time
import platform
import tempfile
from pathlib import Path

# Path to key directories
base_dir = os.path.dirname(__file__)
ansible_dir = os.path.expanduser("/home/deploymentvm/Desktop/IaC-Automated-Network-Server-Deployment-for-Menards/Ansible-Playbooks")
firewall_dir = os.path.expanduser("/home/deploymentvm/Desktop/IaC-Automated-Network-Server-Deployment-for-Menards/Firewall")
frontend_dir = os.path.expanduser("/home/deploymentvm/Desktop/IaC-Automated-Network-Server-Deployment-for-Menards/automation-frontend")

# Mapping of relevant Ansible playbooks and inventory files
playbooks = {
    'webserver': [
        os.path.join(ansible_dir, 'CreateVM.yaml'),   # Creates a VM
        os.path.join(ansible_dir, 'CreateDNS.yaml'),  # Configures DNS (optional/disabled)
        os.path.join(ansible_dir, 'getVMIP.yaml')     # Fetches VM's IP
        ],
    'request': [os.path.join(base_dir, 'requests')],
    'firewall': [os.path.join(firewall_dir, 'fortinet_policy_change.yaml')],
    'email': [os.path.join(firewall_dir, 'email_sender.yaml')],
    'inventory': {
        'webserver': os.path.join(ansible_dir, 'inventory'),
        'firewall': os.path.join(firewall_dir, 'inventory'),
    }
}


# -----------------------------
# Load Latest Request and Save as YAML
# -----------------------------
# Get list of JSON request files and load the most recent one
request_files = sorted([f for f in os.listdir(playbooks["request"][0]) if f.endswith('.json')], reverse=True)
if not request_files:
    print("No request files found.")
    exit(1)

# Load latest request data
latest_request = request_files[0]
request_path = os.path.join(playbooks["request"][0], latest_request)
with open(request_path, 'r') as f:
    request_data = json.load(f)
print(f"Loaded latest request: {latest_request}")
print(json.dumps(request_data, indent=4))

# Convert the loaded JSON request to a vars.yaml file for use in Ansible
vars_yaml_path = os.path.join(os.path.dirname(__file__), 'vars.yaml')
with open(vars_yaml_path, 'w') as f:
    yaml.dump(request_data, f)
print(f"Converted data saved to: {vars_yaml_path}")


# -----------------------------
# Function: runPlaybook
# -----------------------------
# Executes an Ansible playbook with a given inventory
def runPlaybook(playbook, inventoryPath):
    try:
        results = subprocess.run([
            "ansible-playbook", playbook, '-i', inventoryPath
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Playbook {playbook} executed successfully!")
        print(results.stdout.decode())
    except subprocess.CalledProcessError as e:
        print(f"Error while executing playbook {playbook}:")
        print("STDOUT:")
        print(e.stdout.decode())
        print("STDERR:")
        print(e.stderr.decode())
        return False
    return True

# -----------------------------
# Function: generate_autounattend_iso
# -----------------------------
# Generates a Windows installation ISO with a customized autounattend.xml file
def generate_autounattend_iso(xml_template_path, yaml_input_path, output_iso_path):
    with open(yaml_input_path, "r") as f:
        input_data = yaml.safe_load(f)
    with open(xml_template_path, "r") as f:
        xml_content = f.read()
    for key, value in input_data.items():
        xml_content = xml_content.replace(f"{{{{ {key} }}}}", str(value))
    with tempfile.TemporaryDirectory() as temp_dir:
        xml_path = Path(temp_dir) / "autounattend.xml"
        with open(xml_path, "w") as f:
            f.write(xml_content)
        subprocess.run(["genisoimage", "-o", output_iso_path, "-quiet", "-V", "AUTOUNATTEND", "-J", "-r", str(xml_path)], check=True)
        print(f"autounattend ISO created: {output_iso_path}")


# -----------------------------
# Function: generate_ubuntu_autoinstall_iso
# -----------------------------
# Generates an Ubuntu autoinstall ISO by calling a frontend script
def generate_ubuntu_autoinstall_iso():
    subprocess.run(["python3", os.path.join(frontend_dir, "generate_ubuntu_iso.py")], check=True)


# -----------------------------
# Function: createVM
# -----------------------------
# Core function that automates the full VM provisioning process
def createVM():
    print("Starting VM creation...")

    
    vars_file = os.path.join(frontend_dir, 'vars.yaml')
    with open(vars_file, 'r') as f:
        os_data = yaml.safe_load(f)
        selected_os = os_data.get("os", "").lower()
    print(f"OS selected from vars.yaml: {selected_os}")

    # Generate the appropriate installation media based on OS
    if selected_os == "windows":
        generate_autounattend_iso(
            os.path.join(ansible_dir, 'autounattendTEMPLATE.xml'),
            vars_file,
            os.path.join(ansible_dir, 'unattend.iso')
        )
    elif selected_os == "ubuntu":
        generate_ubuntu_autoinstall_iso()
    else:
        print(f"Unsupported OS for ISO generation: {selected_os}")
        return

    # Run webserver playbook
    if not runPlaybook(playbooks["webserver"][0], playbooks["inventory"]["webserver"]):
        return
    
    # Wait up to 35 minutes to give time for provisioning before attempting IP fetch
    ip_file_path = os.path.join(ansible_dir, 'tmp/vmip.txt')
    vmIP = ""
    max_wait_time = 2100  # in seconds
    print("Waiting for VM IP to be written to vmip.txt...")
    time.sleep(max_wait_time)
    
    # Run playbook to retrieve the VM IP
    if not runPlaybook(playbooks["webserver"][2], playbooks["inventory"]["webserver"]):
        return

    # Read IP address from file
    try:
        with open(ip_file_path, 'r') as f:
            vmIP = f.read().strip()
    except Exception as e:
        print(f"Failed to read VM IP: {e}")
        return
    print(f"VM IP retrieved: {vmIP}")
    
    # Apply firewall policy updates via Ansible   
    if not runPlaybook(playbooks["firewall"][0], playbooks["inventory"]["firewall"]):
        return
        
    # Runs DNS playbook (disabled)
    # if not runPlaybook(playbooks["webserver"][1], playbooks["inventory"]["webserver"]):
    #     return


    # Finally, send the credentials via email
    if not runPlaybook(playbooks["email"][0], playbooks["inventory"]["firewall"]):
        print("WARNING: Failed to send email with credentials.")
    else:
        print("Credentials have been emailed to the user.")

    # (Optional future feature) Apache deployment if OS is Ubuntu
    '''# Run the Apache deployment playbook with the dynamic IP **only if OS is Ubuntu**
    if selected_os == "ubuntu":
        with open(vars_file, 'r') as f:
            vars_data = yaml.safe_load(f)

        ssh_user = vars_data.get("username", "ubuntu")  # Fallback to 'ubuntu' if not specified
        ssh_key_path = "/home/deploymentvm/.ssh/ansible"  # Update if needed

        dynamic_inventory = f"""[VM]
{vmIP} ansible_user={ssh_user} ansible_ssh_private_key_file={ssh_key_path}
"""

        temp_inventory_path = "/home/deploymentvm/Desktop/IaC-Automated-Network-Server-Deployment-for-Menards/Ansible-Playbooks/tmp/dynamic_inventory.ini"
        with open(temp_inventory_path, 'w') as f:
            f.write(dynamic_inventory)

        apache_playbook_path = os.path.join(ansible_dir, 'Apache.yaml')
        print("Running Apache deployment playbook...")
        if not runPlaybook(apache_playbook_path, temp_inventory_path):
            print("Failed to deploy Apache to the VM.")
            return
    else:
        print("Skipping Apache deployment since OS is not Ubuntu.")'''

    # Final confirmation
    print(f"Your VM was successfully created with the IP address of: {vmIP}")

# -----------------------------
# Entry point
# -----------------------------
# Trigger the main provisioning workflow
createVM()
