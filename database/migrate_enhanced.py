import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import engine
from sqlalchemy import text

def migrate():
    print("Adding enhanced metadata columns...")
    
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE elements ADD COLUMN parent_element VARCHAR(200)"))
            print("[OK] Added parent_element")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("  parent_element already exists")
            else:
                print(f"[FAIL] parent_element: {e}")
        
        try:
            conn.execute(text("ALTER TABLE elements ADD COLUMN interaction_type VARCHAR(50)"))
            print("[OK] Added interaction_type")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("  interaction_type already exists")
            else:
                print(f"[FAIL] interaction_type: {e}")
        
        try:
            conn.execute(text("ALTER TABLE elements ADD COLUMN element_context TEXT"))
            print("[OK] Added element_context")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("  element_context already exists")
            else:
                print(f"[FAIL] element_context: {e}")
        
        try:
            conn.execute(text("ALTER TABLE elements ADD COLUMN selector_priority INTEGER DEFAULT 3"))
            print("[OK] Added selector_priority")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("  selector_priority already exists")
            else:
                print(f"[FAIL] selector_priority: {e}")
        
        try:
            conn.execute(text("ALTER TABLE elements ADD COLUMN form_group VARCHAR(100)"))
            print("[OK] Added form_group")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("  form_group already exists")
            else:
                print(f"[FAIL] form_group: {e}")
        
        try:
            conn.execute(text("ALTER TABLE elements ADD COLUMN requires_wait BOOLEAN DEFAULT FALSE"))
            print("[OK] Added requires_wait")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("  requires_wait already exists")
            else:
                print(f"[FAIL] requires_wait: {e}")
        
        conn.commit()
    
    print("\nMigration complete! Enhanced metadata fields added.")

if __name__ == "__main__":
    migrate()
