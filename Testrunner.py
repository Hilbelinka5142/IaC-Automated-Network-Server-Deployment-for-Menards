import subprocess

# Defining the options to playbook maping
playbooks = {
	"webserver": ["Ansible-Playbooks/CreateVM.yaml"]
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
	   print(result.stdout.decode())
	
	except subprocess.CalledProcessError as e:
	   print(f"Error while executing playbook {playbook}:\n{e.stderr.decode()}")





"""
if creating web server
    call webserver ansible playbook (Pass input variables from site)
    call firewall policies playbook
        allow RDP, HTTPS, SSH ports

    wait until webserver pings == success 
        web server was created successfully
        output IP address of webserver

"""
