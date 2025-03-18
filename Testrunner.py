import subprocess

vmName = input("Enter the VM Name: ")

playbook = "CreateVM.yaml"

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
