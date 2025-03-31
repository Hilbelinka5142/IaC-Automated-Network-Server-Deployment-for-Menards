import argparse
from netmiko import ConnectHandler
from datetime import datetime

def get_expired_schedules(net_connect):
    """Get all onetime schedules and filter out the expired ones."""
    schedule_output = net_connect.send_command("show firewall schedule onetime")
    expired_schedules = []

    # Get current date for comparison
    current_date = datetime.now().strftime("%Y/%m/%d")

    # Parse the schedule output
    for line in schedule_output.splitlines():
        if "edit" in line:
            schedule_name = line.split()[1]
            schedule_end_date = None
        if "set end" in line:
            schedule_end_date = line.split()[2]

        if schedule_end_date and schedule_end_date < current_date:
            expired_schedules.append(schedule_name)

    return expired_schedules

def delete_policies_from_schedule(net_connect, expired_schedules):
    """Delete policies and their corresponding source address objects."""
    for schedule_name in expired_schedules:
        # Find the policy ID associated with the expired schedule
        policy_output = net_connect.send_command(f"show firewall policy | grep {schedule_name}")
        
        # Get the policy ID
        policy_id = None
        for line in policy_output.splitlines():
            if f"schedule {schedule_name}" in line:
                policy_id = line.split()[1]
                break

        # If a policy is found, delete the policy and corresponding source address object
        if policy_id:
            # Delete the policy
            delete_policy_commands = [
                "config firewall policy",
                f"delete {policy_id}",
                "end"
            ]
            policy_output = net_connect.send_config_set(delete_policy_commands)
            print(f"Deleted policy {policy_id} associated with expired schedule {schedule_name}:\n", policy_output)

            # Delete the source address object corresponding to the policy
            delete_address_commands = [
                "config firewall address",
                f"delete SRC-{policy_id}",
                "end"
            ]
            address_output = net_connect.send_config_set(delete_address_commands)
            print(f"Deleted source address object SRC-{policy_id}:\n", address_output)

        else:
            print(f"No policy found associated with schedule {schedule_name}")

def remove_disabled_policies(host, user, password):
    """Connects to the Fortinet firewall and removes any policies with expired schedules."""
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
            # Get expired schedules
            expired_schedules = get_expired_schedules(net_connect)
            if expired_schedules:
                print(f"Expired schedules: {expired_schedules}")
                # Delete policies and corresponding source address objects associated with expired schedules
                delete_policies_from_schedule(net_connect, expired_schedules)
            else:
                print("No expired schedules found.")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remove disabled policies and associated source address objects from Fortinet firewall")
    parser.add_argument("--host", required=True, help="Firewall host IP")
    parser.add_argument("--user", required=True, help="Firewall username")
    parser.add_argument("--password", required=True, help="Firewall password")

    args = parser.parse_args()

    remove_disabled_policies(args.host, args.user, args.password)
