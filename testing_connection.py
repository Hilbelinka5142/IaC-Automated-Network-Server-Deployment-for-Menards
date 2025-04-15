from netmiko import ConnectHandler

def test_ssh_connection():
    # Firewall connection details
    fortigate = {
        "device_type": "fortinet",
        "host": "10.0.1.1",  # Firewall IP address
        "username": "Ansible",  # Your username
        "password": "password",  # Your password
        "port": 22,  # Default SSH port
    }

    try:
        # Establish SSH connection using Netmiko
        net_connect = ConnectHandler(**fortigate)
        
        # Send a simple command to verify connection
        output = net_connect.send_command("get system status")
        print("Connection successful. Firewall status:\n", output)

        # Close the connection
        net_connect.disconnect()

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_ssh_connection()
