import requests  # Fixed: changed 'request' to 'requests'
import uuid
import json
import time

BASE_URL_AUTH = "http://localhost:8000/api/v1/auth"
BASE_URL_ADMIN = "http://localhost:8000/api/v1/admin/interviews"
BASE_URL_CANDIDATE = "http://localhost:8000/api/v1/candidate/interviews"
BASE_URL_SESSION = "http://localhost:8000/api/v1/session"
BASE_URL_SUBMIT = "http://localhost:8000/api/v1/submit/submit"

# Fixed username and password
admin_user = "admin"
admin_email = "admin@example.com" 
password = "admin"

admin_payload = {
    "username": admin_user,
    "email": admin_email,
    "password": password,
    "role": "admin",
    "profile": {
        "first_name": "HR",
        "last_name": "Manager",
        "department": "Data Science Hiring",
        "designation": "Lead Recruiter"
    }
}

print(f"Registering admin: {admin_user}")
resp = requests.post(f"{BASE_URL_AUTH}/register/admin", json=admin_payload)
print(f"Status Code: {resp.status_code}")
if resp.status_code == 201:
    print("✓ Admin registered successfully")
    print(f"  Username: {admin_user}")
    print(f"  Password: {password}")
else:
    print(f"✗ Registration failed: {resp.text}")