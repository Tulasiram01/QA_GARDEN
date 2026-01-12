import json
import sys
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Screen, Element

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///locator_system.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def export_session_to_json(session_id: str, output_file: str = None):
    """Export session data to JSON in vertical format"""
    
    if not output_file:
        output_file = f"{session_id}.json"
    
    db = SessionLocal()
    
    try:
        screens = db.query(Screen).filter(Screen.session_id == session_id).all()
        
        if not screens:
            print(f"Session {session_id} not found")
            return False
        
        data = {
            "session_id": session_id,
            "total_pages": len(screens),
            "total_elements": 0,
            "pages": []
        }
        
        total_elements = 0
        
        for screen in screens:
            elements = db.query(Element).filter(Element.screen_id == screen.id).all()
            total_elements += len(elements)
            
            page_data = {
                "url": screen.url,
                "name": screen.name,
                "title": screen.title,
                "element_count": len(elements),
                "elements": []
            }
            
            for elem in elements:
                elem_dict = {
                    "element_name": elem.element_name,
                    "element_type": elem.element_type,
                    "element_id": elem.element_id,
                    "data_testid": elem.data_testid,
                    "aria_label": elem.aria_label,
                    "role": elem.role,
                    "text_content": elem.text_content,
                    "css_selector": elem.css_selector,
                    "xpath": elem.xpath,
                    "verified": elem.verified,
                    "stability_score": elem.stability_score
                }
                page_data["elements"].append(elem_dict)
            
            data["pages"].append(page_data)
        
        data["total_elements"] = total_elements
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Exported {total_elements} elements from {len(screens)} pages")
        print(f"✓ Saved to: {output_file}")
        return True
        
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python export_session.py <session_id> [output_file]")
        print("\nExample: python export_session.py session_20251229_143041")
        sys.exit(1)
    
    session_id = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = export_session_to_json(session_id, output_file)
    sys.exit(0 if success else 1)
