#!/usr/bin/env python
import os
import sys
import django
import requests
import json

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

def test_login_api():
    """Test the login API to get a valid token"""
    
    print("Testing login API...")
    print("-" * 40)
    
    # Test login
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    try:
        response = requests.post('http://localhost:8000/api/login/', json=login_data)
        print(f"Login response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Login successful!")
            print(f"Access token: {data.get('access', 'Not found')[:50]}...")
            print(f"Refresh token: {data.get('refresh', 'Not found')[:50]}...")
            
            # Test the medicine search API with the token
            headers = {
                'Authorization': f"Bearer {data['access']}"
            }
            
            search_response = requests.get(
                'http://localhost:8000/api/pharmacy/medicines/search/?barcode=8901234567890',
                headers=headers
            )
            
            print(f"\nMedicine search response status: {search_response.status_code}")
            if search_response.status_code == 200:
                search_data = search_response.json()
                print("✅ Medicine search successful!")
                print(f"Response: {json.dumps(search_data, indent=2)}")
            else:
                print(f"❌ Medicine search failed: {search_response.text}")
                
        else:
            print(f"❌ Login failed: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the server is running.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    test_login_api() 