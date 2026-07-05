"""
Pydantic v2 models for authentication endpoints.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr, ConfigDict


class TokenRequest(BaseModel):
    """Request model for token generation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "api_user",
                "password": "secure_password",
            }
        }
    )

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Username or email",
    )
    password: str = Field(
        ...,
        min_length=8,
        description="User password",
    )
    scopes: Optional[List[str]] = Field(
        default=None,
        description="Requested scopes",
    )


class TokenResponse(BaseModel):
    """Response model for token generation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400,
                "scopes": ["read", "write"],
            }
        }
    )

    access_token: str = Field(..., description="JWT access token")
    refresh_token: Optional[str] = Field(None, description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., gt=0, description="Token expiration in seconds")
    scopes: List[str] = Field(default_factory=list, description="Granted scopes")


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""

    refresh_token: str = Field(..., description="Refresh token")


class UserCreate(BaseModel):
    """Request model for user creation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "new_user",
                "email": "user@example.com",
                "password": "secure_password",
                "full_name": "John Doe",
            }
        }
    )

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern="^[a-zA-Z0-9_]+$",
        description="Username (alphanumeric and underscores only)",
    )
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User password (min 8 characters)",
    )
    full_name: Optional[str] = Field(
        None,
        max_length=100,
        description="Full name",
    )


class UserResponse(BaseModel):
    """Response model for user information."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "user_123",
                "username": "api_user",
                "email": "user@example.com",
                "full_name": "John Doe",
                "is_active": True,
                "is_admin": False,
                "scopes": ["read", "write"],
                "created_at": "2026-03-01T12:00:00Z",
            }
        },
    )

    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: Optional[EmailStr] = Field(None, description="Email address")
    full_name: Optional[str] = Field(None, description="Full name")
    is_active: bool = Field(default=True, description="Whether user is active")
    is_admin: bool = Field(default=False, description="Whether user is admin")
    scopes: List[str] = Field(default_factory=list, description="User scopes")
    created_at: Optional[datetime] = Field(None, description="Account creation time")
    last_login: Optional[datetime] = Field(None, description="Last login time")


class APIKeyCreate(BaseModel):
    """Request model for API key creation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Production API Key",
                "description": "API key for production frontend",
                "scopes": ["read"],
                "expires_days": 365,
            }
        }
    )

    name: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="API key name",
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="API key description",
    )
    scopes: List[str] = Field(
        default_factory=lambda: ["read"],
        description="Allowed scopes",
    )
    expires_days: Optional[int] = Field(
        None,
        gt=0,
        le=365,
        description="Expiration in days (None = never expires)",
    )


class APIKeyResponse(BaseModel):
    """Response model for API key creation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "key_123",
                "name": "Production API Key",
                "key": "marta_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "scopes": ["read"],
                "created_at": "2026-03-13T12:00:00Z",
                "expires_at": "2027-03-13T12:00:00Z",
            }
        }
    )

    id: str = Field(..., description="API key ID")
    name: str = Field(..., description="API key name")
    key: str = Field(
        ...,
        description="The API key (only shown once at creation)",
    )
    scopes: List[str] = Field(default_factory=list, description="Allowed scopes")
    created_at: datetime = Field(..., description="Creation time")
    expires_at: Optional[datetime] = Field(None, description="Expiration time")
