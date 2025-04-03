import json
import os
import argparse
from datetime import datetime
from netmiko import ConnectHandler

# Define path to JSON config file
CONFIG_FILE = "tmp/firewall_config.json"

def load_config():
    """Load configuration from JSON file."""
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: Configuration file {CONFIG_FILE} not found!")
        return None

    with open(CONFIG_FILE, "r") as file:
        try:
            config = json.load(file)
            return config
        except json.JSONDecodeError:
            print("Error: Failed to parse JSON configuration file.")
            return None

def get_next_policy_id(net_connect):
    """Retrieve the next available policy ID on the firewall."""
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
    """Connects to the Fortinet firewall and applies configurations dynamically."""
    
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
                f"set service \"{config['service']}\"",
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
