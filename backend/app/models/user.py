from sqlalchemy import Column, String, Boolean, Integer, TIMESTAMP, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
import enum
from typing import TYPE_CHECKING
from app.database import Base

if TYPE_CHECKING:
    from app.models.file_record import UploadedFile


def _utcnow() -> datetime:
    """Timezone-aware UTC now, for TIMESTAMP(timezone=True) column defaults.

    datetime.utcnow() (used previously) returns a naive datetime with no
    tzinfo - Pydantic/FastAPI then serializes it to JSON with no offset
    (e.g. "2026-07-31T14:34:06"), which browsers interpret as LOCAL time
    per the ECMAScript Date Time String spec, not UTC. That silently
    shifted every displayed timestamp app-wide by the viewer's UTC offset
    (an admin audit log looked hours stale/off). Storing and serializing
    timezone-aware values fixes this at the source.
    """
    return datetime.now(timezone.utc)


class UserRole(enum.Enum):
    """User role enumeration."""
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
    GUEST = "guest"


class AuthProvider(enum.Enum):
    """Authentication provider enumeration."""
    LOCAL = "local"
    GOOGLE = "google"
    GITHUB = "github"


class User(Base):
    """User model with authentication and authorization."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=True, index=True)
    full_name = Column(String, nullable=True)
    
    # Authentication
    hashed_password = Column(String, nullable=True)  # Null for OAuth users
    auth_provider = Column(Enum(AuthProvider), default=AuthProvider.LOCAL, nullable=False)
    google_id = Column(String, unique=True, nullable=True)  # Google OAuth ID
    github_id = Column(String, unique=True, nullable=True)  # GitHub OAuth ID
    profile_picture = Column(String, nullable=True)
    
    # Authorization
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Email OTP verification. otp_attempts caps brute-forcing the 6-digit
    # code (locked out after 5 wrong tries, forcing a fresh resend) rather
    # than relying on request rate-limiting alone.
    otp_code = Column(String, nullable=True)
    otp_expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    otp_attempts = Column(Integer, default=0, nullable=False)

    # Only set for role=GUEST. Checked on every authenticated request (see
    # utils/auth.py) for an immediate cutoff, and swept up by the periodic
    # sweep in analysis_tasks.py which hard-deletes the row (and, via the
    # relationship cascades below, everything the guest uploaded).
    guest_expires_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), default=_utcnow)
    last_login = Column(TIMESTAMP(timezone=True), nullable=True)
    # Set only by an explicit POST /auth/logout - lets "is this user
    # actually online" be a real fact (last_logout newer than last_login)
    # instead of purely inferred from how recently a heartbeat landed,
    # which can't tell a genuine logout apart from a session just idling.
    last_logout = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # Relationships
    uploaded_files = relationship("UploadedFile", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.email} ({self.role.value})>"
    
    @property
    def is_admin(self):
        """Check if user has admin privileges."""
        return self.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
    
    @property
    def is_super_admin(self):
        """Check if user is super admin."""
        return self.role == UserRole.SUPER_ADMIN


class APIKey(Base):
    """API Key model for programmatic access."""
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    key_hash = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)  # User-friendly name
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), default=_utcnow)
    last_used = Column(TIMESTAMP(timezone=True), nullable=True)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="api_keys")


class AuditLog(Base):
    """Audit log for tracking user actions."""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)  # Nullable for anonymous actions
    action = Column(String, nullable=False)  # e.g., "file_upload", "file_delete", "user_login"
    resource_type = Column(String, nullable=True)  # e.g., "file", "user"
    resource_id = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    details = Column(String, nullable=True)  # JSON string with additional info
    timestamp = Column(TIMESTAMP(timezone=True), default=_utcnow, index=True)
    
    # Relationship
    user = relationship("User", back_populates="audit_logs")
