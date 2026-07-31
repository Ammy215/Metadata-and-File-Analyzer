from celery import Celery
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Celery
celery_app = Celery(
    "fileshield",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    # Bound broker-connection retries so a down broker fails fast rather
    # than retrying with growing backoff for minutes - this is what was
    # blocking the entire single-worker dev server on every upload whenever
    # Redis wasn't running. is_broker_available() below is the primary
    # guard (checked before ever calling .delay()); this is defense in depth
    # for the actual enqueue call itself.
    #
    # broker_connection_retry, unlike the _on_startup variant, governs
    # reconnection after a *previously working* connection drops - this
    # setting is shared by the celery_worker consumer process too (same
    # celery_app), and disabling it there caused the worker to permanently
    # shut down on any transient Redis blip instead of reconnecting once
    # Redis came back, silently stranding every file uploaded afterward in
    # "analysis in progress" forever. Confirmed by killing Redis mid-test:
    # the worker logged "Shutting down..." and never recovered, even after
    # Redis was healthy again, until manually restarted.
    broker_connection_retry_on_startup=False,
    broker_connection_retry=True,
    broker_transport_options={"max_retries": 1},
)


def is_broker_available(timeout: float = 1.5) -> bool:
    """Fast, bounded connectivity check against the Celery broker (Redis),
    used before enqueueing a task so a down broker returns a quick, honest
    answer instead of hanging on Celery's own internal reconnect/backoff
    loop for the duration of the whole HTTP request.

    Note: if CELERY_BROKER_URL resolves "localhost" to both an IPv6 and
    IPv4 address, a closed port can take up to 2x `timeout` (one attempt
    per address family) rather than erroring out instantly - worst case is
    still a few seconds, nowhere near Celery's own multi-minute retry loop.
    """
    import redis

    try:
        client = redis.from_url(
            settings.CELERY_BROKER_URL,
            socket_connect_timeout=timeout,
            socket_timeout=timeout,
        )
        return bool(client.ping())
    except Exception:
        return False


@celery_app.task(bind=True, max_retries=3)
def analyze_file_task(self, file_id: str, file_path: str):
    """
    Celery task for async file analysis.
    
    Args:
        file_id: UUID of the file
        file_path: Path to the file to analyze
    """
    try:
        import asyncio

        # asyncio.run() gives this task its own fresh event loop rather than
        # reusing/creating one via the deprecated get_event_loop() pattern -
        # matters because a long-lived Celery worker process runs many tasks.
        asyncio.run(_run_analysis(file_id, file_path))

        logger.info(f"Analysis completed for file {file_id}")
        return {"status": "success", "file_id": file_id}

    except Exception as exc:
        logger.error(f"Error analyzing file {file_id}: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


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


async def _run_analysis(file_id: str, file_path: str):
    """Internal async analysis function."""
    import json
    import uuid
    from pathlib import Path
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
    file_uuid = uuid.UUID(file_id)
    file_extension = file_path_obj.suffix.lower()

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

    # Calculate risk score
    entropy_score = entropy_data.get("entropy_score", 0)

    # Check for GPS and other flagged metadata. NOTE: these read
    # metadata_analyzer's own internal dict keys ("meta_key"/"flagged"),
    # which are unrelated to the ORM column names below - do not "fix"
    # these to match model column names, they're already correct.
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

    # Save to database
    async with async_session_maker() as session:
        # Update file record
        stmt = select(UploadedFile).where(UploadedFile.id == file_uuid)
        result = await session.execute(stmt)
        file_record = result.scalar_one()

        # Update hash values from analysis
        file_record.sha256 = hash_data.get("sha256", "")
        file_record.md5 = hash_data.get("md5", "")
        file_record.sha1 = hash_data.get("sha1", "")
        # Overwrite the client-supplied Content-Type with the server-verified
        # one (python-magic reading actual file content, not trusting the
        # browser's header) - this is what makes MIME-mismatch detection
        # meaningful rather than just re-storing whatever the client claimed.
        if mime_data.get("mime_type"):
            file_record.mime_type = mime_data["mime_type"]
        file_record.risk_score = risk_score
        file_record.verdict = verdict
        file_record.analyzed = True

        # Delete-then-insert per file_id makes this idempotent, so a Celery
        # retry (or a future manual re-scan) doesn't crash on the
        # entropy_results.file_id unique constraint or leave duplicate rows.
        for model in (MetadataEntry, ThreatMatch, RiskBreakdown, EntropyResult):
            await session.execute(delete(model).where(model.file_id == file_uuid))

        # Entropy result (1:1 with the file)
        entropy_details = {
            "byte_distribution": entropy_data.get("byte_distribution"),
            "risk": entropy_data.get("risk"),
            "is_compressed": entropy_data.get("is_compressed"),
            "is_encrypted": entropy_data.get("is_encrypted"),
            "file_size_bytes": entropy_data.get("file_size_bytes"),
        }
        session.add(EntropyResult(
            id=uuid.uuid4(),
            file_id=file_uuid,
            entropy_score=entropy_score,
            classification=entropy_data.get("classification"),
            details=entropy_details,
        ))

        # Metadata entries
        for entry in metadata_data.get("entries", []):
            session.add(MetadataEntry(
                id=uuid.uuid4(),
                file_id=file_uuid,
                category=entry.get("category"),
                key=entry.get("meta_key"),
                value=entry.get("meta_value"),
                flagged=entry.get("flagged", False),
            ))

        # Threat matches: keyword/URL matches and YARA rule matches share
        # this table, distinguished by match_type in matched_data.
        for match in threat_matches:
            match_type = match.get("match_type")
            line_number = match.get("line_number")
            description = (
                f"{match_type} match on line {line_number}" if line_number is not None
                else f"{match_type} match"
            )
            session.add(ThreatMatch(
                id=uuid.uuid4(),
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

        # Risk breakdown
        for factor in risk_factors:
            session.add(RiskBreakdown(
                id=uuid.uuid4(),
                file_id=file_uuid,
                factor_name=factor.get("factor"),
                weight=factor.get("weight"),
                contribution=factor.get("score_delta"),
                details=factor.get("detail"),
            ))

        await session.commit()
