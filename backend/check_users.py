# backend/check_users.py
import sys
sys.path.append('.')

from database import SessionLocal, Base, engine
from models import User
from passlib.context import CryptContext
import os

def setup_admin():
    db = SessionLocal()
    
    print("=" * 60)
    print("PAPER RECOMMENDATION PLATFORM - ADMIN SETUP")
    print("=" * 60)
    
    # First, make sure tables exist
    try:
        Base.metadata.create_all(bind=engine)
        print("✓ Database tables checked/created")
    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        return
    
    # Check existing users
    users = db.query(User).all()
    
    if users:
        print(f"\n📊 Found {len(users)} user(s):")
        print("-" * 60)
        for user in users:
            admin_icon = "👑" if user.is_admin else "👤"
            print(f"{admin_icon} ID: {user.id} | Email: {user.email} | Admin: {user.is_admin}")
        
        print("\n" + "=" * 60)
        print("What would you like to do?")
        print("1. Make an existing user admin")
        print("2. Create a new admin user")
        print("3. Just show current users")
        
        choice = input("\nEnter choice (1-3): ")
        
        if choice == "1":
            try:
                user_id = int(input("Enter user ID to make admin: "))
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user.is_admin = True
                    db.commit()
                    print(f"\n✅ SUCCESS! User '{user.email}' is now an administrator.")
                    print(f"   You can now access the admin dashboard.")
                else:
                    print(f"\n❌ User with ID {user_id} not found.")
            except ValueError:
                print("\n❌ Please enter a valid number.")
        
        elif choice == "2":
            print("\nCreating new admin user...")
            email = input("Email: ").strip()
            password = input("Password: ").strip()
            full_name = input("Full name: ").strip()
            
            # Check if user exists
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                print(f"\n⚠️  User '{email}' already exists.")
                make_admin = input("Make this user admin? (y/n): ").lower()
                if make_admin == 'y':
                    existing.is_admin = True
                    db.commit()
                    print(f"\n✅ Existing user '{email}' promoted to admin!")
            else:
                pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
                hashed_password = pwd_context.hash(password)
                
                new_user = User(
                    email=email,
                    hashed_password=hashed_password,
                    full_name=full_name,
                    is_admin=True
                )
                db.add(new_user)
                db.commit()
                print(f"\n✅ New admin user '{email}' created successfully!")
                print(f"   You can login with email: {email}")
                print(f"   Password: {password}")
        
        elif choice == "3":
            print("\nCurrent users:")
            for user in users:
                status = "Admin" if user.is_admin else "User"
                print(f"  - {user.email} ({status})")
    
    else:
        print("\n📭 No users found in database.")
        print("\nLet's create the first admin user...")
        print("-" * 60)
        
        email = input("Admin email: ").strip()
        password = input("Admin password: ").strip()
        full_name = input("Full name: ").strip()
        
        pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
        hashed_password = pwd_context.hash(password)
        
        admin_user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            is_admin=True
        )
        
        db.add(admin_user)
        db.commit()
        
        print(f"\n🎉 FIRST ADMIN USER CREATED!")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   Name: {full_name}")
        print(f"\n💡 This user will be the platform administrator.")
    
    db.close()
    
    print("\n" + "=" * 60)
    print("NEXT STEPS:")
    print("1. Restart your backend server (if running)")
    print("2. Login with your admin account")
    print("3. Go to /admin in your browser")
    print("=" * 60)

if __name__ == "__main__":
    setup_admin()