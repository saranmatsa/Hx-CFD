"""
User management routes for CFD Backend.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from cfd_backend.core.config import get_settings
from cfd_backend.core.dependencies import get_db_session
from cfd_backend.core.exceptions import NotFoundError, ValidationError
from cfd_backend.core.security import get_password_hash, verify_password
from cfd_backend.models.user import User, UserRole, UserStatus
from cfd_backend.api.v1.auth import get_current_active_user

router = APIRouter()


class UserUpdate(BaseModel):
    """User update model."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    theme: Optional[str] = None
    language: Optional[str] = None
    notification_email: Optional[bool] = None
    notification_webhook: Optional[bool] = None


class UserPasswordChange(BaseModel):
    """Password change model."""
    current_password: str
    new_password: str


class UserListResponse(BaseModel):
    """User list response with pagination."""
    users: list
    total: int
    page: int
    page_size: int
    total_pages: int


class UserResponse(BaseModel):
    """User response model."""
    id: str
    email: str
    username: str
    full_name: Optional[str]
    role: UserRole
    status: UserStatus
    theme: str
    language: str
    notification_email: bool
    notification_webhook: bool
    created_at: str
    last_login_at: Optional[str]


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[UserRole] = None,
    status: Optional[UserStatus] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List users with pagination and filters (admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    
    query = select(User)
    
    if search:
        query = query.where(
            (User.username.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%")) |
            (User.full_name.ilike(f"%{search}%"))
        )
    
    if role:
        query = query.where(User.role == role)
    
    if status:
        query = query.where(User.status == status)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    users = result.scalars().all()
    
    return UserListResponse(
        users=[
            UserResponse(
                id=str(u.id),
                email=u.email,
                username=u.username,
                full_name=u.full_name,
                role=u.role,
                status=u.status,
                theme=u.theme,
                language=u.language,
                notification_email=u.notification_email,
                notification_webhook=u.notification_webhook,
                created_at=u.created_at.isoformat(),
                last_login_at=u.last_login_at.isoformat() if u.last_login_at else None,
            )
            for u in users
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get user by ID."""
    # Users can only view their own profile unless admin/manager
    if current_user.id != user_id and current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise NotFoundError("User", str(user_id))
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        status=user.status,
        theme=user.theme,
        language=user.language,
        notification_email=user.notification_email,
        notification_webhook=user.notification_webhook,
        created_at=user.created_at.isoformat(),
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update user profile."""
    # Users can only update their own profile unless admin
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise NotFoundError("User", str(user_id))
    
    # Check email uniqueness if changing
    if user_data.email and user_data.email != user.email:
        result = await db.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none():
            raise ValidationError("Email already in use")
        user.email = user_data.email
    
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.theme is not None:
        user.theme = user_data.theme
    if user_data.language is not None:
        user.language = user_data.language
    if user_data.notification_email is not None:
        user.notification_email = user_data.notification_email
    if user_data.notification_webhook is not None:
        user.notification_webhook = user_data.notification_webhook
    
    await db.commit()
    await db.refresh(user)
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        status=user.status,
        theme=user.theme,
        language=user.language,
        notification_email=user.notification_email,
        notification_webhook=user.notification_webhook,
        created_at=user.created_at.isoformat(),
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )


@router.post("/{user_id}/change-password")
async def change_password(
    user_id: UUID,
    password_data: UserPasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Change user password."""
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise NotFoundError("User", str(user_id))
    
    # Verify current password (unless admin)
    if current_user.role != UserRole.ADMIN:
        if not verify_password(password_data.current_password, user.hashed_password):
            raise ValidationError("Current password is incorrect")
    
    user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()
    
    return {"message": "Password changed successfully"}


@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Deactivate a user (admin only)."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    if current_user.id == user_id:
        raise ValidationError("Cannot deactivate yourself")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise NotFoundError("User", str(user_id))
    
    user.status = UserStatus.INACTIVE
    await db.commit()
    
    return {"message": "User deactivated"}


@router.post("/{user_id}/activate")
async def activate_user(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Activate a user (admin only)."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise NotFoundError("User", str(user_id))
    
    user.status = UserStatus.ACTIVE
    await db.commit()
    
    return {"message": "User activated"}


@router.delete("/{user_id}")
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a user (admin only)."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    if current_user.id == user_id:
        raise ValidationError("Cannot delete yourself")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise NotFoundError("User", str(user_id))
    
    await db.delete(user)
    await db.commit()
    
    return {"message": "User deleted"}