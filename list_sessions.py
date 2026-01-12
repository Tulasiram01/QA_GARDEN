import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database.models import Screen

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///locator_system.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

db = SessionLocal()

try:
    sessions = db.query(Screen.session_id).distinct().all()
    
    if not sessions:
        print("No sessions found in database")
    else:
        print("Available sessions:")
        for session in sessions:
            if session[0]:
                count = db.query(Screen).filter(Screen.session_id == session[0]).count()
                print(f"  - {session[0]} ({count} pages)")
finally:
    db.close()
