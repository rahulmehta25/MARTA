#!/usr/bin/env python3
"""
Change Data Capture (CDC) - Track and capture data changes across tables
Supports trigger-based CDC for PostgreSQL with change log management
"""
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum
import json
import psycopg2
from psycopg2 import pool

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from config.settings import settings

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


@dataclass
class ChangeRecord:
    """Represents a captured data change"""
    change_id: int
    table_name: str
    change_type: ChangeType
    primary_key: Dict
    old_data: Optional[Dict]
    new_data: Optional[Dict]
    change_timestamp: datetime
    transaction_id: int
    user_name: Optional[str]


class ChangeDataCapture:
    """
    PostgreSQL-based Change Data Capture system
    Uses triggers to capture INSERT, UPDATE, DELETE operations
    """

    # Tables to track for CDC
    CDC_TABLES = [
        'gtfs_stops',
        'gtfs_routes',
        'gtfs_trips',
        'gtfs_stop_times',
        'gtfs_calendar',
        'unified_realtime_data',
        'model_predictions',
        'route_optimization_results',
    ]

    def __init__(self, db_pool: Optional[pool.ThreadedConnectionPool] = None):
        self.db_pool = db_pool or self._create_db_pool()
        self._init_cdc_infrastructure()
        logger.info("ChangeDataCapture initialized")

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

    def _init_cdc_infrastructure(self):
        """Initialize CDC infrastructure - tables and functions"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # Create CDC change log table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS cdc_change_log (
                        change_id BIGSERIAL PRIMARY KEY,
                        table_name VARCHAR(255) NOT NULL,
                        change_type VARCHAR(20) NOT NULL,
                        primary_key JSONB NOT NULL,
                        old_data JSONB,
                        new_data JSONB,
                        change_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        transaction_id BIGINT,
                        user_name VARCHAR(255),
                        session_id VARCHAR(255),
                        metadata JSONB
                    );

                    -- Indexes for efficient querying
                    CREATE INDEX IF NOT EXISTS idx_cdc_table_name
                        ON cdc_change_log(table_name);
                    CREATE INDEX IF NOT EXISTS idx_cdc_change_type
                        ON cdc_change_log(change_type);
                    CREATE INDEX IF NOT EXISTS idx_cdc_timestamp
                        ON cdc_change_log(change_timestamp);
                    CREATE INDEX IF NOT EXISTS idx_cdc_primary_key
                        ON cdc_change_log USING GIN(primary_key);

                    -- CDC configuration table
                    CREATE TABLE IF NOT EXISTS cdc_table_config (
                        id SERIAL PRIMARY KEY,
                        table_name VARCHAR(255) UNIQUE NOT NULL,
                        primary_key_columns TEXT[] NOT NULL,
                        tracked_columns TEXT[],  -- NULL means all columns
                        enabled BOOLEAN DEFAULT TRUE,
                        capture_inserts BOOLEAN DEFAULT TRUE,
                        capture_updates BOOLEAN DEFAULT TRUE,
                        capture_deletes BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    -- CDC replication slot status (for logical replication)
                    CREATE TABLE IF NOT EXISTS cdc_replication_status (
                        id SERIAL PRIMARY KEY,
                        slot_name VARCHAR(255) NOT NULL,
                        last_lsn VARCHAR(50),
                        last_processed_at TIMESTAMP,
                        status VARCHAR(50),
                        metadata JSONB,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                # Create the CDC trigger function
                cursor.execute("""
                    CREATE OR REPLACE FUNCTION cdc_capture_changes()
                    RETURNS TRIGGER AS $$
                    DECLARE
                        pk_columns TEXT[];
                        pk_values JSONB;
                        old_json JSONB;
                        new_json JSONB;
                        config_record RECORD;
                    BEGIN
                        -- Get configuration for this table
                        SELECT * INTO config_record
                        FROM cdc_table_config
                        WHERE table_name = TG_TABLE_NAME AND enabled = TRUE;

                        -- If no config or disabled, skip
                        IF NOT FOUND THEN
                            IF TG_OP = 'DELETE' THEN
                                RETURN OLD;
                            ELSE
                                RETURN NEW;
                            END IF;
                        END IF;

                        -- Get primary key columns
                        pk_columns := config_record.primary_key_columns;

                        -- Build primary key JSON
                        IF TG_OP = 'DELETE' THEN
                            pk_values := to_jsonb(OLD) - (
                                SELECT array_agg(key)
                                FROM jsonb_object_keys(to_jsonb(OLD)) AS key
                                WHERE NOT (key = ANY(pk_columns))
                            );
                        ELSE
                            pk_values := to_jsonb(NEW) - (
                                SELECT array_agg(key)
                                FROM jsonb_object_keys(to_jsonb(NEW)) AS key
                                WHERE NOT (key = ANY(pk_columns))
                            );
                        END IF;

                        -- Convert to JSONB
                        IF TG_OP = 'INSERT' THEN
                            IF NOT config_record.capture_inserts THEN
                                RETURN NEW;
                            END IF;
                            new_json := to_jsonb(NEW);
                            old_json := NULL;
                        ELSIF TG_OP = 'UPDATE' THEN
                            IF NOT config_record.capture_updates THEN
                                RETURN NEW;
                            END IF;
                            new_json := to_jsonb(NEW);
                            old_json := to_jsonb(OLD);

                            -- Skip if no actual changes
                            IF new_json = old_json THEN
                                RETURN NEW;
                            END IF;
                        ELSIF TG_OP = 'DELETE' THEN
                            IF NOT config_record.capture_deletes THEN
                                RETURN OLD;
                            END IF;
                            old_json := to_jsonb(OLD);
                            new_json := NULL;
                        END IF;

                        -- Insert change record
                        INSERT INTO cdc_change_log (
                            table_name,
                            change_type,
                            primary_key,
                            old_data,
                            new_data,
                            transaction_id,
                            user_name
                        ) VALUES (
                            TG_TABLE_NAME,
                            TG_OP,
                            pk_values,
                            old_json,
                            new_json,
                            txid_current(),
                            current_user
                        );

                        IF TG_OP = 'DELETE' THEN
                            RETURN OLD;
                        ELSE
                            RETURN NEW;
                        END IF;
                    END;
                    $$ LANGUAGE plpgsql;
                """)

                conn.commit()
                logger.info("CDC infrastructure initialized")

        finally:
            self.db_pool.putconn(conn)

    def enable_cdc_for_table(
        self,
        table_name: str,
        primary_key_columns: List[str],
        tracked_columns: Optional[List[str]] = None,
        capture_inserts: bool = True,
        capture_updates: bool = True,
        capture_deletes: bool = True
    ):
        """Enable CDC for a specific table"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # Insert/update configuration
                cursor.execute("""
                    INSERT INTO cdc_table_config
                    (table_name, primary_key_columns, tracked_columns,
                     capture_inserts, capture_updates, capture_deletes)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (table_name) DO UPDATE SET
                        primary_key_columns = EXCLUDED.primary_key_columns,
                        tracked_columns = EXCLUDED.tracked_columns,
                        capture_inserts = EXCLUDED.capture_inserts,
                        capture_updates = EXCLUDED.capture_updates,
                        capture_deletes = EXCLUDED.capture_deletes,
                        enabled = TRUE,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    table_name,
                    primary_key_columns,
                    tracked_columns,
                    capture_inserts,
                    capture_updates,
                    capture_deletes
                ))

                # Create trigger
                cursor.execute(f"""
                    DROP TRIGGER IF EXISTS cdc_trigger_{table_name}
                    ON {table_name};

                    CREATE TRIGGER cdc_trigger_{table_name}
                    AFTER INSERT OR UPDATE OR DELETE ON {table_name}
                    FOR EACH ROW EXECUTE FUNCTION cdc_capture_changes();
                """)

                conn.commit()
                logger.info(f"CDC enabled for table: {table_name}")

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to enable CDC for {table_name}: {e}")
            raise
        finally:
            self.db_pool.putconn(conn)

    def disable_cdc_for_table(self, table_name: str):
        """Disable CDC for a specific table"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # Update configuration
                cursor.execute("""
                    UPDATE cdc_table_config
                    SET enabled = FALSE, updated_at = CURRENT_TIMESTAMP
                    WHERE table_name = %s
                """, (table_name,))

                # Drop trigger
                cursor.execute(f"""
                    DROP TRIGGER IF EXISTS cdc_trigger_{table_name}
                    ON {table_name};
                """)

                conn.commit()
                logger.info(f"CDC disabled for table: {table_name}")

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to disable CDC for {table_name}: {e}")
        finally:
            self.db_pool.putconn(conn)

    def setup_default_tables(self):
        """Setup CDC for default MARTA tables"""
        table_pk_mapping = {
            'gtfs_stops': ['stop_id'],
            'gtfs_routes': ['route_id'],
            'gtfs_trips': ['trip_id'],
            'gtfs_stop_times': ['trip_id', 'stop_sequence'],
            'gtfs_calendar': ['service_id'],
            'unified_realtime_data': ['record_id'],
            'model_predictions': ['prediction_id'],
            'route_optimization_results': ['optimization_id'],
        }

        for table_name, pk_columns in table_pk_mapping.items():
            try:
                self.enable_cdc_for_table(table_name, pk_columns)
            except Exception as e:
                logger.warning(f"Could not enable CDC for {table_name}: {e}")

    def get_changes(
        self,
        table_name: Optional[str] = None,
        change_type: Optional[ChangeType] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """Get captured changes with optional filters"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                query = """
                    SELECT
                        change_id,
                        table_name,
                        change_type,
                        primary_key,
                        old_data,
                        new_data,
                        change_timestamp,
                        transaction_id,
                        user_name
                    FROM cdc_change_log
                    WHERE 1=1
                """
                params = []

                if table_name:
                    query += " AND table_name = %s"
                    params.append(table_name)

                if change_type:
                    query += " AND change_type = %s"
                    params.append(change_type.value)

                if since:
                    query += " AND change_timestamp >= %s"
                    params.append(since)

                if until:
                    query += " AND change_timestamp <= %s"
                    params.append(until)

                query += " ORDER BY change_timestamp DESC LIMIT %s"
                params.append(limit)

                cursor.execute(query, params)

                return [
                    {
                        'change_id': row[0],
                        'table_name': row[1],
                        'change_type': row[2],
                        'primary_key': row[3],
                        'old_data': row[4],
                        'new_data': row[5],
                        'change_timestamp': row[6].isoformat() if row[6] else None,
                        'transaction_id': row[7],
                        'user_name': row[8]
                    }
                    for row in cursor.fetchall()
                ]
        finally:
            self.db_pool.putconn(conn)

    def get_change_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of changes in the specified time period"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # Changes by table and type
                cursor.execute("""
                    SELECT
                        table_name,
                        change_type,
                        COUNT(*) as count
                    FROM cdc_change_log
                    WHERE change_timestamp >= NOW() - INTERVAL '%s hours'
                    GROUP BY table_name, change_type
                    ORDER BY table_name, change_type
                """, (hours,))

                changes_by_table = {}
                for row in cursor.fetchall():
                    table = row[0]
                    if table not in changes_by_table:
                        changes_by_table[table] = {}
                    changes_by_table[table][row[1]] = row[2]

                # Total changes
                cursor.execute("""
                    SELECT COUNT(*) FROM cdc_change_log
                    WHERE change_timestamp >= NOW() - INTERVAL '%s hours'
                """, (hours,))
                total_changes = cursor.fetchone()[0]

                # Changes per hour
                cursor.execute("""
                    SELECT
                        DATE_TRUNC('hour', change_timestamp) as hour,
                        COUNT(*) as count
                    FROM cdc_change_log
                    WHERE change_timestamp >= NOW() - INTERVAL '%s hours'
                    GROUP BY DATE_TRUNC('hour', change_timestamp)
                    ORDER BY hour
                """, (hours,))

                changes_per_hour = [
                    {
                        'hour': row[0].isoformat() if row[0] else None,
                        'count': row[1]
                    }
                    for row in cursor.fetchall()
                ]

                return {
                    'period_hours': hours,
                    'total_changes': total_changes,
                    'changes_by_table': changes_by_table,
                    'changes_per_hour': changes_per_hour
                }
        finally:
            self.db_pool.putconn(conn)

    def get_table_history(
        self,
        table_name: str,
        primary_key: Dict,
        limit: int = 100
    ) -> List[Dict]:
        """Get change history for a specific record"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        change_id,
                        change_type,
                        old_data,
                        new_data,
                        change_timestamp,
                        user_name
                    FROM cdc_change_log
                    WHERE table_name = %s
                      AND primary_key @> %s
                    ORDER BY change_timestamp DESC
                    LIMIT %s
                """, (table_name, json.dumps(primary_key), limit))

                return [
                    {
                        'change_id': row[0],
                        'change_type': row[1],
                        'old_data': row[2],
                        'new_data': row[3],
                        'change_timestamp': row[4].isoformat() if row[4] else None,
                        'user_name': row[5]
                    }
                    for row in cursor.fetchall()
                ]
        finally:
            self.db_pool.putconn(conn)

    def replay_changes(
        self,
        table_name: str,
        since: datetime,
        until: Optional[datetime] = None,
        target_table: Optional[str] = None
    ) -> int:
        """Replay changes to recreate state at a point in time"""
        target = target_table or f"{table_name}_replay"
        changes = self.get_changes(
            table_name=table_name,
            since=since,
            until=until,
            limit=100000
        )

        # Sort by timestamp ascending for replay
        changes.sort(key=lambda x: x['change_timestamp'])

        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                replayed = 0

                for change in changes:
                    if change['change_type'] == 'INSERT' and change['new_data']:
                        # Replay insert
                        columns = list(change['new_data'].keys())
                        values = list(change['new_data'].values())
                        placeholders = ', '.join(['%s'] * len(values))
                        cols_str = ', '.join(columns)

                        cursor.execute(f"""
                            INSERT INTO {target} ({cols_str})
                            VALUES ({placeholders})
                            ON CONFLICT DO NOTHING
                        """, values)
                        replayed += 1

                    elif change['change_type'] == 'UPDATE' and change['new_data']:
                        # Replay update
                        pk = change['primary_key']
                        updates = []
                        values = []
                        for k, v in change['new_data'].items():
                            if k not in pk:
                                updates.append(f"{k} = %s")
                                values.append(v)

                        where_clauses = []
                        for k, v in pk.items():
                            where_clauses.append(f"{k} = %s")
                            values.append(v)

                        if updates:
                            cursor.execute(f"""
                                UPDATE {target}
                                SET {', '.join(updates)}
                                WHERE {' AND '.join(where_clauses)}
                            """, values)
                            replayed += 1

                    elif change['change_type'] == 'DELETE':
                        # Replay delete
                        pk = change['primary_key']
                        where_clauses = []
                        values = []
                        for k, v in pk.items():
                            where_clauses.append(f"{k} = %s")
                            values.append(v)

                        cursor.execute(f"""
                            DELETE FROM {target}
                            WHERE {' AND '.join(where_clauses)}
                        """, values)
                        replayed += 1

                conn.commit()
                logger.info(f"Replayed {replayed} changes to {target}")
                return replayed

        except Exception as e:
            conn.rollback()
            logger.error(f"Error replaying changes: {e}")
            raise
        finally:
            self.db_pool.putconn(conn)

    def get_cdc_status(self) -> Dict[str, Any]:
        """Get CDC system status"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # Get enabled tables
                cursor.execute("""
                    SELECT table_name, enabled, capture_inserts,
                           capture_updates, capture_deletes, updated_at
                    FROM cdc_table_config
                    ORDER BY table_name
                """)

                tables = [
                    {
                        'table_name': row[0],
                        'enabled': row[1],
                        'capture_inserts': row[2],
                        'capture_updates': row[3],
                        'capture_deletes': row[4],
                        'updated_at': row[5].isoformat() if row[5] else None
                    }
                    for row in cursor.fetchall()
                ]

                # Get change log size
                cursor.execute("SELECT COUNT(*) FROM cdc_change_log")
                total_changes = cursor.fetchone()[0]

                # Get oldest change
                cursor.execute("""
                    SELECT MIN(change_timestamp) FROM cdc_change_log
                """)
                oldest = cursor.fetchone()[0]

                return {
                    'enabled_tables': len([t for t in tables if t['enabled']]),
                    'total_tables': len(tables),
                    'total_changes_captured': total_changes,
                    'oldest_change': oldest.isoformat() if oldest else None,
                    'tables': tables
                }
        finally:
            self.db_pool.putconn(conn)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    cdc = ChangeDataCapture()

    # Setup default tables
    print("Setting up CDC for default tables...")
    cdc.setup_default_tables()

    # Get status
    status = cdc.get_cdc_status()
    print(f"\nCDC Status:")
    print(f"  Enabled tables: {status['enabled_tables']}/{status['total_tables']}")
    print(f"  Total changes captured: {status['total_changes_captured']}")

    # Get change summary
    summary = cdc.get_change_summary(hours=24)
    print(f"\nChange Summary (last 24h):")
    print(f"  Total changes: {summary['total_changes']}")
    for table, changes in summary['changes_by_table'].items():
        print(f"  {table}: {changes}")
