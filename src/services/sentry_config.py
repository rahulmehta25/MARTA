# src/services/sentry_config.py

import os
import logging
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class SentryConfig:
    """
    Sentry monitoring configuration for MARTA Transit Analytics Platform.
    """

    def __init__(self):
        self.dsn = os.getenv("SENTRY_DSN")
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.release = os.getenv("APP_VERSION", "1.0.0")
        self.traces_sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
        self.profiles_sample_rate = float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1"))
        self.initialized = False

    def initialize(self, app_name: str = "marta-backend") -> bool:
        """
        Initialize Sentry monitoring.

        Args:
            app_name: Name of the application

        Returns:
            True if successfully initialized
        """
        if not self.dsn:
            logger.warning("Sentry DSN not configured - monitoring disabled")
            return False

        if self.initialized:
            logger.info("Sentry already initialized")
            return True

        try:
            # Configure logging integration
            logging_integration = LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR
            )

            # Initialize Sentry
            sentry_sdk.init(
                dsn=self.dsn,
                environment=self.environment,
                release=self.release,
                traces_sample_rate=self.traces_sample_rate,
                profiles_sample_rate=self.profiles_sample_rate,
                integrations=[
                    FastApiIntegration(transaction_style="endpoint"),
                    SqlalchemyIntegration(),
                    logging_integration,
                    RedisIntegration(),
                ],
                # Performance monitoring
                enable_tracing=True,

                # Session tracking
                release_health=True,

                # Error filtering
                before_send=self._before_send,
                before_send_transaction=self._before_send_transaction,

                # Additional options
                attach_stacktrace=True,
                send_default_pii=False,  # Don't send personally identifiable information
                max_breadcrumbs=50,
                debug=self.environment == "development",

                # Custom tags
                tags={
                    "app": app_name,
                    "service": "marta-transit",
                    "component": "backend"
                }
            )

            # Set user context if available
            self._set_user_context()

            # Set additional context
            sentry_sdk.set_context("app_info", {
                "name": app_name,
                "version": self.release,
                "environment": self.environment
            })

            self.initialized = True
            logger.info(f"Sentry initialized for {app_name} in {self.environment} environment")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}")
            return False

    def capture_exception(self, exception: Exception, context: Optional[Dict[str, Any]] = None):
        """
        Capture exception with optional context.

        Args:
            exception: The exception to capture
            context: Additional context to attach
        """
        if not self.initialized:
            return

        try:
            if context:
                with sentry_sdk.push_scope() as scope:
                    for key, value in context.items():
                        scope.set_context(key, value)
                    sentry_sdk.capture_exception(exception)
            else:
                sentry_sdk.capture_exception(exception)
        except Exception as e:
            logger.error(f"Failed to capture exception in Sentry: {e}")

    def capture_message(self, message: str, level: str = "info", context: Optional[Dict[str, Any]] = None):
        """
        Capture a message with optional context.

        Args:
            message: The message to capture
            level: Log level (debug, info, warning, error, fatal)
            context: Additional context to attach
        """
        if not self.initialized:
            return

        try:
            if context:
                with sentry_sdk.push_scope() as scope:
                    for key, value in context.items():
                        scope.set_context(key, value)
                    sentry_sdk.capture_message(message, level=level)
            else:
                sentry_sdk.capture_message(message, level=level)
        except Exception as e:
            logger.error(f"Failed to capture message in Sentry: {e}")

    def add_breadcrumb(self, message: str, category: str = "custom", level: str = "info", data: Optional[Dict] = None):
        """
        Add breadcrumb for tracking user actions.

        Args:
            message: Breadcrumb message
            category: Category of the breadcrumb
            level: Log level
            data: Additional data
        """
        if not self.initialized:
            return

        try:
            sentry_sdk.add_breadcrumb(
                message=message,
                category=category,
                level=level,
                data=data or {}
            )
        except Exception as e:
            logger.error(f"Failed to add breadcrumb: {e}")

    def set_user(self, user_id: str, email: Optional[str] = None, username: Optional[str] = None):
        """
        Set user context for error tracking.

        Args:
            user_id: Unique user identifier
            email: User email
            username: Username
        """
        if not self.initialized:
            return

        try:
            sentry_sdk.set_user({
                "id": user_id,
                "email": email,
                "username": username
            })
        except Exception as e:
            logger.error(f"Failed to set user context: {e}")

    def start_transaction(self, name: str, op: str = "function") -> Optional[Any]:
        """
        Start a performance transaction.

        Args:
            name: Transaction name
            op: Operation type

        Returns:
            Transaction object or None
        """
        if not self.initialized:
            return None

        try:
            return sentry_sdk.start_transaction(name=name, op=op)
        except Exception as e:
            logger.error(f"Failed to start transaction: {e}")
            return None

    def _before_send(self, event: Dict, hint: Dict) -> Optional[Dict]:
        """
        Filter or modify events before sending to Sentry.

        Args:
            event: The event to be sent
            hint: Additional information about the event

        Returns:
            Modified event or None to drop it
        """
        # Filter out certain errors
        if "exc_info" in hint:
            exc_type, exc_value, tb = hint["exc_info"]

            # Don't send certain expected errors
            if exc_type.__name__ in ["KeyboardInterrupt", "SystemExit"]:
                return None

            # Filter out 404 errors in production
            if self.environment == "production" and hasattr(exc_value, "status_code"):
                if exc_value.status_code == 404:
                    return None

        # Remove sensitive data
        if "request" in event:
            request = event["request"]
            # Remove authorization headers
            if "headers" in request:
                request["headers"] = {
                    k: v for k, v in request["headers"].items()
                    if k.lower() not in ["authorization", "cookie", "x-api-key"]
                }
            # Remove sensitive query parameters
            if "query_string" in request:
                # Parse and filter query string if needed
                pass

        return event

    def _before_send_transaction(self, event: Dict, hint: Dict) -> Optional[Dict]:
        """
        Filter or modify transaction events before sending to Sentry.

        Args:
            event: The transaction event
            hint: Additional information

        Returns:
            Modified event or None to drop it
        """
        # Filter out health check endpoints
        if "transaction" in event:
            transaction_name = event["transaction"]
            if transaction_name in ["/health", "/", "/metrics"]:
                return None

        return event

    def _set_user_context(self):
        """Set user context from environment or request."""
        # This would typically be set per request in middleware
        # Example implementation for default context
        user_id = os.getenv("DEFAULT_USER_ID")
        if user_id:
            self.set_user(user_id)

