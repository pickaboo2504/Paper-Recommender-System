# backend/check_admin.py
import sys
import os
sys.path.append('.')

from database import SessionLocal
from models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def main():
    db = SessionLocal()
    
    print("=" * 50)
    print("ADMIN USER CHECK & SETUP")
    print("=" * 50)
    
    # Check current users
    users = db.query(User).all()
    
    if not users:
        print("No users found in database!")
        print("\nDo you want to create an admin user?")
        choice = input("Enter 'y' to create admin, 'n' to exit: ")
        
        if choice.lower() == 'y':
            email = input("Enter email: ")
            password = input("Enter password: ")
            full_name = input("Enter full name: ")
            
            hashed_password = pwd_context.hash(password)
            admin_user = User(
                email=email,
                hashed_password=hashed_password,
                full_name=full_name,
                is_admin=True
            )
            db.add(admin_user)
            db.commit()
            print(f"\n✓ Admin user '{email}' created successfully!")
            print(f"✓ Password hashed and stored")
            print(f"✓ Admin status: True")
        db.close()
        return
    
    print(f"\nFound {len(users)} user(s) in database:")
    print("-" * 50)
    
    for user in users:
        admin_status = "ADMIN" if user.is_admin else "User"
        print(f"ID: {user.id} | Email: {user.email} | Status: {admin_status}")
    
    print("\n" + "=" * 50)
    print("OPTIONS:")
    print("1. Make a user admin")
    print("2. Create new admin user")
    print("3. Exit")
    
    choice = input("\nEnter choice (1-3): ")
    
    if choice == "1":
        try:
            user_id = int(input("Enter user ID to make admin: "))
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.is_admin = True
                db.commit()
                print(f"\n✓ SUCCESS: User {user.email} is now admin!")
                print(f"  User ID: {user.id}")
                print(f"  Email: {user.email}")
                print(f"  Admin status updated: True")
            else:
                print(f"\n✗ ERROR: User with ID {user_id} not found")
        except ValueError:
            print("\n✗ ERROR: Please enter a valid number")
    
    elif choice == "2":
        email = input("Enter email: ")
        
        # Check if user already exists
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"\nUser '{email}' already exists!")
            make_admin = input("Make this user admin? (y/n): ")
            if make_admin.lower() == 'y':
                existing.is_admin = True
                db.commit()
                print(f"\n✓ SUCCESS: Existing user '{email}' promoted to admin!")
        else:
            password = input("Enter password: ")
            full_name = input("Enter full name: ")
            
            hashed_password = pwd_context.hash(password)
            admin_user = User(
                email=email,
                hashed_password=hashed_password,
                full_name=full_name,
                is_admin=True
            )
            db.add(admin_user)
            db.commit()
            print(f"\n✓ SUCCESS: New admin user '{email}' created!")
            print(f"  Password hashed and stored")
            print(f"  Admin status: True")
    
    db.close()
    print("\n" + "=" * 50)
    print("Done! Restart your backend if it's running.")
    print("=" * 50)

if __name__ == "__main__":
    main()