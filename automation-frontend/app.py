import os
import json
import subprocess
import random
import string
import crypt
from flask import Flask, render_template, request
from datetime import datetime

# Initialize the Flask app
app = Flask(__name__)

# Define and create a directory to store submitted request files
REQUESTS_DIR = os.path.join(os.path.dirname(__file__), 'requests')
os.makedirs(REQUESTS_DIR, exist_ok=True)

# Route to serve the HTML form when visiting the root URL
@app.route('/', methods=['GET'])
def form():
    return render_template('index.html')

# Route to handle form submission (POST request to /submit)
@app.route('/submit', methods=['POST'])
def submit():
    # Extract form data from the request
    try:
        requester_first_name = request.form.get('requester_first_name')
        requester_last_name = request.form.get('requester_last_name')
        email = request.form.get('email')
        vm_name = request.form.get('vm_name')
        cpu = int(request.form.get('cpu'))
        memory = int(request.form.get('memory'))
        storage = int(request.form.get('storage'))
        os_type = request.form.get('os')
        expiration = request.form.get('expiration')
        firewall_services_raw = request.form.get('firewall_services', '')
        firewall_services = [s.strip() for s in firewall_services_raw.split(',') if s.strip()]
        reason = request.form.get('reason')

        # Basic validation rules
        if not all([requester_first_name, requester_last_name, email, vm_name, cpu, memory, storage, os_type, expiration, firewall_services, reason]):
            return "All fields are required.", 400

        if not (2 <= cpu <= 16):
            return "CPU cores must be between 2 and 16.", 400

        if not (4 <= memory <= 64):
            return "Memory must be between 4 and 64 GB.", 400

        if not (64 <= storage <= 500):
            return "Storage must be between 64 and 500 GB.", 400
        
        # Check for duplicate VM name from existing requests folder
        # If any duplicates exist, it immediately stops and returns an error back to the user
        for filename in os.listdir(REQUESTS_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(REQUESTS_DIR, filename)
                with open(filepath, 'r') as f:
                    existing_data = json.load(f)
                    if existing_data.get('vm_name') == vm_name:
                        return f"A VM with the name '{vm_name}' already exists. Please choose a different name.", 400

        
        # Creates a username based off requester's first initial and full last name
        username = (requester_first_name[0] + requester_last_name).lower()

        # Generates a random password for the user
        def generate_password(length=16):
            characters = string.ascii_letters + string.digits
            return ''.join(random.choices(characters, k=length))
        
        password = generate_password()
        
        # Hashes the generated password for secure Ubuntu server login
        password_hash = crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512))

        
        # Create a dictionary containing all user-submitted form data
        # along with the generated password and password hash.
        # This dictionary will later be saved as a JSON file to be used 
        # by backend automation scripts and dynamic ISO generation.
        data = {
            'requester_first_name': requester_first_name,
            'requester_last_name': requester_last_name,
            'email': email,
            'username': username,
            'password': password,                 # Plaintext password for email notification
            'password_hash': password_hash,       # Hashed password for secure Ubuntu server login
            'vm_name': vm_name,
            'cpu': cpu,
            'memory': memory,
            'storage': storage,
            'os': os_type,
            'expiration': expiration,
            'firewall_services': firewall_services,
            'reason': reason
        }

        # Generate a timestamped filename to save the request
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"request_{timestamp}.json"
        filepath = os.path.join(REQUESTS_DIR, filename)

        # Save the form data as a JSON file in the requests directory
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)

        # Log the submission for confirmation/debugging
        print(f"Form submitted: {data}")
        print(f"Saved request to: {filepath}")
        
        #Automatically run preview_requests.py after submission
        subprocess.Popen(['python3', 'preview_requests.py'])

        # Return a basic success message to the user
        return "Request submitted and saved successfully!<br>Your VM credentials will be emailed to you once completed!"
    
    except Exception as e:
        print(f"Error processing form: {e}")
        return f"An error occurred: {str(e)}", 500

# Run the Flask development server
if __name__ == '__main__':
    app.run(debug=True)
