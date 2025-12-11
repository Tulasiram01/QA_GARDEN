from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from typing import List, Optional
from contextlib import asynccontextmanager
import socket
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_db, create_tables
from database.models import Screen as ScreenModel, Element as ElementModel
from schemas import Screen, Element, ElementCreate, ScreenCreate, LocatorResponse, VerifyLocator, SessionInfo

def validate_input(value: str, max_length: int = 500) -> str:
    """Validate and sanitize input to prevent injection"""
    if not value or len(value) > max_length:
        raise HTTPException(status_code=400, detail="Invalid input")
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\';%()&+]', '', value.strip())
    return sanitized

def find_free_port(start_port=8000):
    for port in range(start_port, start_port + 10):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', port))
                return port
            except OSError:
                continue
    return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield

app = FastAPI(title="Locator Management System", version="1.0.0", lifespan=lifespan)



@app.post("/add-locator", response_model=Element)
def add_locator(element: ElementCreate, db: Session = Depends(get_db)):
    if element.screen_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid screen ID")
    
    try:
        screen = db.query(ScreenModel).filter(ScreenModel.id == element.screen_id).first()
        if not screen:
            raise HTTPException(status_code=404, detail="Screen not found")
        
        existing = db.query(ElementModel).filter(
            ElementModel.screen_id == element.screen_id,
            ElementModel.css_selector == element.css_selector
        ).first()
        
        if existing:
            for key, value in element.dict().items():
                if hasattr(existing, key) and value is not None:
                    setattr(existing, key, value)
            db.commit()
            db.refresh(existing)
            return existing
        
        db_element = ElementModel(**element.dict())
        db.add(db_element)
        db.commit()
        db.refresh(db_element)
        return db_element
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error")



@app.post("/screens", response_model=Screen)
def create_screen(screen: ScreenCreate, db: Session = Depends(get_db)):
    try:
        if screen.session_id:
            existing = db.query(ScreenModel).filter(
                ScreenModel.url == screen.url,
                ScreenModel.session_id == screen.session_id
            ).first()
            if existing:
                return existing
        
        db_screen = ScreenModel(**screen.dict())
        db.add(db_screen)
        db.commit()
        db.refresh(db_screen)
        return db_screen
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error")



