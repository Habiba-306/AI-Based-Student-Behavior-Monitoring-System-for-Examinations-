import json
from werkzeug.security import generate_password_hash

def load_users():
    try:
        with open('users.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    with open('users.json', 'w') as f:
        json.dump(users, f, indent=4)

def add_user():
    print("\n🛡️  ExamGuard User Registration Tool")
    print("====================================")
    
    username = input("Enter new username: ").strip()
    
    if not username:
        print("❌ Error: Username cannot be empty.")
        return

    users = load_users()
    if username in users:
        print(f"❌ Error: User '{username}' already exists.")
        return

    # simple input for now as getpass might be hidden in some terminals, 
    # but standard input is safer for this environment interaction
    password = input("Enter password: ")
    confirm = input("Confirm password: ")
    
    if password != confirm:
        print("❌ Error: Passwords do not match.")
        return
        
    role = input("Enter role (admin/user) [user]: ").strip().lower() or 'user'
    
    # Store the hashed password
    users[username] = {
        "password": generate_password_hash(password),
        "role": role,
        "name": username.title()
    }
    
    save_users(users)
    print(f"\n✅ User '{username}' registered successfully!")
    print(f"   Role: {role}")
    print("   You can now log in with these credentials.")

if __name__ == '__main__':
    add_user()
