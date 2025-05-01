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
firewall_dir = os.path.expanduser("/home/deploymentvm/Desktop/Ansible/Firewall")
frontend_dir = os.path.expanduser("/home/deploymentvm/Desktop/Automation_frontend/IaC-Automated-Network-Server-Deployment-for-Menards/automation-frontend")
playbooks = {
    'webserver': [
        os.path.join(ansible_dir, 'CreateVM.yaml'), 
        os.path.join(ansible_dir, 'CreateDNS.yaml'),
        os.path.join(ansible_dir, 'getVMIP.yaml')
        ],
    'request': [os.path.join(base_dir, 'requests')],
    'firewall': [os.path.join(firewall_dir, 'fortinet_policy_change.yaml')],
    'email': [os.path.join(firewall_dir, 'email_sender.yaml')],
    'inventory': {
        'webserver': os.path.join(ansible_dir, 'inventory'),
        'firewall': os.path.join(firewall_dir, 'inventory.ini'),
    }
}


# Load latest request JSON and save to vars.yaml
request_files = sorted([f for f in os.listdir(playbooks["request"][0]) if f.endswith('.json')], reverse=True)
if not request_files:
    print("No request files found.")
    exit(1)
latest_request = request_files[0]
request_path = os.path.join(playbooks["request"][0], latest_request)
with open(request_path, 'r') as f:
    request_data = json.load(f)
print(f"Loaded latest request: {latest_request}")
print(json.dumps(request_data, indent=4))
vars_yaml_path = os.path.join(os.path.dirname(__file__), 'vars.yaml')
with open(vars_yaml_path, 'w') as f:
    yaml.dump(request_data, f)
print(f"Converted data saved to: {vars_yaml_path}")


# Function to run ansible-playbook
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

# Gets custom inputs and creates unattend.iso file for Windows machine
# Windows: Generate unattend.iso
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


# Ubuntu: Generate ubuntu-autoinstall.iso
def generate_ubuntu_autoinstall_iso():
    subprocess.run(["python3", os.path.join(frontend_dir, "generate_ubuntu_iso.py")], check=True)


# Main VM creation flow and checks vm status
def createVM():
    print("Starting VM creation...")
    vars_file = os.path.join(frontend_dir, 'vars.yaml')
    with open(vars_file, 'r') as f:
        os_data = yaml.safe_load(f)
        selected_os = os_data.get("os", "").lower()
#debug command
    print(f"OS selected from vars.yaml: {selected_os}")

    # Conditionally generate install media
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
    
    # Wait up to 2100 seconds (35 minutes) for the VM IP file
    ip_file_path = os.path.join(ansible_dir, 'tmp/vmip.txt')
    vmIP = ""
    max_wait_time = 2100  # in seconds
    check_interval = 30   # check every 30 seconds
    elapsed = 0

    print("Waiting for VM IP to be written to vmip.txt...")

    while elapsed < max_wait_time:
        if os.path.exists(ip_file_path):
            with open(ip_file_path, 'r') as f:
                vmIP = f.read().strip()
            if vmIP:
                print(f"IP address retrieved: {vmIP}")
                break
        time.sleep(check_interval)
        elapsed += check_interval
    else:
        print("Timed out waiting for vmip.txt. VM may not have booted or reported IP.")
        return

    # Run get vm ip playbook
    if not runPlaybook(playbooks["webserver"][2], playbooks["inventory"]["webserver"]):
        return

    print(f"VM IP retrieved: {vmIP}")
    
    # Run firewall playbook    
    if not runPlaybook(playbooks["firewall"][0], playbooks["inventory"]["firewall"]):
        return
        
    # Runs DNS playbook (disabled)
    # if not runPlaybook(playbooks["webserver"][1], playbooks["inventory"]["webserver"]): #TODO: need to make sure playbook collects correct VM data once it boots
    #     return #stops if playbook fails


    # Finally, send the credentials via email
    if not runPlaybook(playbooks["email"][0], playbooks["inventory"]["firewall"]):
        print("WARNING: Failed to send email with credentials.")
    else:
        print("Credentials have been emailed to the user.")

    # Run the Apache deployment playbook with the dynamic IP **only if OS is Ubuntu**
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
        print("Skipping Apache deployment since OS is not Ubuntu.")

    print(f"Your VM was successfully created with the IP address of: {vmIP}")

createVM()