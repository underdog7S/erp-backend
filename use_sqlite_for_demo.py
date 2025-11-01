"""
Quick script to switch to SQLite for local demo data creation
Run this before creating demo data if PostgreSQL is not configured
"""
import os

env_file = '.env'
sqlite_config = """# Temporary SQLite configuration for local demo
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

# PostgreSQL settings (commented out for demo)
# DB_ENGINE=django.db.backends.postgresql
# DB_NAME=zenith_erp_db
# DB_USER=zenith_user
# DB_PASSWORD=Zenerp@#785
# DB_HOST=localhost
# DB_PORT=5432
"""

if os.path.exists(env_file):
    # Backup existing .env
    with open(env_file, 'r') as f:
        existing = f.read()
    with open('.env.backup', 'w') as f:
        f.write(existing)
    print("✅ Backed up existing .env to .env.backup")

# Write SQLite config
with open(env_file, 'w') as f:
    f.write(sqlite_config)

print("✅ Updated .env to use SQLite")
print("📝 Now run: python manage.py migrate")
print("📝 Then run: python manage.py create_demo_data --create-demo-user")

