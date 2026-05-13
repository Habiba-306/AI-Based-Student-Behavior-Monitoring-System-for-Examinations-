import json
from werkzeug.security import generate_password_hash

users = {
    "admin": {
        "password": generate_password_hash("admin123"),
        "role": "admin",
        "name": "System Administrator"
    },
    "invigilator": {
        "password": generate_password_hash("exam2025"),
        "role": "user",
        "name": "Exam Invigilator"
    }
}

with open('users.json', 'w') as f:
    json.dump(users, f, indent=4)

print("✅ users.json created with default users!")
print("   - admin / admin123")
print("   - invigilator / exam2025")
