"""Test backend and database connectivity"""
import requests
import sys
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

def test_backend():
    """Test if backend is running"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Backend returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Backend not running at {API_URL}")
        print("   Start it with: python backend/main.py")
        return False
    except Exception as e:
        print(f"❌ Backend test failed: {e}")
        return False

def test_database():
    """Test if database connection works"""
    try:
        # Try to get sessions (requires DB connection)
        response = requests.get(f"{API_URL}/sessions", timeout=5)
        if response.status_code == 200:
            print("✅ Database connected")
            sessions = response.json()
            print(f"   Found {len(sessions)} sessions")
            return True
        else:
            print(f"❌ Database query failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_create_screen():
    """Test creating a screen"""
    try:
        data = {
            "name": "test_connection",
            "url": "http://test.com",
            "title": "Test Connection",
            "session_id": "test_session"
        }
        response = requests.post(f"{API_URL}/screens", json=data, timeout=5)
        if response.status_code in [200, 201]:
            print("✅ Can create screens")
            print(f"   Screen ID: {response.json().get('id')}")
            return True
        else:
            print(f"❌ Create screen failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Create screen test failed: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("Testing Backend & Database Connection")
    print("="*60 + "\n")
    
    results = []
    
    print("1. Testing Backend...")
    results.append(test_backend())
    print()
    
    if results[0]:
        print("2. Testing Database...")
        results.append(test_database())
        print()
        
        print("3. Testing Write Operations...")
        results.append(test_create_screen())
        print()
    
    print("="*60)
    if all(results):
        print("✅ ALL TESTS PASSED - System is ready")
    else:
        print("❌ SOME TESTS FAILED - Check errors above")
    print("="*60 + "\n")
    
    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
