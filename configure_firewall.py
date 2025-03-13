import json
import os
from netmiko import ConnectHandler

# Define path to JSON config file
CONFIG_FILE = "/tmp/firewall_config.json"

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

def clear_config_file():
    """Clear the firewall_config.json file after execution."""
    with open(CONFIG_FILE, "w") as file:
        file.write("{}")  # Write an empty JSON object

def configure_fortinet_firewall(config):
    """Connects to the Fortinet firewall and applies configurations."""
    
    # Firewall connection details
    fortigate = {
        "device_type": "fortinet",
        "host": config["host"],
        "username": config["username"],
        "password": config["password"],
        "session_log": "/tmp/netmiko_log.txt",
    }

    try:
        # Establish SSH connection using Netmiko
        with ConnectHandler(**fortigate) as net_connect:
            
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
                "set schedule always",
                f"set service \"{config['service']}\"",
                "set logtraffic all",
                "set nat enable",
                "next",
                "end",
            ]
            output2 = net_connect.send_config_set(policy_commands)
            print("Policy Output:\n", output2)

            # Save Configuration
            output3 = net_connect.send_command("execute save")
            print("Save Output:\n", output3)

        print("Firewall configuration completed successfully!")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    # Load config from JSON file
    config = load_config()
    
    if config:
        configure_fortinet_firewall(config)
        clear_config_file()  # Clear the file after execution
