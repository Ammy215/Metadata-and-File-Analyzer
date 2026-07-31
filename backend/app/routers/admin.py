from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from typing import Optional
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models.user import User, UserRole, AuditLog
from app.models.file_record import UploadedFile
from app.schemas.auth import UserResponse, UserAdminUpdate, AuditLogResponse
from app.utils.auth import get_current_admin_user, get_current_super_admin_user, log_audit, get_client_ip

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/dashboard/stats")
async def get_admin_dashboard_stats(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive admin dashboard statistics."""
    
    # Total users
    stmt = select(func.count(User.id))
    result = await db.execute(stmt)
    total_users = result.scalar()
    
    # Active users (logged in within last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    stmt = select(func.count(User.id)).where(User.last_login >= thirty_days_ago)
    result = await db.execute(stmt)
    active_users = result.scalar()
    
    # New users (registered in last 7 days)
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    stmt = select(func.count(User.id)).where(User.created_at >= seven_days_ago)
    result = await db.execute(stmt)
    new_users = result.scalar()
    
    # Total files analyzed
    stmt = select(func.count(UploadedFile.id))
    result = await db.execute(stmt)
    total_files = result.scalar()
    
    # Files by verdict
    stmt = select(
        UploadedFile.verdict,
        func.count(UploadedFile.id)
    ).group_by(UploadedFile.verdict)
    result = await db.execute(stmt)
    verdict_counts = {row[0]: row[1] for row in result}
    
    # Files uploaded today
    today = datetime.now(timezone.utc).date()
    stmt = select(func.count(UploadedFile.id)).where(
        func.date(UploadedFile.upload_time) == today
    )
    result = await db.execute(stmt)
    files_today = result.scalar()
    
    # Average risk score
    stmt = select(func.avg(UploadedFile.risk_score)).where(
        UploadedFile.analyzed == True
    )
    result = await db.execute(stmt)
    avg_risk_score = result.scalar() or 0
    
    # Storage used (total bytes)
    stmt = select(func.sum(UploadedFile.size_bytes))
    result = await db.execute(stmt)
    storage_used = result.scalar() or 0
    
    # Recent audit logs count
    stmt = select(func.count(AuditLog.id)).where(
        AuditLog.timestamp >= seven_days_ago
    )
    result = await db.execute(stmt)
    recent_activity = result.scalar()
    
    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "new_this_week": new_users,
            "inactive": total_users - active_users
        },
        "files": {
            "total": total_files,
            "today": files_today,
            "by_verdict": {
                "safe": verdict_counts.get("SAFE", 0),
                "suspicious": verdict_counts.get("SUSPICIOUS", 0),
                "high_risk": verdict_counts.get("HIGH RISK", 0),
                "critical": verdict_counts.get("CRITICAL", 0)
            },
            "avg_risk_score": round(avg_risk_score, 2)
        },
        "storage": {
            "used_bytes": storage_used,
            "used_gb": round(storage_used / (1024**3), 2)
        },
        "activity": {
            "events_this_week": recent_activity
        }
    }


@router.get("/users")
async def list_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """List all users with filtering and pagination."""
    
    # Build query
    stmt = select(User)
    
    # Apply filters
    if role:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            (User.email.ilike(search_pattern)) |
            (User.username.ilike(search_pattern)) |
            (User.full_name.ilike(search_pattern))
        )
    
    # Order and paginate
    stmt = stmt.order_by(desc(User.created_at)).offset(skip).limit(limit)
    
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    # Return as dict with users array for frontend compatibility
    return {
        "users": [
            {
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None
            }
            for user in users
        ]
    }


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_details(
    user_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific user."""
    
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserAdminUpdate,
    request: Request,
    current_user: User = Depends(get_current_super_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user (admin only). Super admin required for role changes."""
    
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent modifying super admin
    if user.role == UserRole.SUPER_ADMIN and current_user.id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify super admin users"
        )
    
    # Track changes for audit log
    changes = []
    
    # Update fields
    if user_update.role is not None:
        try:
            new_role = UserRole[user_update.role.upper()]
            if user.role != new_role:
                changes.append(f"role changed from {user.role.value} to {new_role.value}")
                user.role = new_role
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role"
            )
    
    if user_update.is_active is not None and user.is_active != user_update.is_active:
        action_type = "unbanned" if user_update.is_active else "banned"
        changes.append(f"user {action_type}")
        user.is_active = user_update.is_active
        
        # Log ban/unban action
        await log_audit(
            db=db,
            user_id=str(current_user.id),
            action="USER_BAN" if not user_update.is_active else "USER_UNBAN",
            resource_type="user",
            resource_id=str(user.id),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
            details=f"Admin {current_user.email} {'banned' if not user_update.is_active else 'unbanned'} user: {user.email}"
        )
    
    if user_update.is_verified is not None:
        user.is_verified = user_update.is_verified
    
    await db.commit()
    await db.refresh(user)
    
    # Log general update if there were other changes
    if changes:
        await log_audit(
            db=db,
            user_id=str(current_user.id),
            action="USER_UPDATE",
            resource_type="user",
            resource_id=str(user.id),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
            details=f"Admin {current_user.email} updated user {user.email}: {', '.join(changes)}"
        )
    
    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    request: Request,
    current_user: User = Depends(get_current_super_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a user (super admin only)."""
    
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent deleting super admin
    if user.role == UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete super admin users"
        )
    
    # Prevent self-deletion
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    # Log before deletion
    await log_audit(
        db=db,
        user_id=str(current_user.id),
        action="USER_DELETE",
        resource_type="user",
        resource_id=str(user.id),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        details=f"Admin {current_user.email} deleted user: {user.email}"
    )
    
    await db.delete(user)
    await db.commit()
    
    return {"message": "User deleted successfully"}


@router.get("/files")
async def list_all_files(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user_id: Optional[str] = None,
    verdict: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """List all uploaded files with filtering."""
    
    try:
        # Build query
        stmt = select(UploadedFile)
        
        # Apply filters
        if user_id:
            stmt = stmt.where(UploadedFile.user_id == user_id)
        if verdict:
            stmt = stmt.where(UploadedFile.verdict == verdict)
        
        # Order and paginate
        stmt = stmt.order_by(desc(UploadedFile.upload_time)).offset(skip).limit(limit)
        
        result = await db.execute(stmt)
        files = result.scalars().all()
        
        return [
            {
                "id": str(f.id),
                "user_id": str(f.user_id) if f.user_id else None,
                "original_name": f.original_name or "Unknown",
                "size_bytes": f.size_bytes or 0,
                "mime_type": f.mime_type or "Unknown",
                "verdict": f.verdict or "PENDING",
                "risk_score": f.risk_score if f.risk_score is not None else 0,
                "upload_time": f.upload_time.isoformat() if f.upload_time else None,
                "analyzed": f.analyzed if f.analyzed is not None else False
            }
            for f in files
        ]
    except Exception as e:
        print(f"Error fetching files: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch files: {str(e)}"
        )


@router.delete("/files/{file_id}")
async def delete_file_admin(
    file_id: str,
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete any file (admin only)."""
    
    stmt = select(UploadedFile).where(UploadedFile.id == file_id)
    result = await db.execute(stmt)
    file = result.scalar_one_or_none()
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Log before deletion
    await log_audit(
        db=db,
        user_id=str(current_user.id),
        action="FILE_DELETE",
        resource_type="file",
        resource_id=str(file.id),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        details=f"Admin {current_user.email} deleted file: {file.original_name}"
    )
    
    await db.delete(file)
    await db.commit()
    
    return {"message": "File deleted successfully"}


@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get audit logs with filtering."""
    
    # Build query
    stmt = select(AuditLog)
    
    # Date filter
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = stmt.where(AuditLog.timestamp >= cutoff_date)
    
    # Apply filters
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    
    # Order and paginate
    stmt = stmt.order_by(desc(AuditLog.timestamp)).offset(skip).limit(limit)
    
    result = await db.execute(stmt)
    logs = result.scalars().all()
    
    return logs


@router.get("/analytics/user-growth")
async def get_user_growth_analytics(
    days: int = Query(30, ge=7, le=365),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user growth analytics over time."""
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    stmt = select(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('count')
    ).where(
        User.created_at >= cutoff_date
    ).group_by(
        func.date(User.created_at)
    ).order_by('date')
    
    result = await db.execute(stmt)
    data = [{"date": str(row[0]), "count": row[1]} for row in result]
    
    return {"data": data}


@router.get("/analytics/file-uploads")
async def get_file_upload_analytics(
    days: int = Query(30, ge=7, le=365),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get file upload analytics over time."""
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    stmt = select(
        func.date(UploadedFile.upload_time).label('date'),
        func.count(UploadedFile.id).label('count')
    ).where(
        UploadedFile.upload_time >= cutoff_date
    ).group_by(
        func.date(UploadedFile.upload_time)
    ).order_by('date')
    
    result = await db.execute(stmt)
    data = [{"date": str(row[0]), "count": row[1]} for row in result]
    
    return {"data": data}


@router.get("/analytics/threat-distribution")
async def get_threat_distribution(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get distribution of file verdicts."""
    
    stmt = select(
        UploadedFile.verdict,
        func.count(UploadedFile.id).label('count')
    ).where(
        UploadedFile.analyzed == True
    ).group_by(
        UploadedFile.verdict
    )
    
    result = await db.execute(stmt)
    data = [{"verdict": row[0], "count": row[1]} for row in result]
    
    return {"data": data}
