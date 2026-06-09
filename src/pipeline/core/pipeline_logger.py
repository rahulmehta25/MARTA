#!/usr/bin/env python3
"""
Pipeline Logger - Comprehensive structured logging for all pipeline stages
Supports file, database, and structured JSON logging with context tracking
"""
import os
import sys
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum
import traceback
import threading
from contextlib import contextmanager
import psycopg2
from psycopg2 import pool
import uuid

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from config.settings import settings


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class PipelineStage(Enum):
    INIT = "initialization"
    DOWNLOAD = "download"
    PARSE = "parse"
    VALIDATE = "validate"
    TRANSFORM = "transform"
    LOAD = "load"
    ENRICH = "enrich"
    QUALITY_CHECK = "quality_check"
    ARCHIVE = "archive"
    CLEANUP = "cleanup"


@dataclass
class PipelineLogEntry:
    """Structured log entry for pipeline operations"""
    timestamp: datetime
    pipeline_name: str
    stage: str
    level: str
    message: str
    run_id: str
    duration_ms: Optional[float] = None
    records_processed: Optional[int] = None
    records_failed: Optional[int] = None
    error_type: Optional[str] = None
    error_traceback: Optional[str] = None
    metadata: Optional[Dict] = None
    source_file: Optional[str] = None
    source_line: Optional[int] = None

    def to_dict(self) -> Dict:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class PipelineLogger:
    """
    Comprehensive pipeline logging system with multiple output targets
    """

    _instances: Dict[str, 'PipelineLogger'] = {}
    _lock = threading.Lock()

    def __init__(
        self,
        pipeline_name: str,
        log_dir: str = "logs",
        db_logging: bool = True,
        console_logging: bool = True,
        file_logging: bool = True,
        json_logging: bool = True,
        db_pool: Optional[pool.ThreadedConnectionPool] = None
    ):
        self.pipeline_name = pipeline_name
        self.log_dir = log_dir
        self.db_logging = db_logging
        self.console_logging = console_logging
        self.file_logging = file_logging
        self.json_logging = json_logging

        # Create log directory
        os.makedirs(log_dir, exist_ok=True)

        # Run tracking
        self._current_run_id: Optional[str] = None
        self._stage_start_times: Dict[str, datetime] = {}

        # Database connection pool
        self.db_pool = db_pool

        # Setup Python logger
        self._setup_python_logger()

        # Initialize database logging table
        if self.db_logging:
            self._init_db_logging()

    @classmethod
    def get_logger(cls, pipeline_name: str, **kwargs) -> 'PipelineLogger':
        """Get or create a pipeline logger instance"""
        with cls._lock:
            if pipeline_name not in cls._instances:
                cls._instances[pipeline_name] = cls(pipeline_name, **kwargs)
            return cls._instances[pipeline_name]

    def _setup_python_logger(self):
        """Configure Python logging handlers"""
        self.logger = logging.getLogger(f"pipeline.{self.pipeline_name}")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []  # Clear existing handlers

        # Console handler
        if self.console_logging:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_format = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
            )
            console_handler.setFormatter(console_format)
            self.logger.addHandler(console_handler)

        # File handler (human-readable)
        if self.file_logging:
            log_file = os.path.join(
                self.log_dir,
                f"{self.pipeline_name}_{datetime.now().strftime('%Y%m%d')}.log"
            )
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_format = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | [%(run_id)s] | %(stage)s | %(message)s'
            )
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)

        # JSON file handler (structured)
        if self.json_logging:
            json_file = os.path.join(
                self.log_dir,
                f"{self.pipeline_name}_{datetime.now().strftime('%Y%m%d')}.jsonl"
            )
            self.json_file_path = json_file

    def _init_db_logging(self):
        """Initialize database logging tables"""
        if not self.db_pool:
            try:
                self.db_pool = pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=5,
                    host=settings.DB_HOST,
                    database=settings.DB_NAME,
                    user=settings.DB_USER,
                    password=settings.DB_PASSWORD,
                    port=settings.DB_PORT
                )
            except Exception as e:
                self.logger.warning(f"Failed to create DB pool for logging: {e}")
                self.db_logging = False
                return

        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS pipeline_logs (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP NOT NULL,
                        pipeline_name VARCHAR(255) NOT NULL,
                        stage VARCHAR(100),
                        level VARCHAR(20) NOT NULL,
                        message TEXT,
                        run_id VARCHAR(64),
                        duration_ms NUMERIC,
                        records_processed INTEGER,
                        records_failed INTEGER,
                        error_type VARCHAR(255),
                        error_traceback TEXT,
                        metadata JSONB,
                        source_file VARCHAR(255),
                        source_line INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE INDEX IF NOT EXISTS idx_pipeline_logs_timestamp
                        ON pipeline_logs(timestamp);
                    CREATE INDEX IF NOT EXISTS idx_pipeline_logs_pipeline
                        ON pipeline_logs(pipeline_name);
                    CREATE INDEX IF NOT EXISTS idx_pipeline_logs_run
                        ON pipeline_logs(run_id);
                    CREATE INDEX IF NOT EXISTS idx_pipeline_logs_level
                        ON pipeline_logs(level);
                    CREATE INDEX IF NOT EXISTS idx_pipeline_logs_stage
                        ON pipeline_logs(stage);

                    -- Pipeline run tracking
                    CREATE TABLE IF NOT EXISTS pipeline_runs (
                        run_id VARCHAR(64) PRIMARY KEY,
                        pipeline_name VARCHAR(255) NOT NULL,
                        status VARCHAR(50) NOT NULL DEFAULT 'running',
                        started_at TIMESTAMP NOT NULL,
                        completed_at TIMESTAMP,
                        total_records_processed INTEGER DEFAULT 0,
                        total_records_failed INTEGER DEFAULT 0,
                        error_count INTEGER DEFAULT 0,
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE INDEX IF NOT EXISTS idx_pipeline_runs_pipeline
                        ON pipeline_runs(pipeline_name);
                    CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status
                        ON pipeline_runs(status);
                """)
                conn.commit()
        finally:
            self.db_pool.putconn(conn)

    def start_run(self, metadata: Optional[Dict] = None) -> str:
        """Start a new pipeline run and return run ID"""
        self._current_run_id = str(uuid.uuid4())[:16]
        self._stage_start_times = {}

        if self.db_logging and self.db_pool:
            conn = self.db_pool.getconn()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO pipeline_runs
                        (run_id, pipeline_name, status, started_at, metadata)
                        VALUES (%s, %s, 'running', %s, %s)
                    """, (self._current_run_id, self.pipeline_name,
                          datetime.now(), json.dumps(metadata or {})))
                    conn.commit()
            finally:
                self.db_pool.putconn(conn)

        self.info(
            "Pipeline run started",
            stage=PipelineStage.INIT.value,
            metadata=metadata
        )

        return self._current_run_id

    def end_run(self, success: bool = True, metadata: Optional[Dict] = None):
        """End the current pipeline run"""
        status = "success" if success else "failed"

        self.info(
            f"Pipeline run completed with status: {status}",
            stage=PipelineStage.CLEANUP.value,
            metadata=metadata
        )

        if self.db_logging and self.db_pool and self._current_run_id:
            conn = self.db_pool.getconn()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE pipeline_runs
                        SET status = %s,
                            completed_at = %s,
                            metadata = COALESCE(metadata, '{}'::jsonb) || %s::jsonb
                        WHERE run_id = %s
                    """, (status, datetime.now(),
                          json.dumps(metadata or {}), self._current_run_id))
                    conn.commit()
            finally:
                self.db_pool.putconn(conn)

        self._current_run_id = None

    @contextmanager
    def stage(self, stage: PipelineStage, metadata: Optional[Dict] = None):
        """Context manager for pipeline stage tracking"""
        stage_name = stage.value if isinstance(stage, PipelineStage) else stage
        start_time = datetime.now()
        self._stage_start_times[stage_name] = start_time

        self.info(f"Stage '{stage_name}' started", stage=stage_name, metadata=metadata)

        try:
            yield
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            self.info(
                f"Stage '{stage_name}' completed",
                stage=stage_name,
                duration_ms=duration_ms,
                metadata=metadata
            )
        except Exception as e:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            self.error(
                f"Stage '{stage_name}' failed: {str(e)}",
                stage=stage_name,
                duration_ms=duration_ms,
                error=e,
                metadata=metadata
            )
            raise

    def _log(
        self,
        level: LogLevel,
        message: str,
        stage: Optional[str] = None,
        duration_ms: Optional[float] = None,
        records_processed: Optional[int] = None,
        records_failed: Optional[int] = None,
        error: Optional[Exception] = None,
        metadata: Optional[Dict] = None
    ):
        """Internal logging method"""
        # Get caller info
        frame = sys._getframe(2)
        source_file = os.path.basename(frame.f_code.co_filename)
        source_line = frame.f_lineno

        entry = PipelineLogEntry(
            timestamp=datetime.now(),
            pipeline_name=self.pipeline_name,
            stage=stage or "general",
            level=level.value,
            message=message,
            run_id=self._current_run_id or "no-run",
            duration_ms=duration_ms,
            records_processed=records_processed,
            records_failed=records_failed,
            error_type=type(error).__name__ if error else None,
            error_traceback=traceback.format_exc() if error else None,
            metadata=metadata,
            source_file=source_file,
            source_line=source_line
        )

        # Log to Python logger
        extra = {
            'run_id': entry.run_id,
            'stage': entry.stage
        }
        log_method = getattr(self.logger, level.value.lower())
        log_method(message, extra=extra)

        # Log to JSON file
        if self.json_logging:
            try:
                with open(self.json_file_path, 'a') as f:
                    f.write(entry.to_json() + '\n')
            except Exception as e:
                self.logger.warning(f"Failed to write JSON log: {e}")

        # Log to database
        if self.db_logging and self.db_pool:
            self._log_to_db(entry)

    def _log_to_db(self, entry: PipelineLogEntry):
        """Write log entry to database"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO pipeline_logs
                    (timestamp, pipeline_name, stage, level, message, run_id,
                     duration_ms, records_processed, records_failed,
                     error_type, error_traceback, metadata, source_file, source_line)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    entry.timestamp,
                    entry.pipeline_name,
                    entry.stage,
                    entry.level,
                    entry.message,
                    entry.run_id,
                    entry.duration_ms,
                    entry.records_processed,
                    entry.records_failed,
                    entry.error_type,
                    entry.error_traceback,
                    json.dumps(entry.metadata) if entry.metadata else None,
                    entry.source_file,
                    entry.source_line
                ))
                conn.commit()
        except Exception as e:
            self.logger.warning(f"Failed to write DB log: {e}")
            conn.rollback()
        finally:
            self.db_pool.putconn(conn)

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message"""
        self._log(LogLevel.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self._log(LogLevel.CRITICAL, message, **kwargs)

    def log_records(
        self,
        stage: str,
        records_processed: int,
        records_failed: int = 0,
        duration_ms: Optional[float] = None,
        metadata: Optional[Dict] = None
    ):
        """Log record processing statistics"""
        self.info(
            f"Processed {records_processed} records ({records_failed} failed)",
            stage=stage,
            records_processed=records_processed,
            records_failed=records_failed,
            duration_ms=duration_ms,
            metadata=metadata
        )

    def get_run_logs(self, run_id: str) -> List[Dict]:
        """Retrieve all logs for a specific run"""
        if not self.db_pool:
            return []

        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT timestamp, stage, level, message, duration_ms,
                           records_processed, records_failed, error_type, metadata
                    FROM pipeline_logs
                    WHERE run_id = %s
                    ORDER BY timestamp
                """, (run_id,))

                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            self.db_pool.putconn(conn)

    def get_recent_errors(self, hours: int = 24) -> List[Dict]:
        """Retrieve recent error logs"""
        if not self.db_pool:
            return []

        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT timestamp, pipeline_name, stage, message,
                           error_type, error_traceback, run_id
                    FROM pipeline_logs
                    WHERE level IN ('ERROR', 'CRITICAL')
                      AND timestamp >= NOW() - INTERVAL '%s hours'
                    ORDER BY timestamp DESC
                    LIMIT 100
                """, (hours,))

                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            self.db_pool.putconn(conn)


# Convenience function for getting pipeline logger
def get_pipeline_logger(pipeline_name: str, **kwargs) -> PipelineLogger:
    """Get or create a pipeline logger"""
    return PipelineLogger.get_logger(pipeline_name, **kwargs)
