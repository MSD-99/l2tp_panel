"""
CLI script to create the first admin user.
There is deliberately no public web signup route - creating/changing a
user's role is only possible via console (sudo) access to the server
itself.

Usage:
    python3 create_admin.py
"""
import getpass
import sys

from app.database import SessionLocal, Base, engine
from app.models import User, UserRole
from app.security import hash_password

Base.metadata.create_all(bind=engine)


def main():
    db = SessionLocal()
    try:
        username = input("New admin username: ").strip()
        if not username:
            print("[!] Username cannot be empty.")
            sys.exit(1)

        existing = db.query(User).filter(User.username == username).first()
        if existing:
            print(f"[!] A user named '{username}' already exists.")
            sys.exit(1)

        password = getpass.getpass("Password: ")
        password_confirm = getpass.getpass("Confirm password: ")
        if password != password_confirm:
            print("[!] Passwords do not match.")
            sys.exit(1)
        if len(password) < 8:
            print("[!] Password must be at least 8 characters long.")
            sys.exit(1)

        user = User(
            username=username,
            password_hash=hash_password(password),
            role=UserRole.admin,
        )
        db.add(user)
        db.commit()
        print(f"[OK] Admin user '{username}' was created successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
