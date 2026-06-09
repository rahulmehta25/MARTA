"""Core module for MARTA API."""
from .config import settings, get_settings
from .logging import get_logger, setup_logging, RequestIdMiddleware
from .cache import cache, cached
from .security import (
    create_access_token,
    verify_token,
    get_password_hash,
    verify_password,
    get_current_user,
    get_api_key,
    require_auth,
)

__all__ = [
    "settings",
    "get_settings",
    "get_logger",
    "setup_logging",
    "RequestIdMiddleware",
    "cache",
    "cached",
    "create_access_token",
    "verify_token",
    "get_password_hash",
    "verify_password",
    "get_current_user",
    "get_api_key",
    "require_auth",
]
