import subprocess
import time

# Defining the options to playbook maping
playbooks = {
	"webserver": ["Ansible-Playbooks/CreateVM.yaml, Firewall"] #add path to other playbooks that will need to be called
	#"windows": ["PATH"]
}

# Function for running a playbook
def runPlaybook(playbook):

	try:
		results = subprocess.run(
			["ansible-playbook", playbook],
			check=True,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE
	    )

		print(f"Playbook {playbook} excuted successfully!")
		print(results.stdout.decode())
	except subprocess.CalledProcessError as e:
		print(f"Error while executing playbook {playbook}:\n{e.stderr.decode()}")
		return False
	return True

def checkServerStatus(ipAddress):
	try:
		result = subprocess.run(
			["ping", "-c", "4", ipAddress],  # Adjust "-c" for Windows or other platforms
			check=True,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE
		)
		print(f"Server at {ipAddress} is up!")
		return True
	except subprocess.CalledProcessError:
		print(f"Server at {ipAddress} is not reachable.")
		return False
	
#Runs the createVM playbook as well as the firewall playbook
def createVM():
	print("Starting VM creation...")
	
	#runs the webserver playbook
	if not runPlaybook(playbooks["webserver"][0]):
		return #stops if playbook fails
	
	#runs the firewall playbook
	if not runPlaybook(playbooks["webserver"][1]):
		return #stops if playbook fails
	
	# Get's the Ip of the new VM
	vmIP = ""

	while not checkServerStatus(vmIP):
		print("Waiting for VM to come online...")
		time.sleep(10) #waits 10 seconds before retrying

	print(f"Your VM was successfully created with the IP address of: {vmIP}")


createVM()

"""
if creating web server
    call webserver ansible playbook (Pass input variables from site)
    call firewall policies playbook
        allow RDP, HTTPS, SSH ports

    wait until webserver pings == success 
        web server was created successfully
        output IP address of webserver

# Function to check if the web server is up and running (ping)
def check_server_status(ip_address):
	try:
		result = subprocess.run(
			["ping", "-c", "4", ip_address],  # Adjust "-c" for Windows or other platforms
			check=True,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE
		)
		print(f"Server at {ip_address} is up!")
		return True
	except subprocess.CalledProcessError:
		print(f"Server at {ip_address} is not reachable.")
		return False

"""
