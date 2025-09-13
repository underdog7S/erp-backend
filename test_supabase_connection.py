#!/usr/bin/env python3
"""
Test script to verify Supabase connection and database setup
"""
import os
import sys
import django
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_dir))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings_production')

# Setup Django
django.setup()

def test_supabase_client():
    """Test Supabase client connection"""
    try:
        from erp.supabase_config import get_supabase_client
        
        print("🔗 Testing Supabase client connection...")
        supabase = get_supabase_client()
        
        # Test a simple query
        result = supabase.table('todos').select('*').limit(1).execute()
        print("✅ Supabase client connection successful!")
        print(f"📊 Found {len(result.data)} todos in the database")
        
        return True
    except Exception as e:
        print(f"❌ Supabase client connection failed: {e}")
        return False

def test_django_database():
    """Test Django database connection"""
    try:
        from django.db import connection
        
        print("\n🔗 Testing Django database connection...")
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print("✅ Django database connection successful!")
            print(f"📊 PostgreSQL version: {version[0]}")
        
        return True
    except Exception as e:
        print(f"❌ Django database connection failed: {e}")
        return False

def test_django_migrations():
    """Test Django migrations"""
    try:
        from django.core.management import execute_from_command_line
        
        print("\n🔗 Testing Django migrations...")
        execute_from_command_line(['manage.py', 'showmigrations'])
        print("✅ Django migrations check completed!")
        
        return True
    except Exception as e:
        print(f"❌ Django migrations check failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Starting Supabase Integration Tests...\n")
    
    # Check environment variables
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY',
        'SUPABASE_DB_PASSWORD'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n📝 Please set these variables in your .env file")
        print("   See supabase_env_template.txt for reference")
        return False
    
    print("✅ All required environment variables are set")
    
    # Run tests
    tests = [
        test_django_database,
        test_supabase_client,
        test_django_migrations
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    # Summary
    print(f"\n📊 Test Results: {sum(results)}/{len(results)} tests passed")
    
    if all(results):
        print("🎉 All tests passed! Supabase integration is ready!")
        print("\n📋 Next steps:")
        print("1. Run migrations: python manage.py migrate")
        print("2. Create superuser: python manage.py createsuperuser")
        print("3. Start your Django server: python manage.py runserver")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
    
    return all(results)

if __name__ == "__main__":
    main()