import json
import os
import smtplib
from email.message import EmailMessage

# Directory containing request files
REQUESTS_DIR ="/home/deploymentvm/Desktop/Automation_frontend/IaC-Automated-Network-Server-Deployment-for-Menards/automation-frontend/requests"

def get_latest_json_file():
    files = [f for f in os.listdir(REQUESTS_DIR) if f.startswith("request_") and f.endswith(".json")]
    if not files:
        raise FileNotFoundError("No request files found in the 'requests' directory.")
    files.sort(reverse=True)
    return os.path.join(REQUESTS_DIR, files[0])

def load_credentials():
    path = get_latest_json_file()
    with open(path, "r") as file:
        data = json.load(file)
        return {
            "email": data.get("email"),
            "username": data.get("username"),
            "password": data.get("password")
        }

def send_email(email, username, password):
    sender = "nsat.no.reply@gmail.com"
    sender_password = "smafaffdtfyptihj"  # No spaces

    msg = EmailMessage()
    msg['Subject'] = "Your VM Credentials"
    msg['From'] = sender
    msg['To'] = email
    msg.set_content(f"""
Hello,

Your VM has been created! Here are your credentials:

Username: {username}
Password: {password}

Please log in and change your password as soon as possible.

Thanks,

NSAT Team

- Don't reply to this email
    """)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender, sender_password)
            smtp.send_message(msg)
            print(f"Email successfully sent to {email}!")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    try:
        creds = load_credentials()
        send_email(creds["email"], creds["username"], creds["password"])
    except Exception as e:
        print(f"Failed to send credentials: {e}")
