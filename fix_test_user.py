#!/usr/bin/env python
import os
import sys
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from api.models import UserProfile

def check_and_fix_test_user():
    print("🔍 Checking test user authentication...")
    
    # Check if testuser exists
    try:
        user = User.objects.get(username='testuser')
        print(f"✅ User 'testuser' exists (ID: {user.id})")
        print(f"   Email: {user.email}")
        print(f"   Is active: {user.is_active}")
        print(f"   Is staff: {user.is_staff}")
        print(f"   Is superuser: {user.is_superuser}")
        
        # Check if user profile exists
        try:
            profile = UserProfile.objects.get(user=user)
            print(f"   Role: {profile.role}")
            print(f"   Department: {profile.department}")
        except UserProfile.DoesNotExist:
            print("   ❌ No user profile found")
            return False
            
    except User.DoesNotExist:
        print("❌ User 'testuser' does not exist")
        return False
    
    # Test authentication
    print("\n🔐 Testing authentication...")
    auth_user = authenticate(username='testuser', password='testpass123')
    
    if auth_user:
        print("✅ Authentication successful!")
        return True
    else:
        print("❌ Authentication failed")
        print("   Trying to reset password...")
        
        # Reset password
        user.set_password('testpass123')
        user.save()
        print("✅ Password reset to 'testpass123'")
        
        # Test again
        auth_user = authenticate(username='testuser', password='testpass123')
        if auth_user:
            print("✅ Authentication now successful!")
            return True
        else:
            print("❌ Authentication still failing")
            return False

def create_test_user_if_needed():
    print("\n🔧 Creating test user if needed...")
    
    try:
        user = User.objects.get(username='testuser')
        print("✅ Test user already exists")
        return user
    except User.DoesNotExist:
        print("Creating new test user...")
        
        # Create user
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        # Create profile
        profile = UserProfile.objects.create(
            user=user,
            role=4,  # Accountant role
            department='Finance',
            phone='1234567890'
        )
        
        print("✅ Test user created successfully!")
        print(f"   Username: testuser")
        print(f"   Password: testpass123")
        print(f"   Role: Accountant (ID: 4)")
        return user

def main():
    print("🚀 ERP Test User Authentication Fix\n")
    
    # Create test user if needed
    user = create_test_user_if_needed()
    
    # Check and fix authentication
    if check_and_fix_test_user():
        print("\n🎉 Test user authentication is working!")
        print("\n📋 Test Credentials:")
        print("   Username: testuser")
        print("   Password: testpass123")
        print("   Role: Accountant")
        
        print("\n🚀 Next Steps:")
        print("1. Go to http://localhost:3000/login")
        print("2. Login with the credentials above")
        print("3. Test the role-based dashboards")
        print("4. Run the test suite again")
        
    else:
        print("\n❌ Authentication fix failed")
        print("Please check Django logs for errors")

if __name__ == "__main__":
    main() 