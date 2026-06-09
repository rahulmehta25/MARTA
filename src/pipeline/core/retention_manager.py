#!/usr/bin/env python3
"""
Retention Manager - Data retention policies and archival management
Handles automatic cleanup, archiving, and configurable retention periods
"""
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum
import json
import gzip
import shutil
import psycopg2
from psycopg2 import pool

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from config.settings import settings

logger = logging.getLogger(__name__)


class RetentionAction(Enum):
    DELETE = "delete"
    ARCHIVE = "archive"
    COMPRESS = "compress"
    MOVE_TO_COLD_STORAGE = "cold_storage"


@dataclass
class RetentionPolicy:
    """Data retention policy configuration"""
    table_name: str
    retention_days: int
    action: RetentionAction
    partition_column: str = "created_at"  # Column used for date partitioning
    archive_path: Optional[str] = None  # Path for archived data
    enabled: bool = True
    batch_size: int = 10000  # Records per batch for deletion
    metadata: Optional[Dict] = None


class RetentionManager:
    """
    Manages data retention policies across pipeline tables
    Supports deletion, archival, and compression strategies
    """

    # Default retention policies for MARTA tables
    DEFAULT_POLICIES = [
        # Real-time data - shorter retention
        RetentionPolicy(
            table_name="gtfs_vehicle_positions",
            retention_days=30,
            action=RetentionAction.ARCHIVE,
            partition_column="timestamp",
            archive_path="data/archive/vehicle_positions"
        ),
        RetentionPolicy(
            table_name="gtfs_trip_updates",
            retention_days=30,
            action=RetentionAction.ARCHIVE,
            partition_column="timestamp",
            archive_path="data/archive/trip_updates"
        ),
        RetentionPolicy(
            table_name="unified_realtime_data",
            retention_days=90,
            action=RetentionAction.ARCHIVE,
            partition_column="timestamp",
            archive_path="data/archive/unified_realtime"
        ),

        # Historical/analytics data - longer retention
        RetentionPolicy(
            table_name="unified_realtime_historical_data",
            retention_days=365,
            action=RetentionAction.ARCHIVE,
            partition_column="timestamp",
            archive_path="data/archive/historical"
        ),

        # ML data
        RetentionPolicy(
            table_name="feature_store",
            retention_days=180,
            action=RetentionAction.DELETE,
            partition_column="timestamp"
        ),
        RetentionPolicy(
            table_name="model_predictions",
            retention_days=90,
            action=RetentionAction.DELETE,
            partition_column="created_at"
        ),

        # Pipeline logs
        RetentionPolicy(
            table_name="pipeline_logs",
            retention_days=60,
            action=RetentionAction.DELETE,
            partition_column="timestamp"
        ),
        RetentionPolicy(
            table_name="pipeline_job_status",
            retention_days=90,
            action=RetentionAction.DELETE,
            partition_column="created_at"
        ),

        # Weather and events - moderate retention
        RetentionPolicy(
            table_name="atlanta_weather_data",
            retention_days=365,
            action=RetentionAction.ARCHIVE,
            partition_column="timestamp",
            archive_path="data/archive/weather"
        ),
        RetentionPolicy(
            table_name="atlanta_events_data",
            retention_days=365,
            action=RetentionAction.ARCHIVE,
            partition_column="created_at",
            archive_path="data/archive/events"
        ),

        # Data quality metrics
        RetentionPolicy(
            table_name="data_quality_metrics",
            retention_days=180,
            action=RetentionAction.DELETE,
            partition_column="check_timestamp"
        ),

        # CDC logs
        RetentionPolicy(
            table_name="cdc_change_log",
            retention_days=30,
            action=RetentionAction.DELETE,
            partition_column="change_timestamp"
        ),
    ]

    def __init__(
        self,
        db_pool: Optional[pool.ThreadedConnectionPool] = None,
        archive_base_path: str = "data/archive"
    ):
        self.archive_base_path = archive_base_path
        self.policies: Dict[str, RetentionPolicy] = {}

        # Initialize database connection pool
        self.db_pool = db_pool or self._create_db_pool()

        # Initialize tables
        self._init_retention_tables()

        # Load default policies
        for policy in self.DEFAULT_POLICIES:
            self.add_policy(policy)

        logger.info(f"RetentionManager initialized with {len(self.policies)} policies")

    def _create_db_pool(self) -> pool.ThreadedConnectionPool:
        """Create database connection pool"""
        return pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=5,
            host=settings.DB_HOST,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            port=settings.DB_PORT
        )

    def _init_retention_tables(self):
        """Initialize retention tracking tables"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    -- Retention policy configuration
                    CREATE TABLE IF NOT EXISTS retention_policies (
                        id SERIAL PRIMARY KEY,
                        table_name VARCHAR(255) UNIQUE NOT NULL,
                        retention_days INTEGER NOT NULL,
                        action VARCHAR(50) NOT NULL,
                        partition_column VARCHAR(255) NOT NULL,
                        archive_path TEXT,
                        enabled BOOLEAN DEFAULT TRUE,
                        batch_size INTEGER DEFAULT 10000,
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    -- Retention execution log
                    CREATE TABLE IF NOT EXISTS retention_execution_log (
                        id SERIAL PRIMARY KEY,
                        table_name VARCHAR(255) NOT NULL,
                        action VARCHAR(50) NOT NULL,
                        started_at TIMESTAMP NOT NULL,
                        completed_at TIMESTAMP,
                        records_processed INTEGER DEFAULT 0,
                        records_archived INTEGER DEFAULT 0,
                        records_deleted INTEGER DEFAULT 0,
                        archive_file_path TEXT,
                        status VARCHAR(50) NOT NULL,
                        error_message TEXT,
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE INDEX IF NOT EXISTS idx_retention_log_table
                        ON retention_execution_log(table_name);
                    CREATE INDEX IF NOT EXISTS idx_retention_log_started
                        ON retention_execution_log(started_at);
                """)
                conn.commit()
        finally:
            self.db_pool.putconn(conn)

    def add_policy(self, policy: RetentionPolicy):
        """Add or update a retention policy"""
        self.policies[policy.table_name] = policy

        # Persist to database
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO retention_policies
                    (table_name, retention_days, action, partition_column,
                     archive_path, enabled, batch_size, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (table_name) DO UPDATE SET
                        retention_days = EXCLUDED.retention_days,
                        action = EXCLUDED.action,
                        partition_column = EXCLUDED.partition_column,
                        archive_path = EXCLUDED.archive_path,
                        enabled = EXCLUDED.enabled,
                        batch_size = EXCLUDED.batch_size,
                        metadata = EXCLUDED.metadata,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    policy.table_name,
                    policy.retention_days,
                    policy.action.value,
                    policy.partition_column,
                    policy.archive_path,
                    policy.enabled,
                    policy.batch_size,
                    json.dumps(policy.metadata) if policy.metadata else None
                ))
                conn.commit()
        finally:
            self.db_pool.putconn(conn)

    def update_retention_days(self, table_name: str, retention_days: int):
        """Update retention period for a table"""
        if table_name in self.policies:
            self.policies[table_name].retention_days = retention_days
            self.add_policy(self.policies[table_name])  # Persist update

    def get_policy(self, table_name: str) -> Optional[RetentionPolicy]:
        """Get retention policy for a table"""
        return self.policies.get(table_name)

    def list_policies(self) -> List[Dict]:
        """List all retention policies"""
        return [
            {
                'table_name': p.table_name,
                'retention_days': p.retention_days,
                'action': p.action.value,
                'partition_column': p.partition_column,
                'archive_path': p.archive_path,
                'enabled': p.enabled
            }
            for p in self.policies.values()
        ]

    def _check_table_exists(self, table_name: str, conn) -> bool:
        """Check if a table exists"""
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = %s
                )
            """, (table_name,))
            return cursor.fetchone()[0]

    def _get_records_to_process(
        self,
        policy: RetentionPolicy,
        conn
    ) -> int:
        """Get count of records eligible for retention action"""
        cutoff_date = datetime.now() - timedelta(days=policy.retention_days)

        with conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT COUNT(*)
                FROM {policy.table_name}
                WHERE {policy.partition_column} < %s
            """, (cutoff_date,))
            return cursor.fetchone()[0]

    def _archive_records(
        self,
        policy: RetentionPolicy,
        conn
    ) -> Dict[str, Any]:
        """Archive records to compressed file"""
        cutoff_date = datetime.now() - timedelta(days=policy.retention_days)
        archive_dir = policy.archive_path or os.path.join(
            self.archive_base_path, policy.table_name
        )
        os.makedirs(archive_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archive_file = os.path.join(
            archive_dir,
            f"{policy.table_name}_{timestamp}.jsonl.gz"
        )

        records_archived = 0

        with conn.cursor() as cursor:
            # Fetch records in batches
            cursor.execute(f"""
                SELECT * FROM {policy.table_name}
                WHERE {policy.partition_column} < %s
                ORDER BY {policy.partition_column}
                LIMIT %s
            """, (cutoff_date, policy.batch_size * 10))

            columns = [desc[0] for desc in cursor.description]

            with gzip.open(archive_file, 'wt', encoding='utf-8') as f:
                for row in cursor:
                    record = dict(zip(columns, row))
                    # Convert datetime objects to strings
                    for k, v in record.items():
                        if isinstance(v, datetime):
                            record[k] = v.isoformat()
                    f.write(json.dumps(record) + '\n')
                    records_archived += 1

        logger.info(f"Archived {records_archived} records to {archive_file}")

        return {
            'records_archived': records_archived,
            'archive_file': archive_file
        }

    def _delete_records(
        self,
        policy: RetentionPolicy,
        conn
    ) -> int:
        """Delete records in batches"""
        cutoff_date = datetime.now() - timedelta(days=policy.retention_days)
        total_deleted = 0

        with conn.cursor() as cursor:
            while True:
                # Delete in batches to avoid long locks
                cursor.execute(f"""
                    DELETE FROM {policy.table_name}
                    WHERE ctid IN (
                        SELECT ctid FROM {policy.table_name}
                        WHERE {policy.partition_column} < %s
                        LIMIT %s
                    )
                """, (cutoff_date, policy.batch_size))

                deleted = cursor.rowcount
                conn.commit()

                if deleted == 0:
                    break

                total_deleted += deleted
                logger.debug(f"Deleted {deleted} records from {policy.table_name}")

        return total_deleted

    def execute_policy(self, table_name: str) -> Dict[str, Any]:
        """Execute retention policy for a specific table"""
        policy = self.policies.get(table_name)
        if not policy:
            raise ValueError(f"No retention policy found for table: {table_name}")

        if not policy.enabled:
            logger.info(f"Policy for {table_name} is disabled, skipping")
            return {'status': 'skipped', 'reason': 'disabled'}

        start_time = datetime.now()
        result = {
            'table_name': table_name,
            'action': policy.action.value,
            'started_at': start_time,
            'records_processed': 0,
            'records_archived': 0,
            'records_deleted': 0,
            'status': 'running'
        }

        conn = self.db_pool.getconn()
        try:
            # Check if table exists
            if not self._check_table_exists(table_name, conn):
                logger.warning(f"Table {table_name} does not exist, skipping")
                result['status'] = 'skipped'
                result['error_message'] = 'Table does not exist'
                return result

            # Get count of records to process
            records_to_process = self._get_records_to_process(policy, conn)
            result['records_processed'] = records_to_process

            if records_to_process == 0:
                logger.info(f"No records to process for {table_name}")
                result['status'] = 'success'
                result['completed_at'] = datetime.now()
                return result

            logger.info(f"Processing {records_to_process} records for {table_name}")

            # Execute action
            if policy.action == RetentionAction.ARCHIVE:
                archive_result = self._archive_records(policy, conn)
                result['records_archived'] = archive_result['records_archived']
                result['archive_file_path'] = archive_result['archive_file']

                # Delete archived records
                deleted = self._delete_records(policy, conn)
                result['records_deleted'] = deleted

            elif policy.action == RetentionAction.DELETE:
                deleted = self._delete_records(policy, conn)
                result['records_deleted'] = deleted

            elif policy.action == RetentionAction.COMPRESS:
                # Compress old partitions (PostgreSQL native)
                logger.info(f"Compression for {table_name} - handled by PostgreSQL")

            result['status'] = 'success'
            result['completed_at'] = datetime.now()

        except Exception as e:
            result['status'] = 'failed'
            result['error_message'] = str(e)
            logger.error(f"Retention policy execution failed for {table_name}: {e}")
            conn.rollback()

        finally:
            self.db_pool.putconn(conn)

        # Log execution
        self._log_execution(result)

        return result

    def _log_execution(self, result: Dict[str, Any]):
        """Log retention execution to database"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO retention_execution_log
                    (table_name, action, started_at, completed_at,
                     records_processed, records_archived, records_deleted,
                     archive_file_path, status, error_message, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    result['table_name'],
                    result['action'],
                    result['started_at'],
                    result.get('completed_at'),
                    result['records_processed'],
                    result['records_archived'],
                    result['records_deleted'],
                    result.get('archive_file_path'),
                    result['status'],
                    result.get('error_message'),
                    json.dumps(result.get('metadata', {}))
                ))
                conn.commit()
        finally:
            self.db_pool.putconn(conn)

    def run_all_policies(self) -> List[Dict[str, Any]]:
        """Execute all enabled retention policies"""
        results = []

        for table_name, policy in self.policies.items():
            if policy.enabled:
                try:
                    result = self.execute_policy(table_name)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to execute policy for {table_name}: {e}")
                    results.append({
                        'table_name': table_name,
                        'status': 'failed',
                        'error_message': str(e)
                    })

        return results

    def get_retention_stats(self) -> Dict[str, Any]:
        """Get retention execution statistics"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_executions,
                        SUM(records_deleted) as total_deleted,
                        SUM(records_archived) as total_archived,
                        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                    FROM retention_execution_log
                    WHERE started_at >= NOW() - INTERVAL '30 days'
                """)
                row = cursor.fetchone()

                # Get recent executions
                cursor.execute("""
                    SELECT table_name, action, started_at, status,
                           records_deleted, records_archived
                    FROM retention_execution_log
                    ORDER BY started_at DESC
                    LIMIT 10
                """)
                recent = [
                    {
                        'table_name': r[0],
                        'action': r[1],
                        'started_at': r[2].isoformat() if r[2] else None,
                        'status': r[3],
                        'records_deleted': r[4],
                        'records_archived': r[5]
                    }
                    for r in cursor.fetchall()
                ]

                return {
                    'last_30_days': {
                        'total_executions': row[0] or 0,
                        'total_records_deleted': row[1] or 0,
                        'total_records_archived': row[2] or 0,
                        'successful': row[3] or 0,
                        'failed': row[4] or 0
                    },
                    'recent_executions': recent,
                    'policies_count': len(self.policies),
                    'enabled_policies': sum(1 for p in self.policies.values() if p.enabled)
                }
        finally:
            self.db_pool.putconn(conn)

    def cleanup_archive_files(self, max_age_days: int = 365):
        """Clean up old archive files"""
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        files_deleted = 0

        for root, dirs, files in os.walk(self.archive_base_path):
            for file in files:
                file_path = os.path.join(root, file)
                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))

                if file_mtime < cutoff_date:
                    try:
                        os.remove(file_path)
                        files_deleted += 1
                        logger.info(f"Deleted old archive file: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to delete {file_path}: {e}")

        return files_deleted


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    manager = RetentionManager()

    # List all policies
    print("\nRetention Policies:")
    for policy in manager.list_policies():
        print(f"  {policy['table_name']}: {policy['retention_days']} days "
              f"({policy['action']}) - Enabled: {policy['enabled']}")

    # Get statistics
    stats = manager.get_retention_stats()
    print(f"\nRetention Stats (last 30 days):")
    print(f"  Total executions: {stats['last_30_days']['total_executions']}")
    print(f"  Records deleted: {stats['last_30_days']['total_records_deleted']}")
    print(f"  Records archived: {stats['last_30_days']['total_records_archived']}")
