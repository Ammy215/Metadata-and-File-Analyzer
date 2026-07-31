from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import secrets
import hashlib
import re
from collections import defaultdict
from functools import lru_cache

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole, APIKey, AuditLog

# Password hashing with enterprise-grade settings
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Stronger than default (10)
)

# Rate limiting storage (in production, use Redis)
login_attempts = defaultdict(list)
failed_login_attempts = defaultdict(int)
MAX_LOGIN_ATTEMPTS = 5
LOGIN_ATTEMPT_WINDOW = 900  # 15 minutes

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
api_key_scheme = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash with enterprise security."""
    if not plain_password or not hashed_password:
        return False
    
    # Truncate password to 72 bytes for bcrypt compatibility
    plain_password_bytes = plain_password.encode('utf-8')[:72]
    
    try:
        return pwd_context.verify(plain_password_bytes.decode('utf-8'), hashed_password)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash a password with enterprise-grade security."""
    if not password:
        raise ValueError("Password cannot be empty")
    
    # Truncate password to 72 bytes for bcrypt compatibility
    password_bytes = password.encode('utf-8')[:72]
    return pwd_context.hash(password_bytes.decode('utf-8'))


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password meets enterprise security requirements.
    Returns: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if len(password) > 128:
        return False, "Password is too long (max 128 characters)"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    # Check for common patterns
    common_passwords = ['password', '12345678', 'qwerty', 'abc123']
    if password.lower() in common_passwords:
        return False, "Password is too common"
    
    return True, "Password is strong"


def check_rate_limit(identifier: str) -> bool:
    """
    Check if request should be rate limited.
    Returns True if rate limit exceeded.
    """
    now = datetime.now(timezone.utc).timestamp()
    cutoff = now - LOGIN_ATTEMPT_WINDOW
    
    # Clean old attempts
    login_attempts[identifier] = [
        attempt for attempt in login_attempts[identifier] 
        if attempt > cutoff
    ]
    
    # Check if too many attempts
    if len(login_attempts[identifier]) >= MAX_LOGIN_ATTEMPTS:
        return True
    
    return False


def record_login_attempt(identifier: str, success: bool):
    """Record a login attempt for rate limiting."""
    if not success:
        login_attempts[identifier].append(datetime.now(timezone.utc).timestamp())
        failed_login_attempts[identifier] += 1


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token with security claims."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
        "jti": secrets.token_urlsafe(16),  # JWT ID for token tracking
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token with security claims."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
        "jti": secrets.token_urlsafe(16),  # JWT ID for token tracking
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """Decode and verify a JWT token with type validation."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # Verify token type
        if payload.get("type") != token_type:
            raise JWTError("Invalid token type")
        
        # Check expiration explicitly
        exp = payload.get("exp")
        if exp and datetime.now(timezone.utc).timestamp() > exp:
            raise JWTError("Token has expired")
        
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Convert user_id string to UUID
    from uuid import UUID as UUIDType
    try:
        user_uuid = UUIDType(user_id)
    except (ValueError, AttributeError):
        raise credentials_exception
    
    # Get user from database
    stmt = select(User).where(User.id == user_uuid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get the current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get the current user and verify they are an admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin access required."
        )
    return current_user


async def get_current_super_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get the current user and verify they are a super admin."""
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Super admin access required."
        )
    return current_user


async def _get_user_by_api_key_value(key: str, db: AsyncSession) -> User:
    """Look up and return the User owning this raw API key value.

    Always resolves to that key's actual owner via the DB row it hashes
    to - never influenced by anything else in the request - so a key can
    only ever authenticate as itself. Shared by get_user_from_api_key and
    get_user_or_api_key below.
    """
    key_hash = hashlib.sha256(key.encode()).hexdigest()

    stmt = select(APIKey).where(
        APIKey.key_hash == key_hash,
        APIKey.is_active == True
    )
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired"
        )

    api_key.last_used = datetime.now(timezone.utc)
    await db.commit()

    stmt = select(User).where(User.id == api_key.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    return user


async def get_user_from_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(api_key_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get user from API key if provided (returns None rather than raising
    when no credentials are present - for call sites that want API-key
    auth without a JWT fallback)."""
    if not credentials:
        return None
    return await _get_user_by_api_key_value(credentials.credentials, db)


async def get_user_or_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(api_key_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Authenticate via either a JWT access token or an API key - both are
    presented identically (Authorization: Bearer <value>). JWT is tried
    first; if the value isn't a valid access token, falls back to an
    API-key lookup. Either path resolves to exactly one real User row
    looked up from the credential itself (the token's subject, or the
    key's owner) - a key can only ever authenticate as its own owner,
    the same guarantee JWT auth provides everywhere else in this app
    (analysis.py's _authorize_file_access, history.py's user_id filter,
    etc. all key off current_user.id, regardless of which method produced
    it), so per-user isolation is identical no matter which auth method
    the caller used.

    NOTE: this deliberately does NOT compose get_current_user (which
    depends on oauth2_scheme with auto_error=True) as a sub-dependency -
    in FastAPI, a sub-dependency that raises aborts the whole request
    immediately, so that composition would raise on any JWT failure and
    never actually reach the API-key fallback. This function inlines the
    JWT check instead, specifically so the fallback can work.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    token = credentials.credentials

    try:
        payload = decode_token(token)
    except HTTPException:
        payload = None

    if payload is not None:
        from uuid import UUID as UUIDType
        try:
            user_uuid = UUIDType(payload.get("sub"))
        except (ValueError, AttributeError, TypeError):
            user_uuid = None

        if user_uuid is not None:
            stmt = select(User).where(User.id == user_uuid)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            if user and user.is_active:
                return user

    # Not a valid/usable JWT - fall back to API-key lookup
    return await _get_user_by_api_key_value(token, db)


def generate_api_key() -> str:
    """Generate a secure random API key."""
    return secrets.token_urlsafe(32)


async def log_audit(
    db: AsyncSession,
    user_id: Optional[str],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[str] = None
):
    """Log an audit event."""
    from uuid import UUID as UUIDType
    
    # Convert string UUID to UUID object if needed
    user_uuid = None
    if user_id:
        user_uuid = UUIDType(user_id) if isinstance(user_id, str) else user_id
    
    audit_log = AuditLog(
        user_id=user_uuid,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details
    )
    db.add(audit_log)
    await db.commit()


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
