#!/usr/bin/env python
"""
Setup local PostgreSQL database for development
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys

# Database configuration
DB_NAME = 'zenith_erp_db'
DB_USER = 'zenith_user'
DB_PASSWORD = 'Zenerp@#785'
DB_HOST = 'localhost'
DB_PORT = 5432

# Connect as postgres superuser (you'll need to enter password)
print("=" * 60)
print("Setting up local PostgreSQL database for development")
print("=" * 60)
print(f"\nDatabase: {DB_NAME}")
print(f"User: {DB_USER}")
print(f"Host: {DB_HOST}:{DB_PORT}")
print("\n" + "-" * 60)

# Get postgres password
postgres_password = input("\nEnter PostgreSQL 'postgres' user password (or press Enter if no password): ").strip()

try:
    # Connect as postgres user
    print("\n1. Connecting to PostgreSQL as 'postgres' user...")
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user='postgres',
        password=postgres_password if postgres_password else None,
        database='postgres'
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    print("   ✅ Connected successfully!")
    
    # Check if user exists
    print("\n2. Checking if user exists...")
    cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (DB_USER,))
    user_exists = cursor.fetchone()
    
    if user_exists:
        print(f"   ⚠️  User '{DB_USER}' already exists. Updating password...")
        cursor.execute(f"ALTER USER {DB_USER} WITH PASSWORD %s", (DB_PASSWORD,))
        print("   ✅ Password updated!")
    else:
        print(f"   Creating user '{DB_USER}'...")
        cursor.execute(f"CREATE USER {DB_USER} WITH PASSWORD %s", (DB_PASSWORD,))
        print("   ✅ User created!")
    
    # Check if database exists
    print("\n3. Checking if database exists...")
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
    db_exists = cursor.fetchone()
    
    if db_exists:
        print(f"   ⚠️  Database '{DB_NAME}' already exists.")
        response = input("   Delete and recreate? (yes/no): ").strip().lower()
        if response == 'yes':
            print(f"   Dropping database '{DB_NAME}'...")
            cursor.execute(f"DROP DATABASE {DB_NAME}")
            print("   ✅ Database dropped!")
        else:
            print("   Keeping existing database.")
            cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO {DB_USER}")
            print("   ✅ Permissions granted!")
            conn.close()
            print("\n" + "=" * 60)
            print("✅ Setup complete! Database already exists.")
            print("=" * 60)
            sys.exit(0)
    
    if not db_exists or (db_exists and response == 'yes'):
        print(f"   Creating database '{DB_NAME}'...")
        cursor.execute(f"CREATE DATABASE {DB_NAME} OWNER {DB_USER}")
        print("   ✅ Database created!")
    
    # Grant privileges
    print("\n4. Granting privileges...")
    cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO {DB_USER}")
    print("   ✅ Privileges granted!")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ Setup complete!")
    print("=" * 60)
    print(f"\nYou can now run: python manage.py runserver")
    print("\nDatabase configuration:")
    print(f"  DB_NAME={DB_NAME}")
    print(f"  DB_USER={DB_USER}")
    print(f"  DB_HOST={DB_HOST}")
    print(f"  DB_PORT={DB_PORT}")
    
except psycopg2.OperationalError as e:
    print(f"\n❌ Error: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure PostgreSQL is running")
    print("2. Check if 'postgres' user password is correct")
    print("3. Try connecting with pgAdmin to verify credentials")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Unexpected error: {e}")
    sys.exit(1)

