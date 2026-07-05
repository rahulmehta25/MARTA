"""
Structured logging with request ID tracking for MARTA API.
"""
import logging
import sys
import uuid
import json
from datetime import datetime
from typing import Optional, Any
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable for request ID
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware to inject request ID into every request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request_id_var.set(request_id)
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request ID if available
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        return json.dumps(log_data)


class StandardFormatter(logging.Formatter):
    """Standard text formatter with request ID."""

    def format(self, record: logging.LogRecord) -> str:
        request_id = request_id_var.get()
        rid_str = f"[{request_id[:8]}]" if request_id else "[-]"
        record.request_id = rid_str
        return super().format(record)


class ContextLogger(logging.Logger):
    """Custom logger that automatically includes context."""

    def _log(
        self,
        level: int,
        msg: object,
        args: tuple,
        exc_info: Any = None,
        extra: Optional[dict] = None,
        stack_info: bool = False,
        **kwargs,
    ) -> None:
        extra = extra or {}
        extra["extra_data"] = kwargs
        super()._log(level, msg, args, exc_info=exc_info, extra=extra, stack_info=stack_info)


# Set logger class early so all loggers created via get_logger() support kwargs
logging.setLoggerClass(ContextLogger)


def setup_logging(
    level: str = "INFO",
    log_format: str = "json",
    log_file: Optional[str] = None,
) -> None:
    """Setup logging configuration."""
    logging.setLoggerClass(ContextLogger)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatter
    if log_format.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = StandardFormatter(
            fmt="%(asctime)s %(levelname)-8s %(request_id)s %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with context support."""
    return logging.getLogger(name)
