import argparse
from netmiko import ConnectHandler
from datetime import datetime

def get_expired_schedules(net_connect):
    """
    Connects to the firewall and retrieves onetime schedules.
    Parses them and returns a list of expired schedule names.
    """
    schedule_output = net_connect.send_command("show firewall schedule onetime")
    expired_schedules = []

    # Get current date for comparison (as a datetime object)
    current_date = datetime.now()

    # Parse the schedule output
    schedule_name = None
    schedule_end_date = None  # Initialize schedule_end_date to avoid reference before assignment

    for line in schedule_output.splitlines():
        if "edit" in line:
            # When a new schedule is found, reset the schedule_name and schedule_end_date
            if schedule_name and schedule_end_date and schedule_end_date < current_date:
                expired_schedules.append(schedule_name)
            schedule_name = line.split()[1]
            schedule_end_date = None  # Reset end date for the new schedule

        if "set end" in line:
            # The line will be like 'set end 00:00 2025/04/01'
            end_date_str = line.split()[-1]  # This grabs '2025/04/01'

            # Convert the date string to a datetime object
            schedule_end_date = datetime.strptime(end_date_str, "%Y/%m/%d")

    # Add the last schedule to expired_schedules if applicable
    if schedule_name and schedule_end_date and schedule_end_date < current_date:
        expired_schedules.append(schedule_name)

    print(f"Expired schedules detected: {expired_schedules}")  # Debug line
    return expired_schedules

def extract_policy_blocks(policy_output):
    """Extract individual policy blocks from the firewall policy output."""
    policy_blocks = []
    policy_block = []
    
    for line in policy_output.splitlines():
        if line.startswith("edit"):  # New policy block starts
            if policy_block:  # If there’s a previous policy, add it to the list
                policy_blocks.append(policy_block)
            policy_block = [line]  # Start a new policy block with the current line
        elif line.strip() == "next":  # End of the current policy block
            policy_block.append(line)  # Add 'next' to the current block
            policy_blocks.append(policy_block)  # Add the completed block to the list
            policy_block = []  # Reset for the next policy block
        else:
            policy_block.append(line)  # Add lines to the current policy block

    if policy_block:  # Add any remaining policy block if present
        policy_blocks.append(policy_block)

    return policy_blocks

def delete_policies_from_schedule(net_connect, expired_schedules):
    """Delete policies and their corresponding source address objects."""
    for schedule_name in expired_schedules:
        # Remove the quotes from the schedule name for comparison purposes
        schedule_name = schedule_name.strip('"')

        # Find the policy blocks associated with the expired schedule
        policy_output = net_connect.send_command("show firewall policy")
        
        print(f"Searching for policies associated with expired schedule: {schedule_name}")  # Debug line
        
        # Extract policy blocks from the output
        policy_blocks = extract_policy_blocks(policy_output)

        # Iterate through each individual policy block
        for policy_block in policy_blocks:
            policy_block_str = "\n".join(policy_block)  # Convert the block to a single string
            
            # Check if the schedule is associated with this policy
            if f'set schedule "{schedule_name}"' in policy_block_str:
                # Extract the policy ID from the 'edit <policy_id>' line
                policy_id = policy_block[0].split()[1]
                print(f"Found policy {policy_id} associated with expired schedule {schedule_name}")  # Debug line

                # Delete the policy and corresponding address object
                if policy_id and policy_id.isdigit():  # Ensure we have a valid numeric policy ID
                    print(f"Deleting policy {policy_id} associated with expired schedule {schedule_name}")  # Debug line
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

                    delete_schedule_command = [
                    "config firewall schedule onetime",
                    f"delete {schedule_name}",
                    "end"
                    ]
                    schedule_output = net_connect.send_config_set(delete_schedule_command)
                    print(f"Deleted schedule {schedule_name}:\n", schedule_output)

                break  # Exit after processing the first matching policy for the schedule

        else:
            print(f"No valid policy found associated with schedule {schedule_name}")

def remove_disabled_policies(host, user, password):
    """Connects to the Fortinet firewall and removes any policies with expired schedules."""
    fortigate = {
        "device_type": "fortinet",
        "host": host,
        "username": user,
        "password": password,
        "port": 22,
        #"session_log": "/tmp/netmiko_log.txt",
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