@app.get("/locators")
def get_all_locators(session_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Get all extracted locators across all pages"""
    try:
        query = db.query(ElementModel).join(ScreenModel)
        if session_id:
            query = query.filter(ScreenModel.session_id == session_id)
        
        elements = query.all()
        return [{
            "id": elem.id,
            "screen_id": elem.screen_id,
            "element_name": elem.element_name,
            "element_type": elem.element_type,
            "css_selector": elem.css_selector,
            "xpath": elem.xpath,
            "verified": elem.verified,
            "stability_score": elem.stability_score
        } for elem in elements]
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")

@app.get("/locators/{page}")
def get_locators_by_page(page: str, db: Session = Depends(get_db)):
    """Get locators for a specific page (by name or URL)"""
    try:
        screen = db.query(ScreenModel).filter(
            (ScreenModel.name == page) | (ScreenModel.url.like(f"%{page}%"))
        ).first()
        
        if not screen:
            raise HTTPException(status_code=404, detail="Page not found")
        
        elements = db.query(ElementModel).filter(ElementModel.screen_id == screen.id).all()
        return [{
            "id": elem.id,
            "element_name": elem.element_name,
            "element_type": elem.element_type,
            "css_selector": elem.css_selector,
            "xpath": elem.xpath,
            "verified": elem.verified
        } for elem in elements]
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")

@app.get("/pages")
def get_pages(session_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Get list of extracted pages"""
    try:
        query = db.query(ScreenModel)
        if session_id:
            query = query.filter(ScreenModel.session_id == session_id)
        
        screens = query.all()
        return [{
            "id": screen.id,
            "name": screen.name,
            "url": screen.url,
            "title": screen.title,
            "created_at": screen.created_at.strftime("%d/%m/%Y %I:%M %p") if screen.created_at else None
        } for screen in screens]
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")

@app.get("/ui-elements")
def get_ui_elements(
    session_id: Optional[str] = Query(None),
    element_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get element details with tag, role, aria, text"""
    try:
        query = db.query(ElementModel).join(ScreenModel)
        if session_id:
            query = query.filter(ScreenModel.session_id == session_id)
        if element_type:
            query = query.filter(ElementModel.element_type == element_type)
        
        elements = query.all()
        return [{
            "id": elem.id,
            "screen_id": elem.screen_id,
            "element_name": elem.element_name,
            "tag": elem.element_type,
            "role": elem.role,
            "aria_label": elem.aria_label,
            "text_content": elem.text_content,
            "element_id": elem.element_id,
            "data_testid": elem.data_testid,
            "css_selector": elem.css_selector,
            "xpath": elem.xpath,
            "stability_score": elem.stability_score,
            "verified": elem.verified
        } for elem in elements]
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")

@app.get("/locator-stats")
def get_locator_stats(session_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Get total counts and analytics"""
    try:
        screen_query = db.query(ScreenModel)
        if session_id:
            screen_query = screen_query.filter(ScreenModel.session_id == session_id)
        
        total_pages = screen_query.count()
        
        element_query = db.query(ElementModel).join(ScreenModel)
        if session_id:
            element_query = element_query.filter(ScreenModel.session_id == session_id)
        
        total_locators = element_query.count()
        verified_count = element_query.filter(ElementModel.verified == True).count()
        
        # Count by element type
        type_counts = db.query(
            ElementModel.element_type,
            func.count(ElementModel.id)
        ).join(ScreenModel)
        if session_id:
            type_counts = type_counts.filter(ScreenModel.session_id == session_id)
        type_counts = type_counts.group_by(ElementModel.element_type).all()
        
        return {
            "total_pages": total_pages,
            "total_locators": total_locators,
            "verified_locators": verified_count,
            "unverified_locators": total_locators - verified_count,
            "avg_locators_per_page": total_locators / max(total_pages, 1),
            "locators_by_type": {t[0]: t[1] for t in type_counts}
        }
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")

@app.get("/locator-errors")
def get_locator_errors(session_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Get errors during extraction (low stability scores)"""
    try:
        query = db.query(ElementModel).join(ScreenModel)
        if session_id:
            query = query.filter(ScreenModel.session_id == session_id)
        
        # Consider elements with stability_score < 50 as potential errors
        low_quality = query.filter(ElementModel.stability_score < 50).all()
        
        return {
            "total_errors": len(low_quality),
            "errors": [{
                "element_id": elem.id,
                "element_name": elem.element_name,
                "screen_id": elem.screen_id,
                "stability_score": elem.stability_score,
                "css_selector": elem.css_selector,
                "issue": "Low stability score - locator may be unreliable"
            } for elem in low_quality]
        }
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")

@app.get("/session/{session_id}")
def get_session_data(session_id: str, db: Session = Depends(get_db)):
    """Get complete session data with pages and nested elements"""
    try:
        screens = db.query(ScreenModel).filter(ScreenModel.session_id == session_id).all()
        
        if not screens:
            raise HTTPException(status_code=404, detail="Session not found")
        
        result = []
        for screen in screens:
            elements = db.query(ElementModel).filter(ElementModel.screen_id == screen.id).all()
            
            result.append({
                "url": screen.url,
                "name": screen.name,
                "title": screen.title,
                "id": screen.id,
                "created_at": screen.created_at.strftime("%d/%m/%Y %I:%M %p") if screen.created_at else None,
                "updated_at": screen.updated_at.strftime("%d/%m/%Y %I:%M %p") if screen.updated_at else None,
                "session_id": screen.session_id,
                "elements": [{
                    "element_name": elem.element_name,
                    "element_type": elem.element_type,
                    "element_id": elem.element_id,
                    "element_name_attr": elem.element_name_attr,
                    "data_testid": elem.data_testid,
                    "aria_label": elem.aria_label,
                    "role": elem.role,
                    "css_selector": elem.css_selector,
                    "xpath": elem.xpath,
                    "text_content": elem.text_content,
                    "stability_score": elem.stability_score,
                    "verified": elem.verified,
                    "id": elem.id,
                    "screen_id": elem.screen_id,
                    "created_at": elem.created_at.strftime("%d/%m/%Y %I:%M %p") if elem.created_at else None,
                    "updated_at": elem.updated_at.strftime("%d/%m/%Y %I:%M %p") if elem.updated_at else None
                } for elem in elements]
            })
        
        return result
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")



def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "0.0.0.0"

if __name__ == "__main__":
    import uvicorn
    port = find_free_port()
    local_ip = get_local_ip()
    if port:
        print(f"\n{'='*60}")
        print(f"Starting server on:")
        print(f"  Local:   http://127.0.0.1:{port}")
        print(f"  Network: http://{local_ip}:{port}")
        print(f"  Docs:    http://{local_ip}:{port}/docs")
        print(f"{'='*60}\n")
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        print("No free ports available")