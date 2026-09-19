from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.config import settings
from app.database import init_db, close_db, async_session_maker
from app.routers import upload, analysis, history, auth, admin
from app.utils.security import add_security_headers
from app.tasks.analysis_tasks import start_periodic_sweep
import logging
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Startup DB connection: 5 attempts with exponential backoff (1s, 2s, 4s,
# 8s - ~15s total) before giving up and booting degraded. The cap matters
# more for the recovery loop below than for startup itself.
DB_INIT_MAX_ATTEMPTS = 5
DB_INIT_BACKOFF_CAP_SECONDS = 30

# How often the degraded-mode recovery loop re-tries the database.
DB_RECOVERY_INTERVAL_SECONDS = 60

# Ceiling on the /health database probe so an unreachable database makes
# the endpoint answer "Unavailable" quickly instead of hanging on a TCP
# timeout - a health check that never responds reads as "down" to the
# platform, which is the outcome this whole module is trying to avoid.
HEALTH_DB_PROBE_TIMEOUT_SECONDS = 5

# False until init_db() has succeeded - at startup, or later from the
# recovery loop. Read by /health to report degraded state.
_db_ready = False

# asyncio only keeps weak references to tasks, so a task with no strong
# reference anywhere can be garbage-collected mid-flight. Holding them
# here keeps them alive and gives shutdown something to cancel.
_background_tasks: set[asyncio.Task] = set()


def _spawn(coro) -> asyncio.Task:
    """Start a background task and keep a strong reference to it."""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


async def _init_db_with_retry() -> bool:
    """Try init_db() with exponential backoff. Returns True on success.

    Never raises: the caller decides what an unreachable database means,
    and for this app the answer is "boot anyway", not "exit".
    """
    delay = 1
    for attempt in range(1, DB_INIT_MAX_ATTEMPTS + 1):
        try:
            await init_db()
            return True
        except Exception as e:
            if attempt == DB_INIT_MAX_ATTEMPTS:
                logger.error(
                    f"✗ Database unreachable after {DB_INIT_MAX_ATTEMPTS} attempts: {e}"
                )
                return False
            logger.warning(
                f"Database init attempt {attempt}/{DB_INIT_MAX_ATTEMPTS} failed "
                f"({e}) - retrying in {delay}s"
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, DB_INIT_BACKOFF_CAP_SECONDS)
    return False


async def _db_recovery_loop() -> None:
    """Keep retrying the database until it comes back, then leave degraded
    mode and start the sweep.

    This is what makes a database outage self-healing. Previously an
    unreachable database at boot raised out of the lifespan, which exits
    the process - and since the next boot hit the same unreachable
    database, the service stayed dead until a human redeployed it.
    """
    global _db_ready
    while not _db_ready:
        await asyncio.sleep(DB_RECOVERY_INTERVAL_SECONDS)
        try:
            await init_db()
        except Exception as e:
            logger.warning(f"Database still unreachable, staying degraded: {e}")
            continue

        _db_ready = True
        logger.info("="*60)
        logger.info("✓ Database reachable again - leaving degraded mode")
        logger.info("="*60)
        _spawn(start_periodic_sweep())


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup, close it on shutdown - replaces the
    deprecated @app.on_event startup/shutdown hooks with FastAPI's current
    lifespan context-manager pattern.

    A database that isn't reachable at boot is explicitly NOT fatal here.
    Serving HTTP in degraded mode keeps /health answering (so the platform
    doesn't kill the container) and lets the recovery loop restore full
    service on its own once the database returns.
    """
    global _db_ready

    _db_ready = await _init_db_with_retry()

    logger.info("="*60)
    logger.info("🛡️  FileShield Intelligence Platform v2.0.0")
    logger.info("="*60)

    if _db_ready:
        # Background analysis runs as FastAPI BackgroundTasks (no separate
        # worker/broker - see analysis_tasks.py's start_periodic_sweep
        # docstring for why). This task is the periodic stuck-file retry +
        # stale-file cleanup sweep; cancelled on shutdown below.
        _spawn(start_periodic_sweep())
        logger.info("✓ Database initialized")
        logger.info("✓ Background analysis sweep started")
    else:
        _spawn(_db_recovery_loop())
        logger.warning("⚠ DEGRADED MODE - database unreachable")
        logger.warning("⚠ Serving HTTP; database-backed endpoints will fail")
        logger.warning(
            f"⚠ Retrying every {DB_RECOVERY_INTERVAL_SECONDS}s - no redeploy needed"
        )

    logger.info("✓ Security middleware active")
    logger.info("✓ Rate limiting enabled")
    logger.info("✓ SQL injection protection active")
    logger.info("✓ XSS protection active")
    logger.info("✓ CORS configured")
    logger.info("✓ Audit logging enabled")
    logger.info(f"✓ API Documentation: http://localhost:8000/docs")
    logger.info(f"✓ Alternative Docs: http://localhost:8000/redoc")
    logger.info("="*60)
    logger.info(
        "🚀 System ready for enterprise operations" if _db_ready
        else "🟡 System up in degraded mode - waiting on database"
    )
    logger.info("="*60)

    yield

    for task in list(_background_tasks):
        task.cancel()
    try:
        await close_db()
        logger.info("✓ Database connection closed")
    except Exception as e:
        logger.error(f"✗ Error closing database: {e}")


# Create FastAPI app
app = FastAPI(
    title="FileShield Intelligence Platform",
    description="Enterprise-grade cybersecurity file analysis with advanced authentication",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Security Middleware - Add security headers to all responses
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Add security headers and logging to all requests."""
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}")
    
    # Process request
    response = await call_next(request)
    
    # Skip security headers for docs and openapi to allow Swagger UI to work
    if not request.url.path.startswith("/docs") and not request.url.path.startswith("/openapi") and not request.url.path.startswith("/redoc"):
        # Add security headers
        response = add_security_headers(response)
    
    # Log response time
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(f"Response: {response.status_code} in {process_time:.4f}s")
    
    return response

# Add CORS middleware with strict configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time"],
    max_age=3600,  # Cache preflight requests for 1 hour
)


