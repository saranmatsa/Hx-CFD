"""
Common API dependencies for CFD Backend.

This module provides shared dependency injection functions used across
all API routes.
"""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cfd_backend.core.config import get_settings
from cfd_backend.core.dependencies import get_db_session
from cfd_backend.core.security import decode_token
from cfd_backend.models.user import User, UserRole, UserStatus

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Get current authenticated user from token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user."""
    if current_user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Get current user and verify superuser/admin status."""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


async def get_current_manager(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Get current user and verify manager status."""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager privileges required",
        )
    return current_user


async def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> Optional[User]:
    """Get current user if token is provided, otherwise return None."""
    if not token:
        return None

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            return None
    except Exception:
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or user.status != UserStatus.ACTIVE:
        return None

    return user


def get_settings_dependency():
    """Get application settings."""
    return get_settings()


class PaginationParams:
    """Pagination parameters dependency."""

    def __init__(
        self,
        page: int = 1,
        page_size: int = 20,
        max_page_size: int = 100,
    ):
        self.page = max(1, page)
        self.page_size = min(max(1, page_size), max_page_size)
        self.offset = (self.page - 1) * self.page_size
        self.limit = self.page_size


def get_pagination_params(
    page: int = 1,
    page_size: int = 20,
) -> PaginationParams:
    """Get pagination parameters."""
    return PaginationParams(page=page, page_size=page_size)


class SortParams:
    """Sorting parameters dependency."""

    def __init__(
        self,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        allowed_fields: Optional[list[str]] = None,
    ):
        self.sort_by = sort_by
        self.sort_order = sort_order.lower() if sort_order else "desc"
        self.allowed_fields = allowed_fields or []

    def get_sort_column(self, model, default_column):
        """Get the sort column for a model."""
        if self.sort_by and self.sort_by in self.allowed_fields:
            return getattr(model, self.sort_by, default_column)
        return default_column

    def get_sort_direction(self):
        """Get sort direction (asc/desc)."""
        return self.sort_order if self.sort_order in ["asc", "desc"] else "desc"


def get_sort_params(
    sort_by: Optional[str] = None,
    sort_order: str = "desc",
    allowed_fields: Optional[list[str]] = None,
) -> SortParams:
    """Get sorting parameters."""
    return SortParams(sort_by=sort_by, sort_order=sort_order, allowed_fields=allowed_fields)