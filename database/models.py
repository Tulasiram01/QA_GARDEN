from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Screen(Base):
    __tablename__ = "screens"
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500), nullable=False, index=True)
    name = Column(String(200))
    title = Column(String(300))
    dom_hash = Column(String(64), unique=True, index=True)
    session_id = Column(String(100), index=True)
    created_at = Column(DateTime, default=lambda: datetime.now())
    updated_at = Column(DateTime, default=lambda: datetime.now(), onupdate=lambda: datetime.now())
    
    elements = relationship("Element", back_populates="screen", cascade="all, delete-orphan")

class Element(Base):
    __tablename__ = "elements"
    
    id = Column(Integer, primary_key=True, index=True)
    screen_id = Column(Integer, ForeignKey("screens.id"), nullable=False)
    element_name = Column(String(200))
    element_type = Column(String(50), nullable=False, index=True)
    element_id = Column(String(200))
    element_name_attr = Column(String(200))
    data_testid = Column(String(200))
    aria_label = Column(String(500))
    role = Column(String(100))
    css_selector = Column(Text, nullable=False)
    xpath = Column(Text, nullable=False)
    text_content = Column(Text)
    stability_score = Column(Integer, default=0)
    verified = Column(Boolean, default=False, index=True)
    parent_element = Column(String(200))
    interaction_type = Column(String(50))
    element_context = Column(Text)
    selector_priority = Column(Integer, default=3)
    form_group = Column(String(100))
    requires_wait = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now())
    updated_at = Column(DateTime, default=lambda: datetime.now(), onupdate=lambda: datetime.now())
    
    screen = relationship("Screen", back_populates="elements")

class ExecutionMetadata(Base):
    __tablename__ = "execution_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String(100), nullable=False)
    start_time = Column(DateTime, default=lambda: datetime.now())
    end_time = Column(DateTime)
    status = Column(String(50))
    screens_crawled = Column(Integer, default=0)
    elements_extracted = Column(Integer, default=0)
    errors = Column(Text)