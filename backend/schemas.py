from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ElementBase(BaseModel):
    element_name: Optional[str] = None
    element_type: str
    element_id: Optional[str] = None
    element_name_attr: Optional[str] = None
    data_testid: Optional[str] = None
    aria_label: Optional[str] = None
    role: Optional[str] = None
    css_selector: str
    xpath: str
    text_content: Optional[str] = None
    stability_score: Optional[int] = 0
    verified: bool = False

class ElementCreate(ElementBase):
    screen_id: int

class Element(ElementBase):
    id: int
    screen_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ScreenBase(BaseModel):
    url: str
    name: Optional[str] = None
    title: Optional[str] = None
    dom_hash: Optional[str] = None
    session_id: Optional[str] = None

class ScreenCreate(ScreenBase):
    pass

class Screen(ScreenBase):
    id: int
    created_at: datetime
    updated_at: datetime
    elements: List[Element] = []
    
    class Config:
        from_attributes = True

class SessionInfo(BaseModel):
    session_id: str
    screens_count: int
    elements_count: int
    created_at: datetime

class LocatorResponse(BaseModel):
    css_selector: str
    xpath: str
    element_id: Optional[str] = None
    data_testid: Optional[str] = None
    verified: bool

class VerifyLocator(BaseModel):
    verified: bool