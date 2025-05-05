import json
import os
import argparse
from datetime import datetime
from netmiko import ConnectHandler

# Directory where all request JSONs are stored
REQUESTS_DIR = "/home/deploymentvm/Desktop/IaC-Automated-Network-Server-Deployment-for-Menards/automation-frontend/requests"

def get_latest_json_file():
    """ 
    Retrieves the latest JSON request file from the requests directory.
    Assumes files are named in timestamped format such as request_YYYYMMDD-HHMMSS.json.
    """
    files = [
        f for f in os.listdir(REQUESTS_DIR)
        if f.startswith("request_") and f.endswith(".json")
    ]
    if not files:
        raise FileNotFoundError("No request files found in the 'requests' directory.")

    # Return the file with the most recent timestamp in the filename
    files.sort(reverse=True)
    return os.path.join(REQUESTS_DIR, files[0])


def load_config():
    """
    Loads configuration data from:
    - The latest user request JSON file (for expiration date and firewall services)
    - A temporary file containing the source VM's IP address
    Returns a dictionary of necessary config values.
    """
    try:
        # Read the VM's IP address from a temporary file
        ip_file_path = "/home/deploymentvm/Desktop/IaC-Automated-Network-Server-Deployment-for-Menards/Ansible-Playbooks/tmp/vmip.txt"
        with open(ip_file_path, "r") as ip_file:
            src_ip = ip_file.read().strip()  # Remove any newlines or spaces

        # Load user request data
        config_file = get_latest_json_file()
        print(f"Loading configuration from: {config_file}")
        with open(config_file, "r") as file:
            full_data = json.load(file)
            return {
                "src_addr": src_ip,
                "expiration": full_data.get("expiration").replace("-", "/"),
                "services": full_data.get("firewall_services", [])
            }
    except Exception as e:
        print(f"Error loading config: {e}")
        return None

def get_next_policy_id(net_connect):
    """
    Determines the next available firewall policy ID by checking existing ones.
    Returns the next integer policy ID.
    """
    output = net_connect.send_command("show firewall policy")
    
    policy_ids = []
    for line in output.splitlines():
        if "edit" in line:  # Policies start with "edit <policy_id>"
            try:
                policy_id = int(line.split()[1])  # Extract the policy number
                policy_ids.append(policy_id)
            except (IndexError, ValueError):
                continue  # Ignore invalid lines

    next_policy_id = max(policy_ids) + 1 if policy_ids else 1  # Start at 1 if no policies exist
    return next_policy_id

def configure_fortinet_firewall(config, host, user, password):
    """
    Connects to a Fortinet firewall via SSH and:
    - Creates a one-time schedule for access
    - Creates a source address object for the VM
    - Dynamically adds a policy allowing traffic from VM to internal services
    """
    
    # Establish SSH connection using Netmiko
    fortigate = {
        "device_type": "fortinet",
        "host": host,
        "username": user,
        "password": password,
        "port": 22,
        "session_log": "/tmp/netmiko_log.txt",
    }

    try:
        with ConnectHandler(**fortigate) as net_connect:
            # Get next available policy ID
            policy_id = get_next_policy_id(net_connect)
            print(f"Next available policy ID: {policy_id}")

            # Generate schedule name dynamically
            schedule_name = f"Policy-{policy_id}"
            start_date = datetime.now().strftime("00:00:00 %Y/%m/%d")
            end_date = f"00:00:00 {config['expiration']}"

            # Schedule commands
            schedule_commands = [
                "config firewall schedule onetime",
                f"edit {schedule_name}",
                f"set start {start_date}",
                f"set end {end_date}",
                "next",
                "end",
            ]  
            net_connect.send_config_set(schedule_commands)
            
            # Create Source Address Object
            address_commands = [
                "config firewall address",
                f"edit SRC-{policy_id}",
                f"set subnet {config['src_addr']} 255.255.255.255",
                "next",
                "end",
            ]
            net_connect.send_config_set(address_commands)

            services_str = " ".join(f"\"{s}\"" for s in config["services"])

            # Create Firewall Policy dynamically
            policy_commands = [
                "config firewall policy",
                f"edit {policy_id}",
                f"set srcintf vlan30",
                f"set dstintf vlan10",
                f"set srcaddr \"SRC-{policy_id}\"",
                f"set dstaddr all",
                "set action accept",
                f"set schedule \"{schedule_name}\"",
                f"set service {services_str}",
                "set logtraffic all",
                "unset nat",
                "next",
                "end",
            ]
            net_connect.send_config_set(policy_commands)

        print("Firewall configuration completed successfully!")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    # Argument parsing for host, user, and password only
    parser = argparse.ArgumentParser(description="Configure Fortinet Firewall using SSH")
    parser.add_argument("--host", required=True, help="Firewall host IP")
    parser.add_argument("--user", required=True, help="Firewall username")
    parser.add_argument("--password", required=True, help="Firewall password")
    args = parser.parse_args()

    # Load config from JSON file
    config = load_config()

    # Check if JSON config was loaded successfully
    if config:
        # Configure the firewall using the parsed arguments and JSON configuration
        configure_fortinet_firewall(config, args.host, args.user, args.password)
