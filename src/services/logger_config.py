# src/services/logger_config.py

import os
import sys
import logging
import logging.handlers
from datetime import datetime
from typing import Optional, Dict, Any
import json
import traceback
from pathlib import Path

class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
            "process_id": record.process,
            "thread_id": record.thread,
        }

        # Add extra fields if present
        if hasattr(record, "user_id"):
            log_obj["user_id"] = record.user_id
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        if hasattr(record, "service"):
            log_obj["service"] = record.service
        if hasattr(record, "metric"):
            log_obj["metric"] = record.metric

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }

        return json.dumps(log_obj)


class LoggerConfig:
    """
    Centralized logging configuration for the MARTA Transit Analytics Platform.
    """

    def __init__(self,
                 service_name: str = "marta-analytics",
                 log_level: str = None,
                 log_dir: str = None):
        self.service_name = service_name
        self.log_level = log_level or os.getenv("LOG_LEVEL", "INFO")
        self.log_dir = log_dir or os.getenv("LOG_DIR", "logs")

        # Create log directory if it doesn't exist
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)

        # Configure root logger
        self._configure_root_logger()

    def _configure_root_logger(self):
        """Configure the root logger with appropriate handlers."""
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.log_level))

        # Remove existing handlers
        root_logger.handlers = []

        # Console handler with colored output
        console_handler = self._get_console_handler()
        root_logger.addHandler(console_handler)

        # File handler for all logs
        file_handler = self._get_file_handler("app.log")
        root_logger.addHandler(file_handler)

        # Error file handler
        error_handler = self._get_error_handler("errors.log")
        root_logger.addHandler(error_handler)

        # Structured JSON handler for production
        if os.getenv("ENVIRONMENT") == "production":
            json_handler = self._get_json_handler("structured.log")
            root_logger.addHandler(json_handler)

    def _get_console_handler(self) -> logging.StreamHandler:
        """Create console handler with colored output."""
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)

        # Use colored formatter for development
        if os.getenv("ENVIRONMENT") != "production":
            formatter = ColoredFormatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

        handler.setFormatter(formatter)
        return handler

    def _get_file_handler(self, filename: str) -> logging.handlers.RotatingFileHandler:
        """Create rotating file handler."""
        handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(self.log_dir, filename),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        )
        handler.setFormatter(formatter)
        return handler

    def _get_error_handler(self, filename: str) -> logging.handlers.RotatingFileHandler:
        """Create error file handler."""
        handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(self.log_dir, filename),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        handler.setLevel(logging.ERROR)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s\n%(exc_info)s"
        )
        handler.setFormatter(formatter)
        return handler

    def _get_json_handler(self, filename: str) -> logging.handlers.RotatingFileHandler:
        """Create JSON structured log handler."""
        handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(self.log_dir, filename),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        handler.setLevel(logging.INFO)
        handler.setFormatter(StructuredFormatter())
        return handler

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger instance with the given name.

        Args:
            name: Logger name (usually __name__)

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(name)

        # Add service context
        logger = logging.LoggerAdapter(logger, {"service": self.service_name})

        return logger


class ColoredFormatter(logging.Formatter):
    """
    Formatter that adds colors to console output.
    """

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        """Add color to log level."""
        levelname = record.levelname
        if levelname in self.COLORS:
            levelname_color = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
            record.levelname = levelname_color
        return super().format(record)


class LogContext:
    """
    Context manager for adding context to logs.
    """

    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context

    def __enter__(self):
        """Add context to logger."""
        for key, value in self.context.items():
            if hasattr(self.logger, 'extra'):
                self.logger.extra[key] = value
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Remove context from logger."""
        for key in self.context.keys():
            if hasattr(self.logger, 'extra') and key in self.logger.extra:
                del self.logger.extra[key]


class MetricsLogger:
    """
    Specialized logger for metrics and performance data.
    """

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def log_metric(self,
                   metric_name: str,
                   value: float,
                   unit: str = None,
                   tags: Dict[str, Any] = None):
        """Log a metric value."""
        metric_data = {
            "metric_name": metric_name,
            "value": value,
            "unit": unit,
            "tags": tags or {},
            "timestamp": datetime.utcnow().isoformat()
        }

        self.logger.info(f"METRIC: {metric_name}", extra={"metric": metric_data})

    def log_duration(self, operation: str, duration_ms: float, success: bool = True):
        """Log operation duration."""
        self.log_metric(
            f"operation.duration.{operation}",
            duration_ms,
            unit="milliseconds",
            tags={"success": success}
        )

    def log_count(self, event: str, count: int = 1, tags: Dict[str, Any] = None):
        """Log event count."""
        self.log_metric(
            f"event.count.{event}",
            count,
            unit="count",
            tags=tags
        )

    def log_gauge(self, metric: str, value: float, unit: str = None):
        """Log a gauge metric."""
        self.log_metric(
            f"gauge.{metric}",
            value,
            unit=unit
        )


# Application-wide logger configuration
def setup_logging(service_name: str = "marta-analytics"):
    """
    Set up logging for the entire application.

    Args:
        service_name: Name of the service for log identification
    """
    config = LoggerConfig(service_name=service_name)

    # Configure specific loggers
    loggers_config = {
        "src": logging.INFO,
        "src.ml": logging.DEBUG,
        "src.api": logging.INFO,
        "src.database": logging.WARNING,
        "src.services": logging.INFO,
        "urllib3": logging.WARNING,
        "requests": logging.WARNING,
    }

    for logger_name, level in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)

    return config


# Decorators for logging
def log_execution(logger: logging.Logger = None):
    """
    Decorator to log function execution.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = logging.getLogger(func.__module__)

            logger.debug(f"Executing {func.__name__}")
            start_time = datetime.now()

            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds() * 1000
                logger.debug(f"Completed {func.__name__} in {duration:.2f}ms")
                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds() * 1000
                logger.error(f"Error in {func.__name__} after {duration:.2f}ms: {str(e)}")
                raise

        return wrapper
    return decorator


def log_api_call(logger: logging.Logger = None):
    """
    Decorator to log API calls.
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = logging.getLogger(func.__module__)

            # Extract request info if available
            request = kwargs.get('request')
            request_id = getattr(request, 'request_id', None) if request else None

            logger.info(f"API call: {func.__name__}", extra={"request_id": request_id})
            start_time = datetime.now()

            try:
                result = await func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds() * 1000
                logger.info(
                    f"API call completed: {func.__name__} in {duration:.2f}ms",
                    extra={"request_id": request_id, "duration_ms": duration}
                )
                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds() * 1000
                logger.error(
                    f"API call failed: {func.__name__} after {duration:.2f}ms: {str(e)}",
                    extra={"request_id": request_id, "duration_ms": duration}
                )
                raise

        return wrapper
    return decorator


# Initialize logging when module is imported
if __name__ == "__main__":
    # Example usage
    setup_logging()
    logger = logging.getLogger(__name__)
    metrics = MetricsLogger(logger)

    logger.info("Logging system initialized")
    metrics.log_metric("system.startup", 1, tags={"version": "1.0.0"})

    # Test different log levels
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    # Test structured logging
    with LogContext(logger, user_id="user123", request_id="req456"):
        logger.info("Processing user request")

    # Test metrics
    metrics.log_duration("database.query", 45.2)
    metrics.log_count("api.request", tags={"endpoint": "/api/v1/routes"})
    metrics.log_gauge("memory.usage", 75.5, unit="percent")