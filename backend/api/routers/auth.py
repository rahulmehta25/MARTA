"""
Authentication API endpoints.
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from backend.api.core.config import settings
from backend.api.core.logging import get_logger
from backend.api.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    verify_password,
    get_password_hash,
    get_current_user,
    User,
)
from backend.api.models.auth import (
    TokenRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserCreate,
    UserResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Demo users (in production, use database)
DEMO_USERS = {
    "admin": {
        "id": "user_001",
        "username": "admin",
        "email": "admin@marta.com",
        "password_hash": get_password_hash("admin123"),
        "is_active": True,
        "is_admin": True,
        "scopes": ["read", "write", "admin"],
    },
    "api_user": {
        "id": "user_002",
        "username": "api_user",
        "email": "api@marta.com",
        "password_hash": get_password_hash("apiuser123"),
        "is_active": True,
        "is_admin": False,
        "scopes": ["read", "write"],
    },
    "readonly": {
        "id": "user_003",
        "username": "readonly",
        "email": "readonly@marta.com",
        "password_hash": get_password_hash("readonly123"),
        "is_active": True,
        "is_admin": False,
        "scopes": ["read"],
    },
}


def get_user_by_username(username: str) -> Optional[dict]:
    """Get user by username (demo implementation)."""
    return DEMO_USERS.get(username)


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Authenticate user with username and password."""
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Get access token",
    description="""
    Authenticate and get JWT access token.

    Provide username and password to receive:
    - Access token (expires in 24 hours by default)
    - Refresh token (expires in 7 days by default)

    Use the access token in the Authorization header:
    `Authorization: Bearer <token>`
    """,
    responses={
        200: {"description": "Authentication successful"},
        401: {"description": "Invalid credentials"},
    },
)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Get access token using username and password."""
    logger.info("Login attempt", username=form_data.username)

    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        logger.warning("Failed login attempt", username=form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )

    # Create tokens
    access_token = create_access_token(
        data={"sub": user["username"], "scopes": user["scopes"]},
    )
    refresh_token = create_refresh_token(
        data={"sub": user["username"]},
    )

    logger.info("Login successful", username=user["username"])

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_expiration_hours * 3600,
        scopes=user["scopes"],
    )


@router.post(
    "/token/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Use refresh token to get a new access token.",
    responses={
        200: {"description": "Token refreshed successfully"},
        401: {"description": "Invalid or expired refresh token"},
    },
)
async def refresh_token(request: RefreshTokenRequest):
    """Refresh access token using refresh token."""
    logger.info("Token refresh attempt")

    try:
        token_data = verify_token(request.refresh_token, token_type="refresh")
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = get_user_by_username(token_data.sub)
    if not user or not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled",
        )

    # Create new access token
    access_token = create_access_token(
        data={"sub": user["username"], "scopes": user["scopes"]},
    )

    logger.info("Token refreshed", username=user["username"])

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_expiration_hours * 3600,
        scopes=user["scopes"],
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get information about the currently authenticated user.",
    responses={
        200: {"description": "User information retrieved"},
        401: {"description": "Not authenticated"},
    },
)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Get current user information."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    user_data = get_user_by_username(current_user.username)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse(
        id=user_data["id"],
        username=user_data["username"],
        email=user_data["email"],
        is_active=user_data["is_active"],
        is_admin=user_data["is_admin"],
        scopes=user_data["scopes"],
    )


@router.post(
    "/verify",
    summary="Verify token",
    description="Verify if a token is valid.",
    responses={
        200: {"description": "Token is valid"},
        401: {"description": "Token is invalid"},
    },
)
async def verify_token_endpoint(
    current_user: User = Depends(get_current_user),
):
    """Verify if the provided token is valid."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return {
        "valid": True,
        "username": current_user.username,
        "scopes": current_user.scopes,
    }
