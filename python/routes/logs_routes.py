"""
Activity logs routes
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models import User, ActivityLog
from auth import get_current_user

router = APIRouter(prefix="/api/logs", tags=["logs"])


class LogResponse(BaseModel):
    type: str
    email: str
    time: str
    extra_data: dict = {}
    
    class Config:
        from_attributes = True


@router.get("", response_model=list[LogResponse])
async def get_user_logs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get activity logs for current user (last 20)
    """
    result = await db.execute(
        select(ActivityLog)
        .where(ActivityLog.email == current_user.email)
        .order_by(ActivityLog.created_at.desc())
        .limit(20)
    )
    
    logs = result.scalars().all()
    
    return [
        LogResponse(
            type=log.action_type,
            email=log.email,
            time=log.created_at.isoformat(),
            extra_data=log.extra_data or {}
        )
        for log in logs
    ]
