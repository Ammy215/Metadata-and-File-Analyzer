"""File analysis, run as a FastAPI BackgroundTask rather than a separate
Celery worker - see the docstring on start_periodic_sweep() for why, and
what that trades away.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID

from app.config import settings

logger = logging.getLogger(__name__)

# A file stuck at analyzed=False past this age almost certainly means the
# process was killed mid-analysis (a restart/redeploy/crash) rather than
# still legitimately running - real analysis finishes in seconds, even for
# large video files, confirmed throughout testing. Past the upper bound,
# stop retrying (a genuinely poison file that keeps failing shouldn't be
# retried forever) and just let the normal deletion window eventually
# clean up its raw bytes.
STUCK_RETRY_MIN_AGE = timedelta(minutes=30)
STUCK_RETRY_MAX_AGE = timedelta(hours=6)

# Files are deleted right after analysis completes (see run_analysis), so
# under normal operation nothing should still have a raw file this old.
# This is the safety net for whatever slips past that - a crashed task
# that also exceeded the stuck-retry window above, or anything else.
DELETE_MIN_AGE = timedelta(hours=48)
DELETE_MAX_AGE = timedelta(days=30)

SWEEP_INTERVAL_SECONDS = 15 * 60


async def run_analysis(file_id: str, file_path: str) -> None:
    """
    Analyze an uploaded file and persist the results. Called directly as a
    BackgroundTask from the upload endpoint, and again by the periodic
    sweep below if a file gets stuck (e.g. the process was killed mid-run).

    Safe to call twice for the same file_id in the ordinary case where the
    first call already finished: the DB writes are delete-then-insert
    (idempotent) and re-deleting an already-deleted raw file is a no-op.
    Concurrent double-execution of a still-genuinely-running analysis is
    not guarded against - the sweep's 30-minute floor makes that
    practically impossible given how fast real analysis actually runs.
    """
    import json
    import uuid as uuid_module
    from sqlalchemy import select, delete
    from app.database import async_session_maker
    from app.models.file_record import UploadedFile, MetadataEntry, ThreatMatch, EntropyResult, RiskBreakdown
    from app.analyzers.hash_analyzer import HashAnalyzer
    from app.analyzers.entropy_analyzer import EntropyAnalyzer
    from app.analyzers.metadata_analyzer import MetadataAnalyzer
    from app.analyzers.keyword_analyzer import KeywordAnalyzer
    from app.analyzers.mime_analyzer import MimeAnalyzer
    from app.analyzers.specialized_analyzers import YARAAnalyzer
    from app.analyzers.risk_engine import RiskEngine
    from app.analyzers.file_type_router import get_extra_analyzer

    file_path_obj = Path(file_path)
    file_uuid = UUID(file_id)
    file_extension = file_path_obj.suffix.lower()

    if not file_path_obj.exists():
        logger.warning(f"run_analysis called for {file_id} but {file_path} no longer exists - skipping")
        return

    try:
        # Universal analyzers - run for every file regardless of type
        hash_analyzer = HashAnalyzer()
        entropy_analyzer = EntropyAnalyzer()
        metadata_analyzer = MetadataAnalyzer()
        keyword_analyzer = KeywordAnalyzer()
        mime_analyzer = MimeAnalyzer()
        yara_analyzer = YARAAnalyzer()

        hash_data = await hash_analyzer.analyze(file_path_obj)
        entropy_data = await entropy_analyzer.analyze(file_path_obj, file_extension)
        metadata_data = await metadata_analyzer.analyze(file_path_obj)
        keyword_data = await keyword_analyzer.analyze(file_path_obj)
        mime_data = await mime_analyzer.analyze(file_path_obj)
        yara_data = await yara_analyzer.analyze(file_path_obj)

        # Format-specific analyzer, if this extension has one (PDF/Excel/
        # Markdown/Video/Audio/PE) - None for everything else (images, docx,
        # archives, plain code/text, etc.)
        extra_analyzer_cls = get_extra_analyzer(file_extension)
        extra_data = await extra_analyzer_cls().analyze(file_path_obj) if extra_analyzer_cls else None
        if extra_data:
            metadata_data.setdefault("entries", []).extend(
                _extra_analyzer_metadata_entries(file_extension, extra_data)
            )

        # Fold YARA matches into the same threat-match list keyword scanning
        # produces, so both surface identically to the API/report.
        threat_matches = keyword_data.get("matches", [])
        for yara_match in yara_data.get("matches", []):
            threat_matches.append({
                "match_type": "yara",
                "matched_value": yara_match.get("rule_name"),
                "severity": yara_match.get("severity", "HIGH"),
                "line_number": None,
                "context_line": ", ".join(yara_match.get("tags", [])) or None,
            })

        entropy_score = entropy_data.get("entropy_score", 0)

        # NOTE: these read metadata_analyzer's own internal dict keys
        # ("meta_key"/"flagged"), unrelated to the ORM column names below -
        # do not "fix" these to match model column names, they're correct.
        has_hidden_metadata = len(metadata_data.get("flagged_items", [])) > 0
        has_gps = any("GPS" in str(entry.get("meta_key", "")) for entry in metadata_data.get("entries", []))
        mime_mismatch = _is_mime_mismatch(file_extension, mime_data.get("mime_type", ""))

        risk_score, verdict, risk_factors = RiskEngine.calculate_risk(
            threat_matches,
            entropy_score,
            file_extension,
            has_hidden_metadata,
            yara_matches=len(yara_data.get("matches", [])),
            has_gps=has_gps,
            mime_mismatch=mime_mismatch,
            pe_data=extra_data if file_extension in {".exe", ".dll"} else None,
            pdf_data=extra_data if file_extension == ".pdf" else None,
            excel_data=extra_data if file_extension == ".xlsx" else None,
        )

        async with async_session_maker() as session:
            stmt = select(UploadedFile).where(UploadedFile.id == file_uuid)
            result = await session.execute(stmt)
            file_record = result.scalar_one()

            file_record.sha256 = hash_data.get("sha256", "")
            file_record.md5 = hash_data.get("md5", "")
            file_record.sha1 = hash_data.get("sha1", "")
            # Overwrite the client-supplied Content-Type with the
            # server-verified one (python-magic reading actual file
            # content, not trusting the browser's header).
            if mime_data.get("mime_type"):
                file_record.mime_type = mime_data["mime_type"]
            file_record.risk_score = risk_score
            file_record.verdict = verdict
            file_record.analyzed = True

            # Delete-then-insert per file_id makes this idempotent, so a
            # stuck-file retry from the sweep doesn't crash on the
            # entropy_results.file_id unique constraint or leave duplicates.
            for model in (MetadataEntry, ThreatMatch, RiskBreakdown, EntropyResult):
                await session.execute(delete(model).where(model.file_id == file_uuid))

            entropy_details = {
                "byte_distribution": entropy_data.get("byte_distribution"),
                "risk": entropy_data.get("risk"),
                "is_compressed": entropy_data.get("is_compressed"),
                "is_encrypted": entropy_data.get("is_encrypted"),
                "file_size_bytes": entropy_data.get("file_size_bytes"),
            }
            session.add(EntropyResult(
                id=uuid_module.uuid4(),
                file_id=file_uuid,
                entropy_score=entropy_score,
                classification=entropy_data.get("classification"),
                details=entropy_details,
            ))

            for entry in metadata_data.get("entries", []):
                session.add(MetadataEntry(
                    id=uuid_module.uuid4(),
                    file_id=file_uuid,
                    category=entry.get("category"),
                    key=entry.get("meta_key"),
                    value=entry.get("meta_value"),
                    flagged=entry.get("flagged", False),
                ))

            for match in threat_matches:
                match_type = match.get("match_type")
                line_number = match.get("line_number")
                description = (
                    f"{match_type} match on line {line_number}" if line_number is not None
                    else f"{match_type} match"
                )
                session.add(ThreatMatch(
                    id=uuid_module.uuid4(),
                    file_id=file_uuid,
                    rule_name=match.get("matched_value"),
                    severity=match.get("severity"),
                    description=description,
                    matched_data=json.dumps({
                        "match_type": match_type,
                        "line_number": line_number,
                        "context": match.get("context_line"),
                    }),
                ))

            for factor in risk_factors:
                session.add(RiskBreakdown(
                    id=uuid_module.uuid4(),
                    file_id=file_uuid,
                    factor_name=factor.get("factor"),
                    weight=factor.get("weight"),
                    contribution=factor.get("score_delta"),
                    details=factor.get("detail"),
                ))

            await session.commit()

        logger.info(f"Analysis completed for file {file_id}")

        # Raw bytes are only ever needed transiently, during analysis
        # itself - nothing in the app serves the original file back
        # afterward (only a generated PDF report), and every actual result
        # now lives in the rows just committed above.
        try:
            file_path_obj.unlink(missing_ok=True)
        except OSError as e:
            logger.warning(f"Could not delete analyzed file {file_path}: {e}")

    except Exception as exc:
        logger.error(f"Error analyzing file {file_id}: {exc}")
        # No retry here (no queue to redeliver to) - the periodic sweep's
        # stuck-file check is what recovers this, whether the failure was
        # a crash mid-run or a genuine exception like this one.


_EXECUTABLE_MIME_SIGNATURES = {
    "application/x-dosexec", "application/x-executable", "application/x-sharedlib",
    "application/x-mach-binary", "application/x-elf", "application/x-msdownload",
    # The libmagic database actually shipped in the deployed (Debian-based)
    # container identifies real Windows PE binaries with this string, not
    # application/x-dosexec - confirmed by uploading a genuine PE file
    # disguised as .txt and finding this was the exact case that failed to
    # flag as a mismatch, defeating the one scenario this check exists for.
    "application/vnd.microsoft.portable-executable",
}


def _is_mime_mismatch(extension: str, mime_type: str) -> bool:
    """Flag the highest-confidence mismatch case: content that's actually
    an executable disguised behind a non-executable extension (a real
    file-content check, not just the extension the client sent).

    Deliberately narrow rather than a general extension<->mime
    compatibility matrix: many legitimate formats are themselves
    zip/container based (.xlsx/.docx detect as application/zip, etc.) and
    a broad mapping would misfire on those without a much larger curated
    table. This targets the specific case that matters most: something
    claiming to be a document/image/text file that's actually a binary.
    """
    from app.utils.file_validator import FileValidator
    return mime_type in _EXECUTABLE_MIME_SIGNATURES and extension not in FileValidator.EXECUTABLE_EXTENSIONS


def _extra_analyzer_metadata_entries(extension: str, extra_data: dict) -> list:
    """Turn a format-specific analyzer's output into the same
    {category, meta_key, meta_value, flagged}-shaped dicts that
    MetadataAnalyzer produces, so they flow through the same MetadataEntry
    write path. Kept deliberately small (counts/flags, not full dumps like
    PDF text_content or the raw imports list) - this is for display/audit,
    not bulk data storage.
    """
    entries = []

    def add(category, key, value, flagged=False):
        entries.append({"category": category, "meta_key": key, "meta_value": str(value), "flagged": flagged})

    if extension == ".pdf":
        add("pdf_security", "pages", extra_data.get("pages", 0))
        add("pdf_security", "has_javascript", extra_data.get("has_javascript", False), flagged=extra_data.get("has_javascript", False))
        add("pdf_security", "has_embedded_objects", extra_data.get("has_embedded_objects", False), flagged=extra_data.get("has_embedded_objects", False))
        add("pdf_security", "has_forms", extra_data.get("has_forms", False))

    elif extension == ".xlsx":
        add("excel", "sheets", ", ".join(extra_data.get("sheets", [])) or "none")
        add("excel", "has_formulas", extra_data.get("has_formulas", False))
        add("excel", "has_macros", extra_data.get("has_macros", False), flagged=extra_data.get("has_macros", False))
        add("excel", "has_external_links", extra_data.get("has_external_links", False), flagged=extra_data.get("has_external_links", False))

    elif extension in {".md", ".markdown"}:
        add("markdown", "headings", extra_data.get("headings", 0))
        add("markdown", "link_count", len(extra_data.get("links", [])))
        add("markdown", "has_code_blocks", extra_data.get("has_code_blocks", False))
        add("markdown", "has_html", extra_data.get("has_html", False))

    elif extension in {".exe", ".dll"}:
        add("pe_security", "is_pe", extra_data.get("is_pe", False))
        add("pe_security", "import_count", len(extra_data.get("imports", [])))
        add("pe_security", "section_count", len(extra_data.get("sections", [])))
        add("pe_security", "has_suspicious_strings", extra_data.get("has_suspicious_strings", False), flagged=extra_data.get("has_suspicious_strings", False))

    else:
        # Video/audio. ffprobe_available surfaced explicitly (flagged when
        # False) so "couldn't check" is visible rather than looking like a
        # clean scan with blank/zero fields.
        if extra_data.get("ffprobe_available") is False:
            add("media", "ffprobe_available", False, flagged=True)
        for key in ("duration", "codec", "bitrate", "width", "height", "sample_rate", "channels"):
            if key in extra_data:
                add("media", key, extra_data[key])

    return entries


async def sweep_once() -> None:
    """
    One pass of: (1) re-trigger analysis for files stuck at analyzed=False
    for 30min-6h (almost certainly a process restart/crash mid-analysis,
    since real analysis takes seconds), and (2) delete raw files left over
    from uploads 48h-30d old regardless of status, as a backstop for
    whatever ( 1) doesn't catch. Called every SWEEP_INTERVAL_SECONDS by
    start_periodic_sweep().
    """
    from sqlalchemy import select
    from app.database import async_session_maker
    from app.models.file_record import UploadedFile

    now = datetime.utcnow()

    async with async_session_maker() as session:
        stuck_stmt = select(UploadedFile).where(
            UploadedFile.analyzed == False,  # noqa: E712
            UploadedFile.upload_time <= now - STUCK_RETRY_MIN_AGE,
            UploadedFile.upload_time > now - STUCK_RETRY_MAX_AGE,
        )
        stuck_files = (await session.execute(stuck_stmt)).scalars().all()

    for file_record in stuck_files:
        file_path = Path(settings.UPLOAD_DIR) / file_record.stored_name
        logger.info(f"Sweep: retrying stuck analysis for file {file_record.id}")
        await run_analysis(str(file_record.id), str(file_path))

    async with async_session_maker() as session:
        delete_stmt = select(UploadedFile).where(
            UploadedFile.upload_time >= now - DELETE_MAX_AGE,
            UploadedFile.upload_time < now - DELETE_MIN_AGE,
        )
        stale_files = (await session.execute(delete_stmt)).scalars().all()

    deleted_count = 0
    for file_record in stale_files:
        file_path = Path(settings.UPLOAD_DIR) / file_record.stored_name
        try:
            if file_path.exists():
                file_path.unlink()
                deleted_count += 1
        except OSError as e:
            logger.warning(f"Sweep could not delete {file_path}: {e}")

    if stuck_files or deleted_count:
        logger.info(
            f"Sweep: retried {len(stuck_files)} stuck file(s), deleted {deleted_count} stale file(s)"
        )


async def start_periodic_sweep() -> None:
    """
    Runs sweep_once() every SWEEP_INTERVAL_SECONDS for the lifetime of the
    process. Started from main.py's lifespan as an asyncio background task.

    This replaces a separate Celery worker + Redis broker + Celery Beat
    scheduler. That combination was built and tested earlier (including
    proving it survives a broker outage), but free-tier hosting (Render)
    has no free tier for always-on background workers at all - only Web
    Services, Static Sites, Postgres, and Key-Value are free. Running
    Celery's worker for genuinely $0 would mean disguising it as a Web
    Service behind a fake health-check endpoint and paying an external
    pinger to keep it from sleeping, which is a workaround on a workaround.

    The real trade-off: a FastAPI BackgroundTask has no durable queue, so a
    process restart/crash mid-analysis kills that task outright, whereas a
    Celery task's message would normally survive in Redis. In practice
    that theoretical advantage wasn't fully realized here either - this
    codebase never set task_acks_late, so a worker killed mid-task (as
    opposed to just losing its Redis connection, which was tested) would
    have lost the task anyway. The stuck-file retry in sweep_once() is the
    mitigation: not as strong a guarantee as a properly-configured durable
    queue, but it self-heals a mid-restart interruption within about 15-45
    minutes without any manual intervention, which is what was verified.
    """
    while True:
        try:
            await sweep_once()
        except Exception as e:
            logger.error(f"Periodic sweep failed: {e}")
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
