#!/usr/bin/env python3
"""
Pipeline Status Tracker - Monitoring dashboard data layer
Exposes data quality metrics, pipeline status, and ingestion timestamps
"""
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
import json
import psycopg2
from psycopg2 import pool

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class TableFreshness:
    """Freshness metrics for a table"""
    table_name: str
    last_update: Optional[datetime]
    record_count: int
    age_seconds: float
    is_stale: bool
    threshold_seconds: int


class PipelineStatusTracker:
    """
    Dashboard data layer for pipeline monitoring
    Provides comprehensive status, metrics, and alerting capabilities
    """

    # Freshness thresholds by table (seconds)
    FRESHNESS_THRESHOLDS = {
        'gtfs_vehicle_positions': 300,  # 5 minutes
        'gtfs_trip_updates': 300,
        'unified_realtime_data': 600,  # 10 minutes
        'atlanta_weather_data': 3600,  # 1 hour
        'atlanta_events_data': 86400,  # 1 day
        'gtfs_stops': 86400 * 7,  # 1 week (static data)
        'gtfs_routes': 86400 * 7,
        'gtfs_trips': 86400 * 7,
    }

    def __init__(self, db_pool: Optional[pool.ThreadedConnectionPool] = None):
        self.db_pool = db_pool or self._create_db_pool()
        self._init_status_tables()
        logger.info("PipelineStatusTracker initialized")

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

    def _init_status_tables(self):
        """Initialize status tracking tables"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    -- Ingestion timestamps tracking
                    CREATE TABLE IF NOT EXISTS ingestion_timestamps (
                        id SERIAL PRIMARY KEY,
                        source_name VARCHAR(255) NOT NULL,
                        table_name VARCHAR(255) NOT NULL,
                        last_successful_ingestion TIMESTAMP,
                        last_attempted_ingestion TIMESTAMP,
                        records_ingested INTEGER DEFAULT 0,
                        status VARCHAR(50),
                        error_message TEXT,
                        metadata JSONB,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(source_name, table_name)
                    );

                    CREATE INDEX IF NOT EXISTS idx_ingestion_ts_source
                        ON ingestion_timestamps(source_name);

                    -- System health metrics
                    CREATE TABLE IF NOT EXISTS system_health_metrics (
                        id SERIAL PRIMARY KEY,
                        metric_name VARCHAR(255) NOT NULL,
                        metric_value NUMERIC,
                        metric_unit VARCHAR(50),
                        threshold_warning NUMERIC,
                        threshold_critical NUMERIC,
                        status VARCHAR(50),
                        measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata JSONB
                    );

                    CREATE INDEX IF NOT EXISTS idx_health_metrics_name
                        ON system_health_metrics(metric_name);
                    CREATE INDEX IF NOT EXISTS idx_health_metrics_time
                        ON system_health_metrics(measured_at);

                    -- Dashboard snapshot (materialized every 5 minutes)
                    CREATE TABLE IF NOT EXISTS dashboard_snapshot (
                        id SERIAL PRIMARY KEY,
                        snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        pipeline_health JSONB,
                        data_quality_summary JSONB,
                        table_freshness JSONB,
                        recent_errors JSONB,
                        system_metrics JSONB
                    );
                """)
                conn.commit()
        finally:
            self.db_pool.putconn(conn)

    def update_ingestion_timestamp(
        self,
        source_name: str,
        table_name: str,
        records_ingested: int,
        status: str = 'success',
        error_message: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Update ingestion timestamp for a source/table"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                now = datetime.now()
                cursor.execute("""
                    INSERT INTO ingestion_timestamps
                    (source_name, table_name, last_successful_ingestion,
                     last_attempted_ingestion, records_ingested, status,
                     error_message, metadata, updated_at)
                    VALUES (%s, %s,
                            CASE WHEN %s = 'success' THEN %s ELSE NULL END,
                            %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source_name, table_name) DO UPDATE SET
                        last_successful_ingestion =
                            CASE WHEN %s = 'success'
                                 THEN %s
                                 ELSE ingestion_timestamps.last_successful_ingestion END,
                        last_attempted_ingestion = %s,
                        records_ingested = ingestion_timestamps.records_ingested + %s,
                        status = %s,
                        error_message = %s,
                        metadata = COALESCE(ingestion_timestamps.metadata, '{}'::jsonb) || %s::jsonb,
                        updated_at = %s
                """, (
                    source_name, table_name, status, now, now, records_ingested,
                    status, error_message, json.dumps(metadata or {}), now,
                    status, now, now, records_ingested, status, error_message,
                    json.dumps(metadata or {}), now
                ))
                conn.commit()
        finally:
            self.db_pool.putconn(conn)

    def get_table_freshness(self, table_name: str) -> Optional[TableFreshness]:
        """Get freshness metrics for a specific table"""
        threshold = self.FRESHNESS_THRESHOLDS.get(table_name, 3600)

        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # Check if table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = %s
                    )
                """, (table_name,))

                if not cursor.fetchone()[0]:
                    return None

                # Get timestamp column (varies by table)
                timestamp_col = 'created_at'
                if table_name in ['gtfs_vehicle_positions', 'gtfs_trip_updates',
                                  'unified_realtime_data', 'atlanta_weather_data']:
                    timestamp_col = 'timestamp'

                try:
                    cursor.execute(f"""
                        SELECT MAX({timestamp_col}), COUNT(*)
                        FROM {table_name}
                    """)
                    row = cursor.fetchone()
                except:
                    # Fall back to created_at
                    cursor.execute(f"""
                        SELECT MAX(created_at), COUNT(*)
                        FROM {table_name}
                    """)
                    row = cursor.fetchone()

                last_update = row[0]
                record_count = row[1] or 0

                age_seconds = 0
                if last_update:
                    age_seconds = (datetime.now() - last_update).total_seconds()

                return TableFreshness(
                    table_name=table_name,
                    last_update=last_update,
                    record_count=record_count,
                    age_seconds=age_seconds,
                    is_stale=age_seconds > threshold,
                    threshold_seconds=threshold
                )
        finally:
            self.db_pool.putconn(conn)

    def get_all_table_freshness(self) -> List[Dict]:
        """Get freshness metrics for all tracked tables"""
        results = []

        for table_name in self.FRESHNESS_THRESHOLDS.keys():
            freshness = self.get_table_freshness(table_name)
            if freshness:
                results.append({
                    'table_name': freshness.table_name,
                    'last_update': freshness.last_update.isoformat() if freshness.last_update else None,
                    'record_count': freshness.record_count,
                    'age_seconds': freshness.age_seconds,
                    'age_human': self._format_duration(freshness.age_seconds),
                    'is_stale': freshness.is_stale,
                    'threshold_seconds': freshness.threshold_seconds
                })

        return results

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds / 60:.0f}m"
        elif seconds < 86400:
            return f"{seconds / 3600:.1f}h"
        else:
            return f"{seconds / 86400:.1f}d"

    def get_pipeline_health(self) -> Dict[str, Any]:
        """Get overall pipeline health status"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # Get pipeline job statistics
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_jobs,
                        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                        MAX(completed_at) as last_completion
                    FROM pipeline_job_status
                    WHERE started_at >= NOW() - INTERVAL '1 hour'
                """)
                job_stats = cursor.fetchone()

                # Get quality check statistics
                cursor.execute("""
                    SELECT
                        SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed,
                        SUM(CASE WHEN status IN ('failed', 'error') THEN 1 ELSE 0 END) as failed,
                        COUNT(*) as total
                    FROM data_quality_metrics
                    WHERE check_timestamp >= NOW() - INTERVAL '1 hour'
                """)
                quality_stats = cursor.fetchone()

                # Get error count
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM pipeline_logs
                    WHERE level IN ('ERROR', 'CRITICAL')
                      AND timestamp >= NOW() - INTERVAL '1 hour'
                """)
                error_count = cursor.fetchone()[0] or 0

                # Calculate overall health score
                job_success_rate = (job_stats[1] or 0) / max(job_stats[0] or 1, 1)
                quality_pass_rate = (quality_stats[0] or 0) / max(quality_stats[2] or 1, 1)

                # Freshness check
                stale_tables = sum(
                    1 for f in self.get_all_table_freshness() if f['is_stale']
                )
                total_tables = len(self.FRESHNESS_THRESHOLDS)
                freshness_rate = 1 - (stale_tables / total_tables)

                # Overall health (weighted average)
                health_score = (
                    job_success_rate * 0.4 +
                    quality_pass_rate * 0.3 +
                    freshness_rate * 0.3
                )

                health_status = 'healthy'
                if health_score < 0.8:
                    health_status = 'degraded'
                if health_score < 0.5:
                    health_status = 'unhealthy'

                return {
                    'status': health_status,
                    'health_score': health_score,
                    'last_hour': {
                        'jobs_total': job_stats[0] or 0,
                        'jobs_successful': job_stats[1] or 0,
                        'jobs_failed': job_stats[2] or 0,
                        'job_success_rate': job_success_rate,
                        'quality_checks_passed': quality_stats[0] or 0,
                        'quality_checks_failed': quality_stats[1] or 0,
                        'quality_pass_rate': quality_pass_rate,
                        'error_count': error_count,
                        'stale_tables': stale_tables,
                        'freshness_rate': freshness_rate
                    },
                    'last_completion': job_stats[3].isoformat() if job_stats[3] else None,
                    'checked_at': datetime.now().isoformat()
                }
        finally:
            self.db_pool.putconn(conn)

    def get_recent_errors(self, limit: int = 20) -> List[Dict]:
        """Get recent pipeline errors"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        timestamp,
                        pipeline_name,
                        stage,
                        message,
                        error_type,
                        run_id
                    FROM pipeline_logs
                    WHERE level IN ('ERROR', 'CRITICAL')
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (limit,))

                return [
                    {
                        'timestamp': row[0].isoformat() if row[0] else None,
                        'pipeline_name': row[1],
                        'stage': row[2],
                        'message': row[3],
                        'error_type': row[4],
                        'run_id': row[5]
                    }
                    for row in cursor.fetchall()
                ]
        finally:
            self.db_pool.putconn(conn)

    def get_ingestion_status(self) -> List[Dict]:
        """Get status of all data sources"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        source_name,
                        table_name,
                        last_successful_ingestion,
                        last_attempted_ingestion,
                        records_ingested,
                        status,
                        error_message,
                        updated_at
                    FROM ingestion_timestamps
                    ORDER BY source_name, table_name
                """)

                return [
                    {
                        'source_name': row[0],
                        'table_name': row[1],
                        'last_successful': row[2].isoformat() if row[2] else None,
                        'last_attempted': row[3].isoformat() if row[3] else None,
                        'records_ingested': row[4],
                        'status': row[5],
                        'error_message': row[6],
                        'updated_at': row[7].isoformat() if row[7] else None
                    }
                    for row in cursor.fetchall()
                ]
        finally:
            self.db_pool.putconn(conn)

    def create_dashboard_snapshot(self) -> Dict[str, Any]:
        """Create a snapshot of all dashboard data"""
        snapshot = {
            'snapshot_time': datetime.now().isoformat(),
            'pipeline_health': self.get_pipeline_health(),
            'table_freshness': self.get_all_table_freshness(),
            'recent_errors': self.get_recent_errors(limit=10),
            'ingestion_status': self.get_ingestion_status()
        }

        # Save to database
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO dashboard_snapshot
                    (pipeline_health, data_quality_summary, table_freshness,
                     recent_errors, system_metrics)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    json.dumps(snapshot['pipeline_health']),
                    json.dumps({}),
                    json.dumps(snapshot['table_freshness']),
                    json.dumps(snapshot['recent_errors']),
                    json.dumps({'ingestion_status': snapshot['ingestion_status']})
                ))
                conn.commit()
        finally:
            self.db_pool.putconn(conn)

        return snapshot

    def get_latest_snapshot(self) -> Optional[Dict]:
        """Get the most recent dashboard snapshot"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        snapshot_time,
                        pipeline_health,
                        data_quality_summary,
                        table_freshness,
                        recent_errors,
                        system_metrics
                    FROM dashboard_snapshot
                    ORDER BY snapshot_time DESC
                    LIMIT 1
                """)
                row = cursor.fetchone()

                if not row:
                    return None

                return {
                    'snapshot_time': row[0].isoformat() if row[0] else None,
                    'pipeline_health': row[1],
                    'data_quality_summary': row[2],
                    'table_freshness': row[3],
                    'recent_errors': row[4],
                    'system_metrics': row[5]
                }
        finally:
            self.db_pool.putconn(conn)

    def get_daily_statistics(self, days: int = 7) -> List[Dict]:
        """Get daily pipeline statistics"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        date,
                        SUM(total_runs) as total_runs,
                        SUM(successful_runs) as successful_runs,
                        SUM(failed_runs) as failed_runs,
                        SUM(total_records_processed) as total_records,
                        AVG(avg_duration_seconds) as avg_duration
                    FROM pipeline_run_summary
                    WHERE date >= CURRENT_DATE - INTERVAL '%s days'
                    GROUP BY date
                    ORDER BY date DESC
                """, (days,))

                return [
                    {
                        'date': row[0].isoformat() if row[0] else None,
                        'total_runs': row[1] or 0,
                        'successful_runs': row[2] or 0,
                        'failed_runs': row[3] or 0,
                        'total_records': row[4] or 0,
                        'avg_duration_seconds': float(row[5]) if row[5] else 0,
                        'success_rate': (row[2] or 0) / max(row[1] or 1, 1)
                    }
                    for row in cursor.fetchall()
                ]
        finally:
            self.db_pool.putconn(conn)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    tracker = PipelineStatusTracker()

    # Get pipeline health
    health = tracker.get_pipeline_health()
    print(f"\nPipeline Health: {health['status']} (score: {health['health_score']:.2f})")

    # Get table freshness
    print("\nTable Freshness:")
    for freshness in tracker.get_all_table_freshness():
        status = "STALE" if freshness['is_stale'] else "OK"
        print(f"  [{status}] {freshness['table_name']}: {freshness['age_human']} old")

    # Get recent errors
    errors = tracker.get_recent_errors(limit=5)
    if errors:
        print("\nRecent Errors:")
        for error in errors:
            print(f"  [{error['timestamp']}] {error['pipeline_name']}: {error['message'][:50]}...")
