"""
Database models for user authentication and authorization.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class User(Base):
    """User model for authentication."""
    
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    ai_configs = relationship("AIProviderConfigDB", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"


# Import backend models to register them with Base
# This ensures all models are available when creating tables
from backend.models.database import (
    Project,
    Geometry,
    Mesh,
    Simulation,
    Optimization,
    Job,
    AIProviderConfigDB,
    AIConversation,
)

__all__ = [
    "Base",
    "User",
    "Project",
    "Geometry",
    "Mesh",
    "Simulation",
    "Optimization",
    "Job",
    "AIProviderConfigDB",
    "AIConversation",
]