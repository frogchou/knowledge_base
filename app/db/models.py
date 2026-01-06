import enum
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class SourceType(str, enum.Enum):
    text = "text"
    url = "url"
    file = "file"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("KnowledgeItem", back_populates="owner")


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    source_type = Column(Enum(SourceType), nullable=False)
    source_url = Column(String(500), nullable=True)
    original_filename = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=True)
    mime_type = Column(String(100), nullable=True)
    content_text = Column(LONGTEXT, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)
    summary = Column(Text, nullable=True)
    keywords = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="items")
