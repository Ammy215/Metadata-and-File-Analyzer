from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserCreate(BaseModel):
    """Schema for creating a new user."""
    email: EmailStr
    username: Optional[str] = None
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None

    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    """Schema for Google OAuth authentication."""
    id_token: str


class VerifyOtpRequest(BaseModel):
    """Schema for verifying an email OTP code."""
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)


class ResendOtpRequest(BaseModel):
    """Schema for requesting a new email OTP code."""
    email: EmailStr


class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""
    refresh_token: str


class UserResponse(BaseModel):
    """Schema for user response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    username: Optional[str]
    full_name: Optional[str]
    profile_picture: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]
    guest_expires_at: Optional[datetime] = None

    @field_validator('role', mode='before')
    @classmethod
    def serialize_role(cls, v):
        """Serialize role enum to uppercase string."""
        if hasattr(v, 'value'):
            return v.value.upper().replace('_', ' ')
        return str(v).upper().replace('_', ' ')


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    username: Optional[str] = None
    full_name: Optional[str] = None
    profile_picture: Optional[str] = None


class PasswordChange(BaseModel):
    """Schema for changing password."""
    current_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class APIKeyCreate(BaseModel):
    """Schema for creating an API key."""
    name: str
    expires_days: Optional[int] = None  # None = never expires


class APIKeyResponse(BaseModel):
    """Schema for API key response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    key: Optional[str] = None  # Only returned on creation
    created_at: datetime
    last_used: Optional[datetime]
    expires_at: Optional[datetime]
    is_active: bool


class UserAdminUpdate(BaseModel):
    """Schema for admin updating user (role, status)."""
    role: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class AuditLogResponse(BaseModel):
    """Schema for audit log response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: Optional[UUID]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    details: Optional[str]
    timestamp: datetime
