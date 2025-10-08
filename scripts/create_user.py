import sys
import os
import argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import init_db, create_user_db, get_user_by_username
from security import SecurityConfig


def create_user(username, plaintext_password, email):
    # Validate inputs
    is_valid_username, username_error = SecurityConfig.validate_username(username)
    if not is_valid_username:
        print(f"Error: {username_error}")
        return False

    is_valid_email, email_error = SecurityConfig.validate_email(email)
    if not is_valid_email:
        print(f"Error: {email_error}")
        return False

    is_valid_password, password_error = SecurityConfig.validate_password(plaintext_password)
    if not is_valid_password:
        print(f"Error: {password_error}")
        return False

    # Sanitize
    username = SecurityConfig.sanitize_input(username)
    email = SecurityConfig.sanitize_input(email)

    # Ensure DB exists
    init_db()

    # Check existing user
    if get_user_by_username(username):
        print(f"Error: Username '{username}' already exists.")
        return False

    # Hash and create
    password_hash = SecurityConfig.hash_password(plaintext_password)
    success = create_user_db(username, email, password_hash)
    if success:
        print(f"✅ Created user '{username}' in database.")
        return True
    else:
        print("❌ Failed to create user (username or email may already exist).")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a user in the database")
    parser.add_argument("username", help="Username")
    parser.add_argument("password", help="Password")
    parser.add_argument("email", help="Email")
    args = parser.parse_args()

    ok = create_user(args.username, args.password, args.email)
    sys.exit(0 if ok else 1)
