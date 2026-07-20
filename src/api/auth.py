# src/api/auth.py

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
import jwt
from jwt import PyJWTError

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

class SupabaseAuth:
    """
    Supabase authentication handler for the MARTA Transit Analytics Platform.
    """

    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL", "")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "")
        self.supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self.jwt_secret = os.getenv("JWT_SECRET", os.getenv("SUPABASE_JWT_SECRET", ""))

        if not self.supabase_url or not self.supabase_anon_key:
            logger.warning("Supabase credentials not configured - auth disabled")
            self.client = None
            self.admin_client = None
        else:
            # Public client (uses anon key)
            self.client = create_client(self.supabase_url, self.supabase_anon_key)

            # Admin client (uses service role key) - optional
            if self.supabase_service_key:
                self.admin_client = create_client(self.supabase_url, self.supabase_service_key)
            else:
                self.admin_client = None

    async def verify_token(self, credentials: HTTPAuthorizationCredentials) -> Dict[str, Any]:
        """
        Verify JWT token from Supabase Auth.

        Args:
            credentials: Bearer token from request header

        Returns:
            Decoded JWT payload with user information

        Raises:
            HTTPException: If token is invalid or expired
        """
        if not self.client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service not available"
            )

        token = credentials.credentials

        try:
            # Decode and verify JWT
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=["HS256"],
                audience="authenticated"
            )

            # Check expiration
            exp = payload.get("exp", 0)
            if datetime.fromtimestamp(exp) < datetime.now():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expired"
                )

            return payload

        except PyJWTError as e:
            logger.error(f"JWT verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )

    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
        """
        Get current authenticated user from token.

        Args:
            credentials: Bearer token from request header

        Returns:
            User information from JWT payload
        """
        payload = await self.verify_token(credentials)

        user_data = {
            "id": payload.get("sub"),
            "email": payload.get("email"),
            "role": payload.get("role", "user"),
            "user_metadata": payload.get("user_metadata", {}),
            "app_metadata": payload.get("app_metadata", {})
        }

        return user_data

    async def require_role(self, required_role: str):
        """
        Dependency to require specific user role.

        Args:
            required_role: Role required to access endpoint

        Returns:
            Dependency function that validates user role
        """
        async def role_checker(user: Dict[str, Any] = Depends(self.get_current_user)):
            user_role = user.get("role", "user")
            app_roles = user.get("app_metadata", {}).get("roles", [])

            # Check if user has required role
            if user_role != required_role and required_role not in app_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required role: {required_role}"
                )

            return user

        return role_checker

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user information by ID using admin client.

        Args:
            user_id: Supabase user ID

        Returns:
            User data or None if not found
        """
        if not self.admin_client:
            logger.warning("Admin client not available - cannot fetch user data")
            return None

        try:
            response = self.admin_client.auth.admin.get_user_by_id(user_id)
            return response.user if response else None
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            return None

    async def create_user(self, email: str, password: str, user_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create new user account.

        Args:
            email: User email
            password: User password
            user_metadata: Additional user metadata

        Returns:
            Created user data

        Raises:
            HTTPException: If user creation fails
        """
        if not self.client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service not available"
            )

        try:
            response = self.client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": user_metadata or {}
                }
            })

            if response.user:
                return {
                    "id": response.user.id,
                    "email": response.user.email,
                    "created_at": response.user.created_at,
                    "user_metadata": response.user.user_metadata
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User creation failed"
                )

        except Exception as e:
            logger.error(f"User creation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    async def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """
        Sign in user and return session.

        Args:
            email: User email
            password: User password

        Returns:
            Session data with access token

        Raises:
            HTTPException: If sign in fails
        """
        if not self.client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service not available"
            )

        try:
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if response.session:
                return {
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token,
                    "expires_in": response.session.expires_in,
                    "token_type": "bearer",
                    "user": {
                        "id": response.user.id,
                        "email": response.user.email,
                        "user_metadata": response.user.user_metadata
                    }
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )

        except Exception as e:
            logger.error(f"Sign in error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )

    async def sign_out(self, access_token: str) -> bool:
        """
        Sign out user session.

        Args:
            access_token: User's access token

        Returns:
            True if successful
        """
        if not self.client:
            return False

        try:
            self.client.auth.sign_out(access_token)
            return True
        except Exception as e:
            logger.error(f"Sign out error: {e}")
            return False

    async def refresh_session(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh user session with refresh token.

        Args:
            refresh_token: Refresh token

        Returns:
            New session data

        Raises:
            HTTPException: If refresh fails
        """
        if not self.client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service not available"
            )

        try:
            response = self.client.auth.refresh_session(refresh_token)

            if response.session:
                return {
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token,
                    "expires_in": response.session.expires_in,
                    "token_type": "bearer"
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session refresh failed"
                )

        except Exception as e:
            logger.error(f"Session refresh error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

    async def update_user_metadata(self, user_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Update user metadata (requires admin client).

        Args:
            user_id: User ID
            metadata: Metadata to update

        Returns:
            True if successful
        """
        if not self.admin_client:
            logger.warning("Admin client not available - cannot update user metadata")
            return False

        try:
            response = self.admin_client.auth.admin.update_user_by_id(
                user_id,
                {"user_metadata": metadata}
            )
            return response is not None
        except Exception as e:
            logger.error(f"Error updating user metadata: {e}")
            return False

# Create singleton instance
auth = SupabaseAuth()

# Dependency functions
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current authenticated user."""
    return await auth.get_current_user(credentials)

async def require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Require admin role."""
    if user.get("role") != "admin" and "admin" not in user.get("app_metadata", {}).get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user

async def require_authenticated(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Require any authenticated user."""
    if not user.get("id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user

# Optional dependency - returns user if authenticated, None otherwise
async def get_optional_user(request: Request) -> Optional[Dict[str, Any]]:
    """Get user if authenticated, otherwise return None."""
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        return None

    try:
        token = authorization.replace("Bearer ", "")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        return await auth.get_current_user(credentials)
    except:
        return None