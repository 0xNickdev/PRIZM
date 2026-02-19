"""
Authentication routes (register, login, logout, etc)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from database import get_db
from models import User, ActivityLog
from auth import get_password_hash, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


# Request/Response models
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    email: str
    method: str


class UserResponse(BaseModel):
    email: str
    method: str
    display_name: str | None = None


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user with email and password"""
    
    # Validation
    if len(request.password) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password min 4 chars"
        )
    
    # Check if user exists
    result = await db.execute(select(User).where(User.email == request.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account exists"
        )
    
    # Create new user
    password_hash = get_password_hash(request.password)
    
    new_user = User(
        email=request.email,
        password_hash=password_hash,
        auth_method='email',
        is_active=True
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Log activity
    log = ActivityLog(
        user_id=new_user.id,
        email=new_user.email,
        action_type='register',
        extra_data={}
    )
    db.add(log)
    await db.commit()
    
    # Create token
    token = create_access_token(
        data={"email": new_user.email, "method": "email"}
    )
    
    return AuthResponse(
        token=token,
        email=new_user.email,
        method='email'
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with email and password"""
    
    # Find user
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Verify password
    if not user.password_hash or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong password"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()
    
    # Log activity
    log = ActivityLog(
        user_id=user.id,
        email=user.email,
        action_type='login',
        extra_data={}
    )
    db.add(log)
    await db.commit()
    
    # Create token
    token = create_access_token(
        data={"email": user.email, "method": user.auth_method}
    )
    
    return AuthResponse(
        token=token,
        email=user.email,
        method=user.auth_method
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
