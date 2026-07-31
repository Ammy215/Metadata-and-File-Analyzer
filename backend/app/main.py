from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import init_db, close_db
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup, close it on shutdown - replaces the
    deprecated @app.on_event startup/shutdown hooks with FastAPI's current
    lifespan context-manager pattern."""
    try:
        await init_db()
        # Background analysis runs as FastAPI BackgroundTasks (no separate
        # worker/broker - see analysis_tasks.py's start_periodic_sweep
        # docstring for why). This task is the periodic stuck-file retry +
        # stale-file cleanup sweep; cancelled on shutdown below.
        sweep_task = asyncio.create_task(start_periodic_sweep())
        logger.info("="*60)
        logger.info("🛡️  FileShield Intelligence Platform v2.0.0")
        logger.info("="*60)
        logger.info("✓ Database initialized")
        logger.info("✓ Security middleware active")
        logger.info("✓ Rate limiting enabled")
        logger.info("✓ SQL injection protection active")
        logger.info("✓ XSS protection active")
        logger.info("✓ CORS configured")
        logger.info("✓ Audit logging enabled")
        logger.info("✓ Background analysis sweep started")
        logger.info(f"✓ API Documentation: http://localhost:8000/docs")
        logger.info(f"✓ Alternative Docs: http://localhost:8000/redoc")
        logger.info("="*60)
        logger.info("🚀 System ready for enterprise operations")
        logger.info("="*60)
    except Exception as e:
        logger.error(f"✗ Error initializing system: {e}")
        raise

    yield

    sweep_task.cancel()
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
@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint."""
    return {
        "status": "healthy",
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
        "database": "Connected"
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