# Create singleton instance
sentry_config = SentryConfig()

# Middleware for FastAPI
class SentryMiddleware:
    """
    FastAPI middleware for Sentry integration.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract request information
        path = scope.get("path", "")
        method = scope.get("method", "")

        # Start transaction
        transaction = sentry_config.start_transaction(
            name=f"{method} {path}",
            op="http.server"
        )

        if transaction:
            with transaction:
                # Add request information
                transaction.set_tag("http.method", method)
                transaction.set_tag("http.url", path)

                # Process request
                try:
                    await self.app(scope, receive, send)
                except Exception as e:
                    transaction.set_status("internal_error")
                    sentry_config.capture_exception(e, context={
                        "request": {
                            "method": method,
                            "path": path
                        }
                    })
                    raise
                else:
                    transaction.set_status("ok")
        else:
            await self.app(scope, receive, send)

# Decorators for function monitoring
def monitor_performance(op: str = "function"):
    """
    Decorator to monitor function performance.

    Args:
        op: Operation type for Sentry
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            transaction = sentry_config.start_transaction(
                name=f"{func.__module__}.{func.__name__}",
                op=op
            )

            if transaction:
                with transaction:
                    try:
                        result = func(*args, **kwargs)
                        transaction.set_status("ok")
                        return result
                    except Exception as e:
                        transaction.set_status("internal_error")
                        sentry_config.capture_exception(e)
                        raise
            else:
                return func(*args, **kwargs)

        return wrapper
    return decorator

def capture_errors(func):
    """
    Decorator to capture function errors.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            sentry_config.capture_exception(e, context={
                "function": f"{func.__module__}.{func.__name__}",
                "args": str(args)[:500],  # Limit size
                "kwargs": str(kwargs)[:500]
            })
            raise

    return wrapper