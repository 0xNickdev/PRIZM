"""
Authentication routes (register, login)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import re

from database import get_db
from models import User, ActivityLog
from auth import get_password_hash, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


# Request/Response models
class RegisterRequest(BaseModel):
    username: str
    password: str
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        v = v.strip()
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        if len(v) > 50:
            raise ValueError('Username too long')
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, _ and -')
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 4:
            raise ValueError('Password must be at least 4 characters')
        if len(v) > 128:
            raise ValueError('Password too long')
        return v


class LoginRequest(BaseModel):
    username: str
    password: str
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        return v.strip()
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) > 128:
            raise ValueError('Password too long')
        return v


class AuthResponse(BaseModel):
    token: str
    username: str


class UserResponse(BaseModel):
    username: str
    display_name: str | None = None


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Register a new user with username and password
    
    Security features:
    - Username validation (3-50 chars, alphanumeric + _ -)
    - Password length validation (4-128 chars)
    - Bcrypt password hashing
    - SQL injection prevention via SQLAlchemy ORM
    """
    
    # Check if user exists
    result = await db.execute(
        select(User).where(User.username == request.username)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken"
        )
    
    # Hash password with bcrypt
    password_hash = get_password_hash(request.password)
    
    # Create new user
    new_user = User(
        username=request.username,
        email=f"{request.username}@local",  # placeholder
        password_hash=password_hash,
        auth_method='username',
        is_active=True
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Log activity
    log = ActivityLog(
        user_id=new_user.id,
        email=new_user.username,
        action_type='register',
        extra_data={}
    )
    db.add(log)
    await db.commit()
    
    # Create JWT token
    token = create_access_token(
        data={"username": new_user.username}
    )
    
    return AuthResponse(
        token=token,
        username=new_user.username
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Login with username and password
    
    Security features:
    - Parameterized SQL queries via ORM
    - Bcrypt password verification
    - Activity logging
    """
    
    # Find user
    result = await db.execute(
        select(User).where(User.username == request.username)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabled"
        )
    
    # Verify password
    if not user.password_hash or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()
    
    # Log activity
    log = ActivityLog(
        user_id=user.id,
        email=user.username,
        action_type='login',
        extra_data={}
    )
    db.add(log)
    await db.commit()
    
    # Create JWT token
    token = create_access_token(
        data={"username": user.username}
    )
    
    return AuthResponse(
        token=token,
        username=user.username
    )


@router.post("/twitter", response_model=AuthResponse)
async def twitter_login(db: AsyncSession = Depends(get_db)):
    """
    Twitter OAuth login (placeholder)
    In production, implement proper OAuth flow
    """
    email = 'x_user@pulse.app'
    
    # Check if user exists
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        # Create new user
        user = User(
            email=email,
            auth_method='twitter',
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()
    
    # Log activity
    log = ActivityLog(
        user_id=user.id,
        email=user.email,
        action_type='login',
        extra_data={'method': 'twitter'}
    )
    db.add(log)
    await db.commit()
    
    # Create token
    token = create_access_token(
        data={"email": user.email, "method": "twitter"}
    )
    
    return AuthResponse(
        token=token,
        email=user.email,
        method='twitter'
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user"""
    return UserResponse(
        email=current_user.email,
        method=current_user.auth_method,
        display_name=current_user.display_name
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Logout (just log the activity)"""
    
    # Log activity
    log = ActivityLog(
        user_id=current_user.id,
        email=current_user.email,
        action_type='logout',
        extra_data={}
    )
    db.add(log)
    await db.commit()
    
    return {"ok": True}
