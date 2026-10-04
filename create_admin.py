"""Create an admin account from the terminal.

Run once after importing schema.sql and creating your .env file:
    python create_admin.py
The password is typed at the prompt, hashed, and never stored as plain text.
"""
import getpass
import re

from dotenv import load_dotenv

load_dotenv()

from mysql.connector import Error, IntegrityError, errorcode
from werkzeug.security import generate_password_hash

from models import AdminModel, Database


def main():
    username = input("Admin username (3-30 letters, numbers, underscores): ").strip()
    if not re.fullmatch(r"[A-Za-z0-9_]{3,30}", username):
        print("Invalid username.")
        return

    password = getpass.getpass("Admin password (at least 8 characters): ")
    confirm = getpass.getpass("Confirm password: ")
    if len(password) < 8:
        print("Password must be at least 8 characters.")
        return
    if password != confirm:
        print("Passwords do not match.")
        return

    try:
        AdminModel(Database()).create(username, generate_password_hash(password))
    except IntegrityError as error:
        if error.errno == errorcode.ER_DUP_ENTRY:
            print("That admin username already exists.")
        else:
            print("Database error:", error)
        return
    except Error as error:
        print("Could not connect to the database. Check your .env file.")
        print("Details:", error)
        return

    print("Admin account created. You can log in at /admin/login.")


if __name__ == "__main__":
    main()