# Include routers
app.include_router(auth.router)  # Authentication routes
app.include_router(admin.router)  # Admin dashboard routes
app.include_router(upload.router)  # File upload routes
app.include_router(analysis.router)  # Analysis routes
app.include_router(history.router)  # History routes


# Health check endpoint
async def _probe_database() -> None:
    """One lightweight round-trip to confirm the database answers."""
    async with async_session_maker() as session:
        await session.execute(text("SELECT 1"))


@app.get("/health")
async def health_check():
    """Health check endpoint. Always returns HTTP 200, deliberately.

    Degraded state is reported in the body, never via the status code.
    Render (like most platforms) treats a non-2xx health check as "replace
    this container", so returning 503 while the database is down would
    destroy the service during precisely the outage degraded mode exists
    to survive. Do not "fix" this to return 503.

    The SELECT 1 is a real probe rather than a hardcoded "Connected", so
    the reported value is honest. That also means this endpoint hits the
    database on every call: do NOT aim a frequent uptime pinger at it on a
    metered or scale-to-zero provider. Doing exactly that kept the compute
    permanently awake and burned a full month's allowance in ~17 days.
    Point uptime pingers at / instead, which touches nothing.
    """
    try:
        await asyncio.wait_for(
            _probe_database(), timeout=HEALTH_DB_PROBE_TIMEOUT_SECONDS
        )
        db_status = "Connected"
    except Exception as e:
        logger.error(f"Health check DB probe failed: {e}")
        db_status = "Unavailable"

    # _db_ready covers the case where the database answers but schema init
    # hasn't succeeded yet - reachable is not the same as ready.
    degraded = db_status != "Connected" or not _db_ready

    return {
        "status": "degraded" if degraded else "healthy",
        "version": "2.0.0",
        "security": {
            "authentication": "JWT + OAuth2",
            "password_hashing": "BCrypt (rounds=12)",
            "rate_limiting": "Active",
            "sql_injection_protection": "Active",
            "xss_protection": "Active",
            "security_headers": "Enforced",
            "audit_logging": "Enabled"
        },
        "features": {
            "authentication": True,
            "google_oauth": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_ID != "NOT_CONFIGURED_OPTIONAL"),
            "admin_dashboard": True,
            "file_analysis": True,
            "api_keys": True,
            "audit_logs": True
        },
        "database": db_status
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "FileShield Intelligence Platform",
        "version": "2.0.0",
        "description": "Production-grade cybersecurity file analysis with authentication",
        "docs_url": "/docs",
        "openapi_schema": "/openapi.json",
        "features": [
            "User Authentication (Email/Password)",
            "Google OAuth Integration",
            "Role-Based Access Control (User/Admin/Super Admin)",
            "File Intelligence Analysis",
            "Admin Dashboard",
            "API Key Management",
            "Audit Logging"
        ]
    }


# Error handling
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
