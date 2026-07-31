"""
Enterprise-Level Security Utilities
Protect against common web vulnerabilities
"""
import re
import html
from typing import Any, Dict
from fastapi import Request, HTTPException, status
from datetime import datetime, timedelta, timezone


class SecurityValidator:
    """Enterprise security validation and sanitization."""
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\bunion\b.*\bselect\b)",
        r"(\bselect\b.*\bfrom\b)",
        r"(\binsert\b.*\binto\b)",
        r"(\bdelete\b.*\bfrom\b)",
        r"(\bdrop\b.*\btable\b)",
        r"(\bexec\b.*\()",
        r"(\bscript\b.*>)",
        r"(--|\#|\/\*)",
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"<script[\s\S]*?>[\s\S]*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
        r"<object",
        r"<embed",
    ]
    
    @classmethod
    def detect_sql_injection(cls, text: str) -> bool:
        """Detect potential SQL injection attempts."""
        if not text:
            return False
        
        text_lower = text.lower()
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def detect_xss(cls, text: str) -> bool:
        """Detect potential XSS attacks."""
        if not text:
            return False
        
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def sanitize_input(cls, text: str) -> str:
        """Sanitize user input to prevent XSS."""
        if not text:
            return text
        
        # HTML escape
        sanitized = html.escape(text)
        
        # Remove any remaining script tags
        sanitized = re.sub(r'<script[\s\S]*?>[\s\S]*?</script>', '', sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    @classmethod
    def validate_input(cls, text: str, field_name: str = "input") -> str:
        """
        Validate and sanitize user input.
        Raises HTTPException if malicious content detected.
        """
        if not text:
            return text
        
        # Check for SQL injection
        if cls.detect_sql_injection(text):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid {field_name}: Potential security threat detected"
            )
        
        # Check for XSS
        if cls.detect_xss(text):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid {field_name}: Potential XSS attack detected"
            )
        
        # Sanitize and return
        return cls.sanitize_input(text)
    
    @classmethod
    def validate_email(cls, email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @classmethod
    def validate_filename(cls, filename: str) -> str:
        """Validate and sanitize filename to prevent directory traversal."""
        if not filename:
            raise ValueError("Filename cannot be empty")
        
        # Remove path traversal attempts
        filename = filename.replace('..', '').replace('/', '').replace('\\', '')
        
        # Remove any non-alphanumeric except dots, dashes, underscores
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        
        if not filename or filename in ['.', '..']:
            raise ValueError("Invalid filename")
        
        return filename


class RateLimiter:
    """Simple in-memory rate limiter (use Redis in production)."""
    
    def __init__(self):
        self.requests: Dict[str, list] = {}
    
    def is_rate_limited(
        self, 
        identifier: str, 
        max_requests: int = 100, 
        window_seconds: int = 60
    ) -> bool:
        """
        Check if identifier has exceeded rate limit.
        Returns True if rate limited.
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=window_seconds)
        
        # Initialize if first request
        if identifier not in self.requests:
            self.requests[identifier] = []
        
        # Remove old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if req_time > cutoff
        ]
        
        # Check if over limit
        if len(self.requests[identifier]) >= max_requests:
            return True
        
        # Record this request
        self.requests[identifier].append(now)
        return False
    
    def get_request_count(self, identifier: str) -> int:
        """Get current request count for identifier."""
        return len(self.requests.get(identifier, []))


# Global rate limiter instance
rate_limiter = RateLimiter()


def get_request_identifier(request: Request) -> str:
    """Get unique identifier for rate limiting."""
    # Use IP address as identifier
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"
    
    return ip


async def check_rate_limit(request: Request, max_requests: int = 100, window_seconds: int = 60):
    """Middleware to check rate limiting."""
    identifier = get_request_identifier(request)
    
    if rate_limiter.is_rate_limited(identifier, max_requests, window_seconds):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later."
        )


def add_security_headers(response):
    """Add security headers to response."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response
