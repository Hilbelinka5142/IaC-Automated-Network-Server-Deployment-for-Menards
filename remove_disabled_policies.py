import argparse
from netmiko import ConnectHandler

def remove_disabled_policies(host, user, password):
    """Connects to the Fortinet firewall and removes any disabled policies."""

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
            net_connect.send_command("config firewall policy")
            policy_output = net_connect.send_command("show")
            disabled_policies = []

            for line in policy_output.splitlines():
                if "edit" in line:
                    policy_id = line.split()[1]
                if "set status disable" in line:
                    disabled_policies.append(policy_id)

            for policy_id in disabled_policies:
                delete_commands = [
                    f"delete {policy_id}",
                    "end"
                ]
                output = net_connect.send_config_set(delete_commands)
                print(f"Deleted disabled policy {policy_id}:\n", output)

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remove disabled policies from Fortinet firewall")
    parser.add_argument("--host", required=True, help="Firewall host IP")
    parser.add_argument("--user", required=True, help="Firewall username")
    parser.add_argument("--password", required=True, help="Firewall password")

    args = parser.parse_args()
    
    remove_disabled_policies(args.host, args.user, args.password)
