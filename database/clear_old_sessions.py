import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import engine
from sqlalchemy import text

def clear_old_sessions():
    """Delete all sessions except the most recent one"""
    print("\n" + "="*60)
    print("CLEARING OLD SESSIONS")
    print("="*60)
    
    try:
        with engine.connect() as conn:
            # Get all sessions ordered by creation date
            sessions = conn.execute(text("""
                SELECT session_id, MIN(created_at) as created_at, COUNT(*) as page_count
                FROM screens 
                WHERE session_id IS NOT NULL 
                GROUP BY session_id 
                ORDER BY MIN(created_at) DESC
            """)).fetchall()
            
            if len(sessions) == 0:
                print("\n  No sessions found.")
                return
            
            print(f"\n  Found {len(sessions)} session(s):")
            for i, session in enumerate(sessions):
                status = "KEEPING" if i == 0 else "DELETING"
                print(f"    [{status}] {session[0]} - {session[1]} ({session[2]} pages)")
            
            if len(sessions) <= 1:
                print("\n  Only 1 session exists. Nothing to delete.")
                return
            
            # Keep only the most recent session
            sessions_to_delete = [s[0] for s in sessions[1:]]
            
            # Delete elements first (foreign key constraint)
            for session_id in sessions_to_delete:
                result = conn.execute(text("""
                    DELETE FROM elements 
                    WHERE screen_id IN (
                        SELECT id FROM screens WHERE session_id = :session_id
                    )
                """), {"session_id": session_id})
                print(f"\n  Deleted {result.rowcount} elements from {session_id}")
            
            # Delete screens
            for session_id in sessions_to_delete:
                result = conn.execute(text("""
                    DELETE FROM screens WHERE session_id = :session_id
                """), {"session_id": session_id})
                print(f"  Deleted {result.rowcount} screens from {session_id}")
            
            conn.commit()
            
            print("\n" + "="*60)
            print("OLD SESSIONS CLEARED SUCCESSFULLY")
            print("="*60)
            print(f"\nKept: {sessions[0][0]}")
            print(f"Deleted: {len(sessions_to_delete)} old session(s)\n")
            
    except Exception as e:
        print(f"\n  ERROR: {e}\n")

if __name__ == "__main__":
    clear_old_sessions()
