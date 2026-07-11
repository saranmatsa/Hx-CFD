"""
Base models and database configuration for CFD Backend.

Provides SQLAlchemy base class, common mixins, and database utilities.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import DateTime, JSON, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr
from sqlalchemy.ext.asyncio import AsyncAttrs

# Cross-dialect JSON type: uses JSONB on PostgreSQL, JSON on SQLite/others
JSONBType = JSON().with_variant(JSONB(), "postgresql")


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    
    # Generate __tablename__ automatically from class name
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDMixin:
    """Mixin for UUID primary key."""
    
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""
    
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False)


class BaseModel(Base, UUIDMixin, TimestampMixin):
    """Base model with UUID and timestamps."""
    
    __abstract__ = True


class BaseModelWithSoftDelete(BaseModel, SoftDeleteMixin):
    """Base model with UUID, timestamps, and soft delete."""
    
    __abstract__ = True


# Type annotations for common columns
UUIDColumn = Mapped[uuid.UUID]
DateTimeColumn = Mapped[datetime]
StringColumn = Mapped[str]
TextColumn = Mapped[str]
IntegerColumn = Mapped[int]
FloatColumn = Mapped[float]
BooleanColumn = Mapped[bool]
JSONColumn = Mapped[Dict[str, Any]]


def generate_uuid() -> uuid.UUID:
    """Generate a new UUID."""
    return uuid.uuid4()


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.utcnow()