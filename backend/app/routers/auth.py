from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from google.oauth2 import id_token
from google.auth.transport import requests
from datetime import datetime, timedelta, timezone
import hashlib

from app.database import get_db
from app.models.user import User, UserRole, AuthProvider, APIKey
from app.schemas.auth import (
    UserCreate, UserLogin, UserResponse, TokenResponse,
    GoogleAuthRequest, RefreshTokenRequest, PasswordChange,
    APIKeyCreate, APIKeyResponse, UserUpdate
)
from app.utils.auth import (
    get_password_hash, verify_password, create_access_token,
    create_refresh_token, decode_token, get_current_user,
    get_current_active_user, generate_api_key, log_audit, get_client_ip,
    check_rate_limit as check_login_rate_limit, record_login_attempt,
)
from app.utils.security import check_rate_limit as check_general_rate_limit
from app.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user with email and password."""

    # Blunt per-IP cap regardless of success/failure - spam registration
    # is the concern here, not credential guessing.
    await check_general_rate_limit(request, max_requests=3, window_seconds=3600)

    # Check if email already exists
    stmt = select(User).where(User.email == user_data.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username already exists
    if user_data.username:
        stmt = select(User).where(User.username == user_data.username)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        auth_provider=AuthProvider.LOCAL,
        role=UserRole.USER,
        is_verified=False  # Require email verification in production
        # DO NOT set last_login on registration - only on actual login
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Log audit
    await log_audit(
        db=db,
        user_id=str(new_user.id),
        action="REGISTER",
        resource_type="user",
        resource_id=str(new_user.id),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        details=f"New user registered: {new_user.email}"
    )
    
    return new_user


@router.post("/login", response_model=TokenResponse)
async def login(
    user_data: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Login with email and password."""

    # Only failed attempts count toward the limit (record_login_attempt
    # below only appends on success=False), so a legitimate user who
    # mistypes their password once or twice isn't punished once they get
    # it right - unlike a blunt "N requests per window" counter.
    identifier = get_client_ip(request)
    if check_login_rate_limit(identifier):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again in 15 minutes.",
        )

    # Find user by email
    stmt = select(User).where(User.email == user_data.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        record_login_attempt(identifier, success=False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Verify password
    if not verify_password(user_data.password, user.hashed_password):
        record_login_attempt(identifier, success=False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    record_login_attempt(identifier, success=True)

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    
    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    # Log audit
    await log_audit(
        db=db,
        user_id=str(user.id),
        action="LOGIN",
        resource_type="user",
        resource_id=str(user.id),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        details=f"User logged in: {user.email}"
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Record an explicit logout. JWTs aren't revoked here (this app has no
    token blocklist - the token still technically works until it expires),
    but last_logout lets the admin's "who's online" view distinguish a real
    logout from a session that's merely between heartbeats, instead of
    relying purely on how recently the last heartbeat landed."""
    current_user.last_logout = datetime.now(timezone.utc)
    await db.commit()

    await log_audit(
        db=db,
        user_id=str(current_user.id),
        action="LOGOUT",
        resource_type="user",
        resource_id=str(current_user.id),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        details=f"User logged out: {current_user.email}"
    )

    return {"message": "Logged out successfully"}


@router.post("/google", response_model=TokenResponse)
async def google_auth(
    auth_data: GoogleAuthRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate with Google OAuth."""
    
    try:
        # Verify Google ID token
        idinfo = id_token.verify_oauth2_token(
            auth_data.id_token,
            requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )
        
        # Get user info from token
        google_id = idinfo['sub']
        email = idinfo['email']
        full_name = idinfo.get('name')
        profile_picture = idinfo.get('picture')
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}"
        )
    
    # Check if user exists with this Google ID
    stmt = select(User).where(User.google_id == google_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        # Check if email already exists (link accounts)
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            # Link Google account to existing user
            user.google_id = google_id
            user.profile_picture = profile_picture
            user.auth_provider = AuthProvider.GOOGLE
        else:
            # Create new user
            user = User(
                email=email,
                full_name=full_name,
                profile_picture=profile_picture,
                google_id=google_id,
                auth_provider=AuthProvider.GOOGLE,
                role=UserRole.USER,
                is_verified=True  # Google accounts are pre-verified
            )
            db.add(user)
    
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)
    
    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    # Log audit
    await log_audit(
        db=db,
        user_id=str(user.id),
        action="LOGIN",
        resource_type="user",
        resource_id=str(user.id),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        details=f"User logged in via Google: {user.email}"
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token."""
    
    try:
        payload = decode_token(refresh_data.refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        
        # Verify user still exists and is active
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new tokens
        access_token = create_access_token(data={"sub": str(user.id)})
        new_refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user information and update last activity."""
    # Update last_login to track active session (heartbeat)
    current_user.last_login = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/heartbeat")
async def session_heartbeat(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user's last activity timestamp (session heartbeat)."""
    current_user.last_login = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "ok", "timestamp": current_user.last_login.isoformat()}


@router.put("/me", response_model=UserResponse)
async def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user profile."""
    
    if user_update.username:
        # Check if username is taken by another user
        stmt = select(User).where(
            User.username == user_update.username,
            User.id != current_user.id
        )
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        current_user.username = user_update.username
    
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    
    if user_update.profile_picture is not None:
        current_user.profile_picture = user_update.profile_picture
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Change user password."""
    
    if not current_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change password for OAuth accounts"
        )
    
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect current password"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()
    
    return {"message": "Password changed successfully"}


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new API key for the current user."""
    
    # Generate API key
    key = generate_api_key()
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    
    # Calculate expiration
    expires_at = None
    if key_data.expires_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=key_data.expires_days)
    
    # Create API key record
    api_key = APIKey(
        user_id=current_user.id,
        key_hash=key_hash,
        name=key_data.name,
        expires_at=expires_at
    )
    
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    
    # Return key only once (on creation)
    response = APIKeyResponse.model_validate(api_key)
    response.key = key
    
    return response


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List all API keys for the current user."""
    
    stmt = select(APIKey).where(APIKey.user_id == current_user.id)
    result = await db.execute(stmt)
    api_keys = result.scalars().all()
    
    return api_keys


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an API key."""
    
    stmt = select(APIKey).where(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    )
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    await db.delete(api_key)
    await db.commit()
    
    return {"message": "API key deleted successfully"}
