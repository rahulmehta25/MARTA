#!/usr/bin/env python3
"""
Pipeline Orchestrator - Main scheduling and orchestration for MARTA data pipelines
Handles scheduled GTFS static/realtime ingestion, weather, events, and data quality checks
"""
import os
import sys
import logging
import threading
import time
import signal
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import schedule
import psycopg2
from psycopg2 import pool

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from config.settings import settings

logger = logging.getLogger(__name__)


class PipelineStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SCHEDULED = "scheduled"


@dataclass
class PipelineJob:
    """Represents a scheduled pipeline job"""
    name: str
    func: Callable
    schedule_type: str  # 'interval', 'daily', 'hourly', 'cron'
    schedule_value: Any  # seconds for interval, time for daily, etc.
    enabled: bool = True
    last_run: Optional[datetime] = None
    last_status: PipelineStatus = PipelineStatus.IDLE
    last_duration_seconds: float = 0
    run_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


class PipelineOrchestrator:
    """
    Central orchestrator for all MARTA data pipeline jobs
    Manages scheduling, execution, monitoring, and error handling
    """

    def __init__(self, db_pool: Optional[pool.ThreadedConnectionPool] = None):
        self.jobs: Dict[str, PipelineJob] = {}
        self.is_running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

        # Database connection pool
        self.db_pool = db_pool or self._create_db_pool()

        # Pipeline state
        self.start_time: Optional[datetime] = None
        self.total_runs = 0
        self.total_errors = 0

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Create pipeline status table
        self._init_status_table()

        logger.info("PipelineOrchestrator initialized")

    def _create_db_pool(self) -> pool.ThreadedConnectionPool:
        """Create database connection pool"""
        return pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            host=settings.DB_HOST,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            port=settings.DB_PORT
        )

    def _init_status_table(self):
        """Initialize pipeline status tracking table"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS pipeline_job_status (
                        id SERIAL PRIMARY KEY,
                        job_name VARCHAR(255) NOT NULL,
                        status VARCHAR(50) NOT NULL,
                        started_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        duration_seconds NUMERIC,
                        records_processed INTEGER DEFAULT 0,
                        error_message TEXT,
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE INDEX IF NOT EXISTS idx_pipeline_job_status_name
                        ON pipeline_job_status(job_name);
                    CREATE INDEX IF NOT EXISTS idx_pipeline_job_status_started
                        ON pipeline_job_status(started_at);
                    CREATE INDEX IF NOT EXISTS idx_pipeline_job_status_status
                        ON pipeline_job_status(status);

                    -- Pipeline run summary table
                    CREATE TABLE IF NOT EXISTS pipeline_run_summary (
                        id SERIAL PRIMARY KEY,
                        job_name VARCHAR(255) NOT NULL,
                        date DATE NOT NULL,
                        total_runs INTEGER DEFAULT 0,
                        successful_runs INTEGER DEFAULT 0,
                        failed_runs INTEGER DEFAULT 0,
                        total_records_processed BIGINT DEFAULT 0,
                        avg_duration_seconds NUMERIC,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(job_name, date)
                    );
                """)
                conn.commit()
        finally:
            self.db_pool.putconn(conn)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.stop()

    def register_job(
        self,
        name: str,
        func: Callable,
        schedule_type: str,
        schedule_value: Any,
        enabled: bool = True,
        metadata: Optional[Dict] = None
    ):
        """Register a new pipeline job"""
        with self._lock:
            job = PipelineJob(
                name=name,
                func=func,
                schedule_type=schedule_type,
                schedule_value=schedule_value,
                enabled=enabled,
                metadata=metadata or {}
            )
            self.jobs[name] = job

            # Schedule the job
            if enabled:
                self._schedule_job(job)

            logger.info(f"Registered job: {name} ({schedule_type}: {schedule_value})")

    def _schedule_job(self, job: PipelineJob):
        """Schedule a job based on its configuration"""
        wrapper = self._create_job_wrapper(job)

        if job.schedule_type == 'interval':
            schedule.every(job.schedule_value).seconds.do(wrapper).tag(job.name)
        elif job.schedule_type == 'minutes':
            schedule.every(job.schedule_value).minutes.do(wrapper).tag(job.name)
        elif job.schedule_type == 'hourly':
            schedule.every().hour.at(f":{job.schedule_value:02d}").do(wrapper).tag(job.name)
        elif job.schedule_type == 'daily':
            schedule.every().day.at(job.schedule_value).do(wrapper).tag(job.name)
        elif job.schedule_type == 'weekly':
            day, time_str = job.schedule_value.split('@')
            getattr(schedule.every(), day.lower()).at(time_str).do(wrapper).tag(job.name)

    def _create_job_wrapper(self, job: PipelineJob) -> Callable:
        """Create a wrapper function that handles job execution and tracking"""
        def wrapper():
            if not job.enabled:
                return

            start_time = datetime.now()
            job.last_run = start_time
            job.last_status = PipelineStatus.RUNNING
            records_processed = 0
            error_message = None

            # Log job start
            self._log_job_start(job.name, start_time)

            try:
                # Execute the job
                result = job.func()

                # Extract records processed if returned
                if isinstance(result, dict):
                    records_processed = result.get('records_processed', 0)
                elif isinstance(result, int):
                    records_processed = result

                job.last_status = PipelineStatus.SUCCESS
                job.run_count += 1
                self.total_runs += 1

                logger.info(f"Job {job.name} completed successfully. Records: {records_processed}")

            except Exception as e:
                job.last_status = PipelineStatus.FAILED
                job.error_count += 1
                job.last_error = str(e)
                error_message = str(e)
                self.total_errors += 1

                logger.error(f"Job {job.name} failed: {e}", exc_info=True)

            finally:
                end_time = datetime.now()
                job.last_duration_seconds = (end_time - start_time).total_seconds()

                # Log job completion
                self._log_job_completion(
                    job.name,
                    start_time,
                    end_time,
                    job.last_status.value,
                    records_processed,
                    error_message
                )

        return wrapper

    def _log_job_start(self, job_name: str, started_at: datetime):
        """Log job start to database"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO pipeline_job_status
                    (job_name, status, started_at)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (job_name, PipelineStatus.RUNNING.value, started_at))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log job start: {e}")
            conn.rollback()
        finally:
            self.db_pool.putconn(conn)

    def _log_job_completion(
        self,
        job_name: str,
        started_at: datetime,
        completed_at: datetime,
        status: str,
        records_processed: int,
        error_message: Optional[str]
    ):
        """Log job completion to database"""
        duration = (completed_at - started_at).total_seconds()
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # Update job status
                cursor.execute("""
                    UPDATE pipeline_job_status
                    SET status = %s,
                        completed_at = %s,
                        duration_seconds = %s,
                        records_processed = %s,
                        error_message = %s
                    WHERE job_name = %s AND started_at = %s
                """, (status, completed_at, duration, records_processed,
                      error_message, job_name, started_at))

                # Update daily summary
                cursor.execute("""
                    INSERT INTO pipeline_run_summary
                    (job_name, date, total_runs, successful_runs, failed_runs,
                     total_records_processed, avg_duration_seconds)
                    VALUES (%s, %s, 1,
                            CASE WHEN %s = 'success' THEN 1 ELSE 0 END,
                            CASE WHEN %s = 'failed' THEN 1 ELSE 0 END,
                            %s, %s)
                    ON CONFLICT (job_name, date) DO UPDATE SET
                        total_runs = pipeline_run_summary.total_runs + 1,
                        successful_runs = pipeline_run_summary.successful_runs +
                            CASE WHEN %s = 'success' THEN 1 ELSE 0 END,
                        failed_runs = pipeline_run_summary.failed_runs +
                            CASE WHEN %s = 'failed' THEN 1 ELSE 0 END,
                        total_records_processed = pipeline_run_summary.total_records_processed + %s,
                        avg_duration_seconds = (
                            pipeline_run_summary.avg_duration_seconds * pipeline_run_summary.total_runs + %s
                        ) / (pipeline_run_summary.total_runs + 1),
                        updated_at = CURRENT_TIMESTAMP
                """, (job_name, completed_at.date(), status, status, records_processed, duration,
                      status, status, records_processed, duration))

                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log job completion: {e}")
            conn.rollback()
        finally:
            self.db_pool.putconn(conn)

    def run_job_now(self, job_name: str) -> bool:
        """Manually trigger a job to run immediately"""
        with self._lock:
            if job_name not in self.jobs:
                logger.error(f"Job {job_name} not found")
                return False

            job = self.jobs[job_name]
            wrapper = self._create_job_wrapper(job)

            # Run in a separate thread to not block
            thread = threading.Thread(target=wrapper, name=f"job-{job_name}")
            thread.start()

            return True

    def enable_job(self, job_name: str):
        """Enable a disabled job"""
        with self._lock:
            if job_name in self.jobs:
                self.jobs[job_name].enabled = True
                self._schedule_job(self.jobs[job_name])
                logger.info(f"Enabled job: {job_name}")

    def disable_job(self, job_name: str):
        """Disable a job"""
        with self._lock:
            if job_name in self.jobs:
                self.jobs[job_name].enabled = False
                schedule.clear(job_name)
                logger.info(f"Disabled job: {job_name}")

    def get_job_status(self, job_name: str) -> Optional[Dict]:
        """Get status of a specific job"""
        with self._lock:
            if job_name not in self.jobs:
                return None

            job = self.jobs[job_name]
            return {
                'name': job.name,
                'enabled': job.enabled,
                'schedule_type': job.schedule_type,
                'schedule_value': job.schedule_value,
                'last_run': job.last_run.isoformat() if job.last_run else None,
                'last_status': job.last_status.value,
                'last_duration_seconds': job.last_duration_seconds,
                'run_count': job.run_count,
                'error_count': job.error_count,
                'last_error': job.last_error
            }

    def get_all_job_statuses(self) -> List[Dict]:
        """Get status of all jobs"""
        with self._lock:
            return [self.get_job_status(name) for name in self.jobs]

    def get_pipeline_health(self) -> Dict:
        """Get overall pipeline health metrics"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # Get recent job statistics
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_jobs,
                        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                        AVG(duration_seconds) as avg_duration,
                        MAX(completed_at) as last_completion
                    FROM pipeline_job_status
                    WHERE started_at >= NOW() - INTERVAL '24 hours'
                """)
                row = cursor.fetchone()

                return {
                    'orchestrator_running': self.is_running,
                    'uptime_seconds': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
                    'registered_jobs': len(self.jobs),
                    'enabled_jobs': sum(1 for j in self.jobs.values() if j.enabled),
                    'last_24h': {
                        'total_runs': row[0] or 0,
                        'successful': row[1] or 0,
                        'failed': row[2] or 0,
                        'success_rate': (row[1] / row[0] * 100) if row[0] else 0,
                        'avg_duration_seconds': float(row[3]) if row[3] else 0,
                        'last_completion': row[4].isoformat() if row[4] else None
                    }
                }
        finally:
            self.db_pool.putconn(conn)

    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(5)

    def start(self, blocking: bool = False):
        """Start the pipeline orchestrator"""
        if self.is_running:
            logger.warning("Orchestrator already running")
            return

        self.is_running = True
        self.start_time = datetime.now()

        logger.info("Starting Pipeline Orchestrator...")

        if blocking:
            self._scheduler_loop()
        else:
            self.scheduler_thread = threading.Thread(
                target=self._scheduler_loop,
                name="pipeline-scheduler",
                daemon=True
            )
            self.scheduler_thread.start()

        logger.info("Pipeline Orchestrator started")

    def stop(self):
        """Stop the pipeline orchestrator"""
        if not self.is_running:
            return

        logger.info("Stopping Pipeline Orchestrator...")
        self.is_running = False

        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=10)

        schedule.clear()

        if self.db_pool:
            self.db_pool.closeall()

        logger.info("Pipeline Orchestrator stopped")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def create_default_orchestrator() -> PipelineOrchestrator:
    """Create orchestrator with default MARTA pipeline jobs"""
    from src.data_ingestion.real_gtfs_static_ingestor import RealGTFSStaticIngestor
    from src.data_ingestion.real_gtfs_realtime_ingestor import RealGTFSRealtimeIngestor
    from src.data_ingestion.weather_data_fetcher import fetch_current_weather, store_weather_data

    orchestrator = PipelineOrchestrator()

    # GTFS Static - Daily at 3:00 AM
    static_ingestor = RealGTFSStaticIngestor()
    orchestrator.register_job(
        name="gtfs_static_ingestion",
        func=lambda: static_ingestor.run_ingestion(download_new=True),
        schedule_type="daily",
        schedule_value="03:00",
        metadata={"description": "Download and ingest GTFS static data"}
    )

    # GTFS Realtime - Every 90 seconds
    realtime_ingestor = RealGTFSRealtimeIngestor()
    orchestrator.register_job(
        name="gtfs_realtime_ingestion",
        func=realtime_ingestor.run_single_fetch,
        schedule_type="interval",
        schedule_value=90,
        metadata={"description": "Fetch GTFS-RT vehicle positions and trip updates"}
    )

    # Weather Data - Every 30 minutes
    orchestrator.register_job(
        name="weather_data_ingestion",
        func=fetch_current_weather,
        schedule_type="minutes",
        schedule_value=30,
        metadata={"description": "Fetch current weather data for Atlanta"}
    )

    return orchestrator


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    orchestrator = create_default_orchestrator()

    try:
        orchestrator.start(blocking=True)
    except KeyboardInterrupt:
        orchestrator.stop()
