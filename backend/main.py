from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "service": "Locator Management System",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "locator-system"}

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
            ElementModel.css_selector == element.css_selector,
            ElementModel.text_content == element.text_content
        ).first()
        
        if existing:
            for key, value in element.model_dump().items():
                if hasattr(existing, key) and value is not None:
                    setattr(existing, key, value)
            db.commit()
            db.refresh(existing)
            return existing
        
        db_element = ElementModel(**element.model_dump())
        db.add(db_element)
        db.commit()
        db.refresh(db_element)
        return db_element
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error")



@app.get("/pages")
def get_pages(session_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Get all pages/screens"""
    try:
        query = db.query(ScreenModel)
        if session_id:
            query = query.filter(ScreenModel.session_id == session_id)
        screens = query.all()
        return [{"id": s.id, "url": s.url, "name": s.name, "session_id": s.session_id} for s in screens]
    except SQLAlchemyError:
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
        
        db_screen = ScreenModel(**screen.model_dump())
        db.add(db_screen)
        db.commit()
        db.refresh(db_screen)
        return db_screen
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error")



@app.get("/locators/latest")
def get_latest_locators(db: Session = Depends(get_db)):
    """Get all locators from the latest session"""
    try:
        latest_session = db.query(
            ScreenModel.session_id,
            func.max(ScreenModel.created_at).label('max_created')
        ).filter(
            ScreenModel.session_id.isnot(None)
        ).group_by(ScreenModel.session_id).order_by(func.max(ScreenModel.created_at).desc()).first()
        
        if not latest_session:
            return []
        
        screen_ids = db.query(ScreenModel.id).filter(
            ScreenModel.session_id == latest_session.session_id
        ).all()
        screen_ids = [s[0] for s in screen_ids]
        
        elements = db.query(ElementModel).filter(
            ElementModel.screen_id.in_(screen_ids)
        ).all()
        
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

@app.get("/sessions")
def get_sessions(db: Session = Depends(get_db)):
    """Get list of last 5 sessions with metadata"""
    try:
        sessions = db.query(
            ScreenModel.session_id,
            func.min(ScreenModel.created_at).label('created_at'),
            func.count(ScreenModel.id).label('total_pages')
        ).filter(ScreenModel.session_id.isnot(None)).group_by(ScreenModel.session_id).all()
        
        result = []
        for session in sessions:
            total_elements = db.query(func.count(ElementModel.id)).join(ScreenModel).filter(
                ScreenModel.session_id == session.session_id
            ).scalar()
            
            result.append({
                "session_id": session.session_id,
                "created_at": session.created_at.strftime("%d/%m/%Y %I:%M %p") if session.created_at else None,
                "total_pages": session.total_pages,
                "total_elements": total_elements
            })
        
        sorted_result = sorted(result, key=lambda x: x['created_at'], reverse=True)
        return sorted_result[:5]
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
                "elements": [
                    {k: v for k, v in {
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
                        "parent_element": elem.parent_element,
                        "interaction_type": elem.interaction_type,
                        "element_context": elem.element_context,
                        "selector_priority": elem.selector_priority,
                        "form_group": elem.form_group,
                        "requires_wait": elem.requires_wait,
                        "id": elem.id,
                        "screen_id": elem.screen_id,
                        "created_at": elem.created_at.strftime("%d/%m/%Y %I:%M %p") if elem.created_at else None,
                        "updated_at": elem.updated_at.strftime("%d/%m/%Y %I:%M %p") if elem.updated_at else None
                    }.items() if v is not None}
                for elem in elements]
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