import re
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from uuid import UUID
from app.database import get_db
from app.models.file_record import UploadedFile, MetadataEntry, ThreatMatch, RiskBreakdown, EntropyResult
from app.models.user import User
from app.utils.auth import get_current_active_user
from app.utils.report_generator import ReportGenerator
from app.config import settings
from app.schemas.report import (
    AnalysisResultSchema, MetadataEntrySchema, ThreatMatchSchema,
    RiskBreakdownSchema, EntropyResultSchema, ReportSchema
)
from datetime import datetime, timezone

router = APIRouter(prefix="/api/v1", tags=["analysis"])


def _authorize_file_access(file_record: UploadedFile, current_user: User) -> None:
    """Only the uploader or an admin may view a file's analysis/report."""
    if file_record.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to access this file")


@router.get("/analyze/{file_id}", response_model=AnalysisResultSchema)
async def get_analysis(
    file_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get analysis results for a file.
    """
    try:
        stmt = (
            select(UploadedFile)
            .where(UploadedFile.id == file_id)
            .options(
                selectinload(UploadedFile.metadata_entries),
                selectinload(UploadedFile.threat_matches),
                selectinload(UploadedFile.risk_breakdowns),
                selectinload(UploadedFile.entropy_result),
            )
        )
        result = await db.execute(stmt)
        file_record = result.scalar_one_or_none()

        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")

        _authorize_file_access(file_record, current_user)

        if not file_record.analyzed:
            raise HTTPException(status_code=202, detail="Analysis still in progress")
        
        # Build response
        return AnalysisResultSchema(
            file_id=file_record.id,
            original_name=file_record.original_name,
            mime_type=file_record.mime_type,
            size_bytes=file_record.size_bytes,
            sha256=file_record.sha256,
            md5=file_record.md5,
            sha1=file_record.sha1,
            upload_time=file_record.upload_time,
            risk_score=file_record.risk_score,
            verdict=file_record.verdict,
            analyzed=file_record.analyzed,
            metadata=[
                MetadataEntrySchema(**m.__dict__)
                for m in file_record.metadata_entries
            ],
            threats=[
                ThreatMatchSchema(**t.__dict__)
                for t in file_record.threat_matches
            ],
            risk_factors=[
                RiskBreakdownSchema(**r.__dict__)
                for r in file_record.risk_breakdowns
            ],
            entropy=(
                EntropyResultSchema(**file_record.entropy_result.__dict__)
                if file_record.entropy_result else None
            ),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching analysis: {str(e)}")


@router.get("/report/{file_id}", response_model=ReportSchema)
async def get_report(
    file_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get full security report for a file.
    """
    try:
        stmt = (
            select(UploadedFile)
            .where(UploadedFile.id == file_id)
            .options(
                selectinload(UploadedFile.metadata_entries),
                selectinload(UploadedFile.threat_matches),
                selectinload(UploadedFile.risk_breakdowns),
                selectinload(UploadedFile.entropy_result),
            )
        )
        result = await db.execute(stmt)
        file_record = result.scalar_one_or_none()

        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")

        _authorize_file_access(file_record, current_user)

        analysis = AnalysisResultSchema(
            file_id=file_record.id,
            original_name=file_record.original_name,
            mime_type=file_record.mime_type,
            size_bytes=file_record.size_bytes,
            sha256=file_record.sha256,
            md5=file_record.md5,
            sha1=file_record.sha1,
            upload_time=file_record.upload_time,
            risk_score=file_record.risk_score,
            verdict=file_record.verdict,
            analyzed=file_record.analyzed,
            metadata=[
                MetadataEntrySchema(**m.__dict__)
                for m in file_record.metadata_entries
            ],
            threats=[
                ThreatMatchSchema(**t.__dict__)
                for t in file_record.threat_matches
            ],
            risk_factors=[
                RiskBreakdownSchema(**r.__dict__)
                for r in file_record.risk_breakdowns
            ],
            entropy=(
                EntropyResultSchema(**file_record.entropy_result.__dict__)
                if file_record.entropy_result else None
            ),
        )
        
        return ReportSchema(
            file_id=file_record.id,
            original_name=file_record.original_name,
            mime_type=file_record.mime_type,
            size_bytes=file_record.size_bytes,
            hashes={
                "sha256": file_record.sha256,
                "md5": file_record.md5,
                "sha1": file_record.sha1,
            },
            analysis=analysis,
            generated_at=datetime.now(timezone.utc),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching report: {str(e)}")


@router.get("/report/{file_id}/pdf")
async def get_report_pdf(
    file_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get the full security report for a file as a downloadable PDF.
    """
    if not settings.WEASYPRINT_ENABLED:
        raise HTTPException(status_code=503, detail="PDF report generation is currently disabled")

    stmt = (
        select(UploadedFile)
        .where(UploadedFile.id == file_id)
        .options(
            selectinload(UploadedFile.metadata_entries),
            selectinload(UploadedFile.threat_matches),
        )
    )
    result = await db.execute(stmt)
    file_record = result.scalar_one_or_none()

    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    _authorize_file_access(file_record, current_user)

    if not file_record.analyzed:
        raise HTTPException(status_code=202, detail="Analysis still in progress")

    file_data = {
        "id": file_record.id,
        "original_name": file_record.original_name,
        "mime_type": file_record.mime_type,
        "size_bytes": file_record.size_bytes,
        "extension": file_record.extension,
        "sha256": file_record.sha256,
        "md5": file_record.md5,
        "sha1": file_record.sha1,
        "risk_score": file_record.risk_score,
        "verdict": file_record.verdict,
    }
    analysis_data = {
        "metadata_entry_count": len(file_record.metadata_entries),
        "threat_count": len(file_record.threat_matches),
    }

    report = ReportGenerator.generate_report(file_data, analysis_data)

    try:
        pdf_bytes = await ReportGenerator.export_pdf(report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF report: {str(e)}")

    # Sanitize the user-supplied filename before it goes into a response
    # header - an unsanitized value here would be a header-injection risk.
    safe_stem = re.sub(r'[^A-Za-z0-9._-]', '_', file_record.original_name or "report")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_stem}_report.pdf"'},
    )
