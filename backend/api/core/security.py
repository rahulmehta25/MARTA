"""
Security utilities: JWT authentication and API key support.
"""
from datetime import datetime, timedelta
from typing import Optional, Union

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from .config import settings
from .logging import get_logger

logger = get_logger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name=settings.api_key_header, auto_error=False)


class TokenData(BaseModel):
    """JWT token payload data."""
    sub: str
    exp: datetime
    type: str = "access"
    scopes: list[str] = []


class User(BaseModel):
    """User model for authentication."""
    id: str
    username: str
    email: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False
    scopes: list[str] = []


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    token_type: str = "access",
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)

    to_encode.update({
        "exp": expire,
        "type": token_type,
        "iat": datetime.utcnow(),
    })

    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    expires_delta = timedelta(days=settings.jwt_refresh_expiration_days)
    return create_access_token(data, expires_delta, token_type="refresh")


def verify_token(token: str, token_type: str = "access") -> TokenData:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        if payload.get("type") != token_type:
            raise JWTError("Invalid token type")

        return TokenData(
            sub=payload.get("sub"),
            exp=datetime.fromtimestamp(payload.get("exp")),
            type=payload.get("type", "access"),
            scopes=payload.get("scopes", []),
        )
    except JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> Optional[User]:
    """
    Get current user from JWT token.
    Returns None if no token provided (allows optional auth).
    """
    if not credentials:
        return None

    token_data = verify_token(credentials.credentials)

    # In production, fetch user from database
    # For now, return a basic user object
    return User(
        id=token_data.sub,
        username=token_data.sub,
        scopes=token_data.scopes,
    )


async def get_api_key(
    api_key: Optional[str] = Security(api_key_header),
) -> Optional[str]:
    """
    Validate API key from header.
    Returns the API key if valid, None otherwise.
    """
    if not api_key:
        return None

    if api_key in settings.allowed_api_keys_list:
        logger.debug("API key authenticated", key_prefix=api_key[:8] if len(api_key) > 8 else "***")
        return api_key

    logger.warning("Invalid API key attempt", key_prefix=api_key[:8] if len(api_key) > 8 else "***")
    return None


async def require_auth(
    user: Optional[User] = Depends(get_current_user),
    api_key: Optional[str] = Depends(get_api_key),
) -> Union[User, str]:
    """
    Require either JWT token or API key authentication.
    Raises 401 if neither is provided/valid.
    """
    if user:
        return user
    if api_key:
        return api_key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide Bearer token or API key.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_scope(required_scope: str):
    """
    Dependency to require a specific scope.

    Example:
        @router.get("/admin")
        async def admin_endpoint(user: User = Depends(require_scope("admin"))):
            ...
    """
    async def scope_checker(
        user: Optional[User] = Depends(get_current_user),
    ) -> User:
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        if required_scope not in user.scopes and not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Scope '{required_scope}' required",
            )

        return user

    return scope_checker
