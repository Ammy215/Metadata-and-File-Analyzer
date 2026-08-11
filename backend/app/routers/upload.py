from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Query, Request, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
from uuid import uuid4
import os
import hashlib
from app.database import get_db
from app.models.file_record import UploadedFile
from app.models.user import User, UserRole
from app.schemas.report import UploadResponse, AnalysisResultSchema, HistoryResponseSchema, HistoryItemSchema
from app.utils.file_validator import FileValidator
from app.utils.auth import get_user_or_api_key, log_audit, get_client_ip
from app.tasks.analysis_tasks import run_analysis
from app.config import settings

router = APIRouter(prefix="/api/v1", tags=["uploads"])

# Files are deleted right after analysis completes (see analysis_tasks.py),
# so under normal operation a user only ever has a handful "in flight" at
# once. This caps how many can be queued/mid-analysis at the same time,
# guarding against someone burst-uploading large files faster than
# analysis+deletion can keep up with - the one gap the delete-after-analysis
# behavior alone doesn't cover.
MAX_PENDING_UPLOADS_PER_USER = 5

# Total (not just pending) uploads a guest account may ever make across its
# whole 4-hour session - keeps the trial genuinely limited rather than just
# rate-limited.
GUEST_MAX_TOTAL_UPLOADS = 3


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    request: Request = None,
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_user_or_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a file for analysis. Accepts either a JWT access token or an
    API key via the Authorization: Bearer header - either way, the file
    is attributed to whichever user actually owns that credential (see
    get_user_or_api_key), so an API key can only ever upload as its own
    owner, not on behalf of anyone else.

    Returns: file_id, original_name, size_bytes
    """
    try:
        # Reject before reading any file bytes if this user already has too
        # many uploads still awaiting analysis - see MAX_PENDING_UPLOADS_PER_USER.
        pending_stmt = select(func.count(UploadedFile.id)).where(
            UploadedFile.user_id == current_user.id,
            UploadedFile.analyzed == False,  # noqa: E712 - SQLAlchemy needs `== False`, not `is False`
        )
        pending_count = (await db.execute(pending_stmt)).scalar()
        if pending_count >= MAX_PENDING_UPLOADS_PER_USER:
            raise HTTPException(
                status_code=429,
                detail=f"You have {pending_count} uploads still being analyzed. "
                       f"Please wait for those to finish before uploading more.",
            )

        if current_user.role == UserRole.GUEST:
            total_stmt = select(func.count(UploadedFile.id)).where(
                UploadedFile.user_id == current_user.id,
            )
            total_count = (await db.execute(total_stmt)).scalar()
            if total_count >= GUEST_MAX_TOTAL_UPLOADS:
                raise HTTPException(
                    status_code=429,
                    detail=f"Guest accounts are limited to {GUEST_MAX_TOTAL_UPLOADS} uploads. "
                           f"Register for a free account to upload more.",
                )

        # Ensure upload directory exists
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(exist_ok=True)
        
        # Generate unique filename
        file_id = uuid4()
        file_extension = Path(file.filename).suffix
        stored_filename = f"{file_id}{file_extension}"
        file_path = upload_dir / stored_filename
        
        # Read and save file
        contents = await file.read()
        
        # Calculate SHA256 before validation
        sha256_hash = hashlib.sha256(contents).hexdigest()
        
        # Validate file
        is_valid, message = FileValidator.validate_file(file_path, len(contents))
        if not is_valid:
            raise HTTPException(status_code=400, detail=message)
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Create database record with SHA256 and user_id
        uploaded_file = UploadedFile(
            id=file_id,
            user_id=current_user.id,  # Link to authenticated user
            original_name=file.filename,
            stored_name=stored_filename,
            extension=file_extension,
            mime_type=file.content_type,
            size_bytes=len(contents),
            sha256=sha256_hash,  # Set the calculated SHA256
        )
        db.add(uploaded_file)
        await db.commit()
        await db.refresh(uploaded_file)

        # Trigger background analysis. The file/DB row above already exist
        # at this point regardless of what happens next - if the process
        # restarts mid-analysis, the periodic sweep in analysis_tasks.py
        # detects the stuck (analyzed=False) record and retries it.
        background_tasks.add_task(run_analysis, str(file_id), str(file_path))

        # Log audit
        await log_audit(
            db=db,
            user_id=str(current_user.id),
            action="FILE_UPLOAD",
            resource_type="file",
            resource_id=str(file_id),
            ip_address=get_client_ip(request) if request else None,
            user_agent=request.headers.get("User-Agent") if request else None,
            details=f"Uploaded file: {file.filename} ({len(contents)} bytes)"
        )
        
        return UploadResponse(
            file_id=file_id,
            original_name=file.filename,
            size_bytes=len(contents),
            message="File uploaded successfully. Analysis in progress..."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
