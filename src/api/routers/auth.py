# src/api/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Dict, Any, Optional
import logging

from src.api.auth import auth, get_current_user, require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# Request/Response models
class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    phone: Optional[str] = None

class SignInRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]

class UserResponse(BaseModel):
    id: str
    email: str
    user_metadata: Dict[str, Any]
    created_at: str

@router.post("/signup", response_model=AuthResponse)
async def sign_up(request: SignUpRequest):
    """
    Create new user account.
    """
    try:
        # Prepare user metadata
        user_metadata = {}
        if request.full_name:
            user_metadata["full_name"] = request.full_name
        if request.phone:
            user_metadata["phone"] = request.phone

        # Create user
        user = await auth.create_user(
            email=request.email,
            password=request.password,
            user_metadata=user_metadata
        )

        # Auto sign in after signup
        session = await auth.sign_in(request.email, request.password)

        logger.info(f"New user signed up: {request.email}")
        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create account"
        )

@router.post("/signin", response_model=AuthResponse)
async def sign_in(request: SignInRequest):
    """
    Sign in with email and password.
    """
    try:
        session = await auth.sign_in(request.email, request.password)
        logger.info(f"User signed in: {request.email}")
        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sign in error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

@router.post("/signout")
async def sign_out(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Sign out current user session.
    """
    try:
        # Note: Supabase sign out is typically handled client-side
        # This endpoint can be used for server-side session cleanup
        logger.info(f"User signed out: {user.get('email')}")
        return {"message": "Signed out successfully"}

    except Exception as e:
        logger.error(f"Sign out error: {e}")
        return {"message": "Sign out processed"}

@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token.
    """
    try:
        session = await auth.refresh_session(request.refresh_token)
        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get current user profile.
    """
    return {
        "id": user.get("id"),
        "email": user.get("email"),
        "user_metadata": user.get("user_metadata", {}),
        "created_at": user.get("created_at", "")
    }

@router.patch("/me")
async def update_user_profile(
    request: UpdateProfileRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update current user profile.
    """
    try:
        # Prepare metadata update
        metadata = user.get("user_metadata", {})

        if request.full_name is not None:
            metadata["full_name"] = request.full_name
        if request.phone is not None:
            metadata["phone"] = request.phone
        if request.preferences:
            metadata["preferences"] = request.preferences

        # Update user metadata
        success = await auth.update_user_metadata(user.get("id"), metadata)

        if success:
            logger.info(f"User profile updated: {user.get('email')}")
            return {
                "message": "Profile updated successfully",
                "user_metadata": metadata
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update profile"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )

@router.get("/users", response_model=list[UserResponse])
async def list_users(
    limit: int = 100,
    offset: int = 0,
    admin: Dict[str, Any] = Depends(require_admin)
):
    """
    List all users (admin only).
    """
    # This would require admin client and proper Supabase admin API calls
    # For now, return a placeholder
    logger.info(f"Admin {admin.get('email')} requested user list")

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User listing requires Supabase admin configuration"
    )

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin: Dict[str, Any] = Depends(require_admin)
):
    """
    Delete user account (admin only).
    """
    # This would require admin client
    logger.warning(f"Admin {admin.get('email')} attempted to delete user {user_id}")

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User deletion requires Supabase admin configuration"
    )

@router.post("/verify-token")
async def verify_token(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Verify if token is valid.
    """
    return {
        "valid": True,
        "user_id": user.get("id"),
        "email": user.get("email")
    }