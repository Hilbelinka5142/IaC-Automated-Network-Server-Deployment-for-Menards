import subprocess

vmName = input("Enter the VM Name: ")

playbook = "Ansible-Playbooks/CreateVM.yaml"

extra_vars = f"vmName={vmName}"

try:
   results = subprocess.run(
	["ansible-playbook", playbook, "--extra-vars", extra_vars],
	check=True,
	text=True,
	capture_output=True
   )
   print("Playbook Output:\n", results.stdout)
except subprocess.CalledProcessError as e:
   print("Error running playbook:\n", e.stderr)




"""
if creating web server
    call webserver ansible playbook (Pass input variables from site)
    call firewall policies playbook
        allow RDP, HTTPS, SSH ports

    wait until webserver pings == success 
        web server was created successfully
        output IP address of webserver

"""
