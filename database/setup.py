import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import create_tables, engine
from sqlalchemy import text
import requests
import os

def test_integration():
    """Test database and API integration"""
    print("\n" + "="*60)
    print("TESTING DATABASE & API INTEGRATION")
    print("="*60)
    
    # Test 1: Database Connection
    print("\n[1] Testing Database Connection...")
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1")).scalar()
            print("    OK - Database connected")
    except Exception as e:
        print(f"    FAIL - Database: {e}")
        return
    
    # Test 2: Check Tables
    print("\n[2] Checking Tables...")
    try:
        with engine.connect() as conn:
            screens = conn.execute(text("SELECT COUNT(*) FROM screens")).scalar()
            elements = conn.execute(text("SELECT COUNT(*) FROM elements")).scalar()
            with_session = conn.execute(text("SELECT COUNT(*) FROM screens WHERE session_id IS NOT NULL")).scalar()
            print(f"    OK - screens: {screens}, elements: {elements}")
            print(f"    OK - With session_id: {with_session}")
    except Exception as e:
        print(f"    FAIL - Tables: {e}")
        return
    
    # Test 3: API Server
    print("\n[3] Testing API Server...")
    try:
        response = requests.get("http://localhost:8000/screens", timeout=5)
        print(f"    OK - API running (status: {response.status_code})")
        
        sessions = requests.get("http://localhost:8000/sessions").json()
        print(f"    OK - Sessions endpoint: {len(sessions)} sessions")
        
        if len(sessions) > 0:
            print(f"    Latest: {sessions[0]['session_id']} ({sessions[0]['elements_count']} elements)")
    except requests.exceptions.ConnectionError:
        print("    FAIL - API not running. Start: python backend/main.py")
        return
    except Exception as e:
        print(f"    FAIL - API: {e}")
        return
    
    print("\n" + "="*60)
    print("INTEGRATION TEST PASSED")
    print("="*60)
    print("\nDatabase and API are successfully integrated!\n")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_integration()
        return
    
    print("Creating enhanced database tables for state-based crawling...")
    try:
        create_tables()
        
        # Add session_id column if it doesn't exist
        with engine.connect() as conn:
            try:
                conn.execute(text("ALTER TABLE screens ADD COLUMN session_id VARCHAR(100)"))
                conn.execute(text("CREATE INDEX ix_screens_session_id ON screens (session_id)"))
                conn.commit()
                print("Added session_id column")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print("session_id column already exists")
                else:
                    raise e
        
        print("Enhanced database tables created successfully!")
        print("Ready to run state-based crawler!")
    except Exception as e:
        print(f"Error creating tables: {e}")

if __name__ == "__main__":
    main()