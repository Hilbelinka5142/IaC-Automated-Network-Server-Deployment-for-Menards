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

def configure_fortinet_firewall(config, host, user, password):
    """Connects to the Fortinet firewall and applies configurations."""
    
    # Get the current date for the start time (today's date) and set time to 00:00:00 (midnight)
    start_date = datetime.now().strftime("00:00:00 %Y/%m/%d")
    end_date = f"00:00:00 {config['expiration']}"
    schedule_name = f"Policy-{config['policy_id']}"

    # Firewall connection details
    fortigate = {
        "device_type": "fortinet",
        "host": host,
        "username": user,
        "password": password,
        "port": 22,
        "session_log": "/tmp/netmiko_log.txt",
    }

    try:
        # Establish SSH connection using Netmiko
        with ConnectHandler(**fortigate) as net_connect:
            
            schedule_commands = [
                "config firewall schedule onetime",
                f"edit {schedule_name}",
                f"set start {start_date}",
                f"set end {end_date}",
                "next",
                "end",
            ]  
            schedule_output = net_connect.send_config_set(schedule_commands)
            print("Address Object Output:\n", schedule_output)
            
            # Create Source Address Object
            address_commands = [
                "config firewall address",
                f"edit SRC-{config['policy_id']}",
                f"set subnet {config['src_addr']} 255.255.255.255",
                "next",
                "end",
            ]
            output1 = net_connect.send_config_set(address_commands)
            print("Address Object Output:\n", output1)

            # Create Firewall Policy
            policy_commands = [
                "config firewall policy",
                f"edit {config['policy_id']}",
                f"set srcintf \"{config['src_intf']}\"",
                f"set dstintf \"{config['dst_intf']}\"",
                f"set srcaddr \"SRC-{config['policy_id']}\"",
                f"set dstaddr \"{config['dst_addr']}\"",
                "set action accept",
                f"set schedule \"{schedule_name}\"",
                f"set service \"{config['service']}\"",
                "set logtraffic all",
                "unset nat",
                "next",
                "end",
            ]
            output2 = net_connect.send_config_set(policy_commands)
            print("Policy Output:\n", output2)

        print("Firewall configuration completed successfully!")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    # Load config from JSON file
    config = load_config()
    
    if config:
        parser = argparse.ArgumentParser(description="Remove disabled policies and associated source address objects from Fortinet firewall")
        parser.add_argument("--host", required=True, help="Firewall host IP")
        parser.add_argument("--user", required=True, help="Firewall username")
        parser.add_argument("--password", required=True, help="Firewall password")
        args = parser.parse_args()

        configure_fortinet_firewall(config, args.host, args.user, args.password)
