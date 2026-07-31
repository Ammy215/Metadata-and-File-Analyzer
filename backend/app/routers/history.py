from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.database import get_db
from app.models.file_record import UploadedFile
from app.models.user import User
from app.utils.auth import get_current_active_user
from app.schemas.report import HistoryResponseSchema, HistoryItemSchema

router = APIRouter(prefix="/api/v1", tags=["history"])


@router.get("/history", response_model=HistoryResponseSchema)
async def get_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    verdict: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get paginated scan history for the current user.

    Query parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    - verdict: Filter by verdict (SAFE, SUSPICIOUS, HIGH_RISK, CRITICAL)
    """
    try:
        # Build query - scoped to the current user's own files.
        # (Site-wide history is available to admins via /api/v1/admin/files.)
        stmt = select(UploadedFile).where(
            UploadedFile.analyzed == True,
            UploadedFile.user_id == current_user.id,
        )

        if verdict:
            stmt = stmt.where(UploadedFile.verdict == verdict)

        # Count total
        count_stmt = select(func.count(UploadedFile.id)).where(
            UploadedFile.analyzed == True,
            UploadedFile.user_id == current_user.id,
        )
        if verdict:
            count_stmt = count_stmt.where(UploadedFile.verdict == verdict)
        
        total_result = await db.execute(count_stmt)
        total = total_result.scalar()
        
        # Paginate and sort
        stmt = stmt.order_by(desc(UploadedFile.upload_time))
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        
        result = await db.execute(stmt)
        files = result.scalars().all()
        
        items = [
            HistoryItemSchema(
                file_id=f.id,
                original_name=f.original_name,
                upload_time=f.upload_time,
                risk_score=f.risk_score,
                verdict=f.verdict,
            )
            for f in files
        ]
        
        return HistoryResponseSchema(
            total=total,
            page=page,
            page_size=page_size,
            items=items,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")


@router.delete("/file/{file_id}")
async def delete_file(
    file_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a file record (owner or admin only)."""
    try:
        stmt = select(UploadedFile).where(UploadedFile.id == file_id)
        result = await db.execute(stmt)
        file_record = result.scalar_one_or_none()

        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")

        if file_record.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to delete this file")

        # Delete file from disk
        from pathlib import Path
        from app.config import settings
        
        file_path = Path(settings.UPLOAD_DIR) / file_record.stored_name
        if file_path.exists():
            file_path.unlink()
        
        # Delete from database
        await db.delete(file_record)
        await db.commit()
        
        return {"message": "File deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")
