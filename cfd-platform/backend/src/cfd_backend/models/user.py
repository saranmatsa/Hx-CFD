"""
User and authentication models for CFD Backend.
"""

import enum
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Enum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cfd_backend.models.base import Base, BaseModel, JSONColumn


class UserRole(str, enum.Enum):
    """User role enumeration."""
    ADMIN = "admin"
    ENGINEER = "engineer"
    VIEWER = "viewer"
    GUEST = "guest"


class UserStatus(str, enum.Enum):
    """User status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"


class User(BaseModel):
    """User model."""
    
    __tablename__ = "users"
    
    # Authentication
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Profile
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    # Role & Status
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.ENGINEER,
        nullable=False,
        index=True,
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus),
        default=UserStatus.PENDING,
        nullable=False,
        index=True,
    )
    
    # Preferences
    preferences: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    theme: Mapped[str] = mapped_column(String(50), default="system", nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    
    # Timestamps
    last_login_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # Relationships
    owned_projects: Mapped[List["Project"]] = relationship(
        "Project",
        back_populates="owner",
        foreign_keys="Project.owner_id",
        lazy="selectin",
    )
    api_keys: Mapped[List["APIKey"]] = relationship(
        "APIKey",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    sessions: Mapped[List["UserSession"]] = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_users_email_status", "email", "status"),
        Index("ix_users_username_status", "username", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role={self.role})>"


class APIKey(BaseModel):
    """API Key model for programmatic access."""
    
    __tablename__ = "api_keys"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Permissions
    scopes: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Expiry
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_keys")
    
    # Indexes
    __table_args__ = (
        Index("ix_api_keys_user_active", "user_id", "is_active"),
        UniqueConstraint("user_id", "name", name="uq_api_key_user_name"),
    )
    
    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, user_id={self.user_id}, name='{self.name}')>"


class UserSession(BaseModel):
    """User session model for tracking active sessions."""
    
    __tablename__ = "user_sessions"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    session_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    refresh_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    
    # Client info
    user_agent: Mapped[Optional[str]] = mapped_column(nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    device_info: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Expiry
    expires_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    last_activity_at: Mapped[datetime] = mapped_column(nullable=False)
    
    # Status
    is_revoked: Mapped[bool] = mapped_column(default=False, nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")
    
    # Indexes
    __table_args__ = (
        Index("ix_user_sessions_user_expires", "user_id", "expires_at"),
        Index("ix_user_sessions_token_expires", "session_token", "expires_at"),
    )
    
    def __repr__(self) -> str:
        return f"<UserSession(id={self.id}, user_id={self.user_id}, expires={self.expires_at})>"


class ProjectMember(BaseModel):
    """Project membership model for collaboration."""
    
    __tablename__ = "project_members"
    
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.VIEWER,
        nullable=False,
    )
    
    # Permissions
    can_edit: Mapped[bool] = mapped_column(default=False, nullable=False)
    can_run_simulations: Mapped[bool] = mapped_column(default=False, nullable=False)
    can_manage_members: Mapped[bool] = mapped_column(default=False, nullable=False)
    can_delete: Mapped[bool] = mapped_column(default=False, nullable=False)
    
    # Invitation
    invited_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    invited_at: Mapped[datetime] = mapped_column(nullable=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", lazy="selectin")
    user: Mapped["User"] = relationship("User", lazy="selectin")
    invited_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[invited_by_id], lazy="selectin")
    
    # Indexes
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_member"),
        Index("ix_project_members_project_role", "project_id", "role"),
    )
    
    def __repr__(self) -> str:
        return f"<ProjectMember(project_id={self.project_id}, user_id={self.user_id}, role={self.role})>"


# Update Project model to add owner relationship
# This is done in project.py but we need to add the relationship here
# The relationship is already defined in project.py as:
# owner: Mapped[Optional["User"]] = relationship("User", back_populates="owned_projects", foreign_keys=[owner_id])