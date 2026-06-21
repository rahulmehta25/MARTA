#!/usr/bin/env python3
"""
Data Quality Monitor - Comprehensive data quality checks for MARTA data pipeline
Includes completeness, freshness, schema validation, and anomaly detection
"""
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import statistics
import psycopg2
from psycopg2 import pool

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from config.settings import settings

logger = logging.getLogger(__name__)


class QualityCheckType(Enum):
    COMPLETENESS = "completeness"
    FRESHNESS = "freshness"
    SCHEMA = "schema"
    UNIQUENESS = "uniqueness"
    REFERENTIAL = "referential"
    RANGE = "range"
    ANOMALY = "anomaly"
    CUSTOM = "custom"


class QualityStatus(Enum):
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    ERROR = "error"


@dataclass
class QualityCheckResult:
    """Result of a data quality check"""
    check_name: str
    check_type: QualityCheckType
    table_name: str
    status: QualityStatus
    metric_value: float
    threshold: float
    message: str
    details: Optional[Dict] = None
    checked_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            'check_name': self.check_name,
            'check_type': self.check_type.value,
            'table_name': self.table_name,
            'status': self.status.value,
            'metric_value': self.metric_value,
            'threshold': self.threshold,
            'message': self.message,
            'details': self.details,
            'checked_at': self.checked_at.isoformat()
        }


@dataclass
class QualityCheck:
    """Data quality check definition"""
    name: str
    check_type: QualityCheckType
    table_name: str
    check_function: Callable
    threshold: float  # Threshold for pass/warning/fail
    warning_threshold: Optional[float] = None  # Optional warning threshold
    enabled: bool = True
    description: Optional[str] = None
    metadata: Optional[Dict] = None


class DataQualityMonitor:
    """
    Comprehensive data quality monitoring system
    Performs completeness, freshness, schema, and anomaly checks
    """

    def __init__(self, db_pool: Optional[pool.ThreadedConnectionPool] = None):
        self.checks: Dict[str, QualityCheck] = {}
        self.db_pool = db_pool or self._create_db_pool()
        self._init_quality_tables()
        self._register_default_checks()

        logger.info("DataQualityMonitor initialized")

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

    def _init_quality_tables(self):
        """Initialize data quality tracking tables"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    -- Data quality check results
                    CREATE TABLE IF NOT EXISTS data_quality_metrics (
                        id SERIAL PRIMARY KEY,
                        check_name VARCHAR(255) NOT NULL,
                        check_type VARCHAR(50) NOT NULL,
                        table_name VARCHAR(255) NOT NULL,
                        status VARCHAR(20) NOT NULL,
                        metric_value NUMERIC,
                        threshold NUMERIC,
                        message TEXT,
                        details JSONB,
                        check_timestamp TIMESTAMP NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE INDEX IF NOT EXISTS idx_dq_metrics_check_name
                        ON data_quality_metrics(check_name);
                    CREATE INDEX IF NOT EXISTS idx_dq_metrics_table
                        ON data_quality_metrics(table_name);
                    CREATE INDEX IF NOT EXISTS idx_dq_metrics_status
                        ON data_quality_metrics(status);
                    CREATE INDEX IF NOT EXISTS idx_dq_metrics_timestamp
                        ON data_quality_metrics(check_timestamp);

                    -- Data quality alerts
                    CREATE TABLE IF NOT EXISTS data_quality_alerts (
                        id SERIAL PRIMARY KEY,
                        check_name VARCHAR(255) NOT NULL,
                        table_name VARCHAR(255) NOT NULL,
                        severity VARCHAR(20) NOT NULL,
                        message TEXT,
                        details JSONB,
                        acknowledged BOOLEAN DEFAULT FALSE,
                        acknowledged_by VARCHAR(255),
                        acknowledged_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE INDEX IF NOT EXISTS idx_dq_alerts_severity
                        ON data_quality_alerts(severity);
                    CREATE INDEX IF NOT EXISTS idx_dq_alerts_acknowledged
                        ON data_quality_alerts(acknowledged);

                    -- Table statistics for anomaly detection
                    CREATE TABLE IF NOT EXISTS table_statistics (
                        id SERIAL PRIMARY KEY,
                        table_name VARCHAR(255) NOT NULL,
                        stat_date DATE NOT NULL,
                        row_count BIGINT,
                        avg_row_size_bytes NUMERIC,
                        null_percentages JSONB,
                        column_stats JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(table_name, stat_date)
                    );

                    CREATE INDEX IF NOT EXISTS idx_table_stats_table
                        ON table_statistics(table_name);
                """)
                conn.commit()
        finally:
            self.db_pool.putconn(conn)

    def _register_default_checks(self):
        """Register default quality checks for MARTA tables"""

        # GTFS Static Completeness Checks
        self.register_check(QualityCheck(
            name="gtfs_stops_completeness",
            check_type=QualityCheckType.COMPLETENESS,
            table_name="gtfs_stops",
            check_function=self._check_required_columns,
            threshold=0.99,
            description="Check that required stop columns are populated"
        ))

        self.register_check(QualityCheck(
            name="gtfs_routes_completeness",
            check_type=QualityCheckType.COMPLETENESS,
            table_name="gtfs_routes",
            check_function=self._check_required_columns,
            threshold=0.99,
            description="Check that required route columns are populated"
        ))

        # Freshness Checks
        self.register_check(QualityCheck(
            name="vehicle_positions_freshness",
            check_type=QualityCheckType.FRESHNESS,
            table_name="gtfs_vehicle_positions",
            check_function=self._check_data_freshness,
            threshold=300,  # 5 minutes in seconds
            warning_threshold=120,
            description="Check vehicle positions are updated within 5 minutes"
        ))

        self.register_check(QualityCheck(
            name="trip_updates_freshness",
            check_type=QualityCheckType.FRESHNESS,
            table_name="gtfs_trip_updates",
            check_function=self._check_data_freshness,
            threshold=300,
            warning_threshold=120,
            description="Check trip updates are within 5 minutes"
        ))

        # Referential Integrity Checks
        self.register_check(QualityCheck(
            name="trip_route_reference",
            check_type=QualityCheckType.REFERENTIAL,
            table_name="gtfs_trips",
            check_function=self._check_referential_integrity,
            threshold=0.99,
            description="Check trips reference valid routes"
        ))

        # Range Checks
        self.register_check(QualityCheck(
            name="stop_coordinates_range",
            check_type=QualityCheckType.RANGE,
            table_name="gtfs_stops",
            check_function=self._check_coordinate_range,
            threshold=1.0,
            description="Check stop coordinates are within Atlanta area"
        ))

        # Anomaly Detection
        self.register_check(QualityCheck(
            name="vehicle_positions_volume",
            check_type=QualityCheckType.ANOMALY,
            table_name="gtfs_vehicle_positions",
            check_function=self._check_volume_anomaly,
            threshold=3.0,  # Standard deviations
            description="Check for unusual volume of vehicle positions"
        ))

    def register_check(self, check: QualityCheck):
        """Register a quality check"""
        self.checks[check.name] = check
        logger.debug(f"Registered quality check: {check.name}")

    def _check_required_columns(
        self,
        table_name: str,
        conn,
        **kwargs
    ) -> QualityCheckResult:
        """Check completeness of required columns"""
        required_columns = {
            'gtfs_stops': ['stop_id', 'stop_name', 'stop_lat', 'stop_lon'],
            'gtfs_routes': ['route_id', 'route_short_name', 'route_type'],
            'gtfs_trips': ['trip_id', 'route_id', 'service_id'],
        }

        columns = required_columns.get(table_name, ['id'])

        with conn.cursor() as cursor:
            # Get total row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_rows = cursor.fetchone()[0]

            if total_rows == 0:
                return QualityCheckResult(
                    check_name=f"{table_name}_completeness",
                    check_type=QualityCheckType.COMPLETENESS,
                    table_name=table_name,
                    status=QualityStatus.WARNING,
                    metric_value=0,
                    threshold=0.99,
                    message=f"Table {table_name} is empty",
                    details={'total_rows': 0}
                )

            # Check null percentages for each column
            null_counts = {}
            for col in columns:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM {table_name}
                    WHERE {col} IS NULL
                """)
                null_counts[col] = cursor.fetchone()[0]

            total_nulls = sum(null_counts.values())
            completeness = 1 - (total_nulls / (total_rows * len(columns)))

            status = QualityStatus.PASSED
            if completeness < 0.99:
                status = QualityStatus.WARNING
            if completeness < 0.95:
                status = QualityStatus.FAILED

            return QualityCheckResult(
                check_name=f"{table_name}_completeness",
                check_type=QualityCheckType.COMPLETENESS,
                table_name=table_name,
                status=status,
                metric_value=completeness,
                threshold=0.99,
                message=f"Completeness: {completeness:.2%}",
                details={
                    'total_rows': total_rows,
                    'null_counts': null_counts,
                    'columns_checked': columns
                }
            )

    def _check_data_freshness(
        self,
        table_name: str,
        conn,
        timestamp_column: str = "timestamp",
        **kwargs
    ) -> QualityCheckResult:
        """Check data freshness - time since last update"""
        check = kwargs.get('check')
        threshold = check.threshold if check else 300

        with conn.cursor() as cursor:
            # Check if table exists and has data
            cursor.execute(f"""
                SELECT MAX({timestamp_column})
                FROM {table_name}
            """)
            result = cursor.fetchone()

            if not result or not result[0]:
                return QualityCheckResult(
                    check_name=f"{table_name}_freshness",
                    check_type=QualityCheckType.FRESHNESS,
                    table_name=table_name,
                    status=QualityStatus.WARNING,
                    metric_value=float('inf'),
                    threshold=threshold,
                    message=f"No data found in {table_name}",
                    details={}
                )

            last_update = result[0]
            age_seconds = (datetime.now() - last_update).total_seconds()

            status = QualityStatus.PASSED
            if check and check.warning_threshold and age_seconds > check.warning_threshold:
                status = QualityStatus.WARNING
            if age_seconds > threshold:
                status = QualityStatus.FAILED

            return QualityCheckResult(
                check_name=f"{table_name}_freshness",
                check_type=QualityCheckType.FRESHNESS,
                table_name=table_name,
                status=status,
                metric_value=age_seconds,
                threshold=threshold,
                message=f"Data age: {age_seconds:.0f} seconds",
                details={
                    'last_update': last_update.isoformat(),
                    'age_seconds': age_seconds
                }
            )

    def _check_referential_integrity(
        self,
        table_name: str,
        conn,
        **kwargs
    ) -> QualityCheckResult:
        """Check referential integrity between tables"""
        references = {
            'gtfs_trips': ('route_id', 'gtfs_routes', 'route_id'),
            'gtfs_stop_times': ('trip_id', 'gtfs_trips', 'trip_id'),
        }

        if table_name not in references:
            return QualityCheckResult(
                check_name=f"{table_name}_referential",
                check_type=QualityCheckType.REFERENTIAL,
                table_name=table_name,
                status=QualityStatus.PASSED,
                metric_value=1.0,
                threshold=0.99,
                message="No referential checks defined",
                details={}
            )

        fk_col, ref_table, ref_col = references[table_name]

        with conn.cursor() as cursor:
            # Count orphan records
            cursor.execute(f"""
                SELECT COUNT(*)
                FROM {table_name} t
                LEFT JOIN {ref_table} r ON t.{fk_col} = r.{ref_col}
                WHERE t.{fk_col} IS NOT NULL AND r.{ref_col} IS NULL
            """)
            orphan_count = cursor.fetchone()[0]

            cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {fk_col} IS NOT NULL")
            total_refs = cursor.fetchone()[0]

            if total_refs == 0:
                integrity = 1.0
            else:
                integrity = 1 - (orphan_count / total_refs)

            status = QualityStatus.PASSED
            if integrity < 0.99:
                status = QualityStatus.WARNING
            if integrity < 0.95:
                status = QualityStatus.FAILED

            return QualityCheckResult(
                check_name=f"{table_name}_referential",
                check_type=QualityCheckType.REFERENTIAL,
                table_name=table_name,
                status=status,
                metric_value=integrity,
                threshold=0.99,
                message=f"Referential integrity: {integrity:.2%}",
                details={
                    'orphan_count': orphan_count,
                    'total_references': total_refs,
                    'reference_table': ref_table
                }
            )

    def _check_coordinate_range(
        self,
        table_name: str,
        conn,
        **kwargs
    ) -> QualityCheckResult:
        """Check that coordinates are within expected range (Atlanta area)"""
        # Atlanta bounding box (approximate)
        min_lat, max_lat = 33.5, 34.1
        min_lon, max_lon = -84.8, -84.0

        with conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN stop_lat < {min_lat} OR stop_lat > {max_lat}
                             OR stop_lon < {min_lon} OR stop_lon > {max_lon}
                        THEN 1 ELSE 0 END) as out_of_range
                FROM {table_name}
                WHERE stop_lat IS NOT NULL AND stop_lon IS NOT NULL
            """)
            row = cursor.fetchone()
            total = row[0]
            out_of_range = row[1]

            if total == 0:
                validity = 1.0
            else:
                validity = 1 - (out_of_range / total)

            status = QualityStatus.PASSED if validity >= 1.0 else QualityStatus.FAILED

            return QualityCheckResult(
                check_name=f"{table_name}_coordinates",
                check_type=QualityCheckType.RANGE,
                table_name=table_name,
                status=status,
                metric_value=validity,
                threshold=1.0,
                message=f"Coordinate validity: {validity:.2%}",
                details={
                    'total_stops': total,
                    'out_of_range': out_of_range,
                    'bounding_box': {
                        'min_lat': min_lat, 'max_lat': max_lat,
                        'min_lon': min_lon, 'max_lon': max_lon
                    }
                }
            )

    def _check_volume_anomaly(
        self,
        table_name: str,
        conn,
        **kwargs
    ) -> QualityCheckResult:
        """Detect anomalies in data volume using statistical analysis"""
        check = kwargs.get('check')
        std_threshold = check.threshold if check else 3.0

        with conn.cursor() as cursor:
            # Get hourly record counts for the last 7 days
            cursor.execute(f"""
                SELECT
                    DATE_TRUNC('hour', created_at) as hour,
                    COUNT(*) as count
                FROM {table_name}
                WHERE created_at >= NOW() - INTERVAL '7 days'
                GROUP BY DATE_TRUNC('hour', created_at)
                ORDER BY hour
            """)
            rows = cursor.fetchall()

            if len(rows) < 24:  # Need at least 24 hours of data
                return QualityCheckResult(
                    check_name=f"{table_name}_volume",
                    check_type=QualityCheckType.ANOMALY,
                    table_name=table_name,
                    status=QualityStatus.PASSED,
                    metric_value=0,
                    threshold=std_threshold,
                    message="Insufficient data for anomaly detection",
                    details={'data_points': len(rows)}
                )

            counts = [r[1] for r in rows]
            mean = statistics.mean(counts)
            std = statistics.stdev(counts) if len(counts) > 1 else 0

            # Get latest hour's count
            cursor.execute(f"""
                SELECT COUNT(*)
                FROM {table_name}
                WHERE created_at >= DATE_TRUNC('hour', NOW())
            """)
            current_count = cursor.fetchone()[0]

            # Calculate z-score
            z_score = (current_count - mean) / std if std > 0 else 0

            status = QualityStatus.PASSED
            if abs(z_score) > 2:
                status = QualityStatus.WARNING
            if abs(z_score) > std_threshold:
                status = QualityStatus.FAILED

            return QualityCheckResult(
                check_name=f"{table_name}_volume",
                check_type=QualityCheckType.ANOMALY,
                table_name=table_name,
                status=status,
                metric_value=abs(z_score),
                threshold=std_threshold,
                message=f"Volume z-score: {z_score:.2f}",
                details={
                    'current_hour_count': current_count,
                    'historical_mean': mean,
                    'historical_std': std,
                    'z_score': z_score
                }
            )

    def run_check(self, check_name: str) -> Optional[QualityCheckResult]:
        """Run a specific quality check"""
        if check_name not in self.checks:
            logger.error(f"Check not found: {check_name}")
            return None

        check = self.checks[check_name]
        if not check.enabled:
            logger.info(f"Check {check_name} is disabled, skipping")
            return None

        conn = self.db_pool.getconn()
        try:
            result = check.check_function(
                check.table_name,
                conn,
                check=check
            )

            # Save result to database
            self._save_result(result)

            # Create alert if failed
            if result.status in [QualityStatus.FAILED, QualityStatus.ERROR]:
                self._create_alert(result)

            return result

        except Exception as e:
            logger.error(f"Error running check {check_name}: {e}")
            result = QualityCheckResult(
                check_name=check_name,
                check_type=check.check_type,
                table_name=check.table_name,
                status=QualityStatus.ERROR,
                metric_value=-1,
                threshold=check.threshold,
                message=f"Check execution error: {str(e)}",
                details={'error': str(e)}
            )
            self._save_result(result)
            return result

        finally:
            self.db_pool.putconn(conn)

    def run_all_checks(self) -> List[QualityCheckResult]:
        """Run all enabled quality checks"""
        results = []

        for check_name in self.checks:
            result = self.run_check(check_name)
            if result:
                results.append(result)

        return results

    def _save_result(self, result: QualityCheckResult):
        """Save quality check result to database"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO data_quality_metrics
                    (check_name, check_type, table_name, status, metric_value,
                     threshold, message, details, check_timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    result.check_name,
                    result.check_type.value,
                    result.table_name,
                    result.status.value,
                    result.metric_value,
                    result.threshold,
                    result.message,
                    json.dumps(result.details) if result.details else None,
                    result.checked_at
                ))
                conn.commit()
        finally:
            self.db_pool.putconn(conn)

    def _create_alert(self, result: QualityCheckResult):
        """Create alert for failed quality check"""
        severity = 'critical' if result.status == QualityStatus.ERROR else 'warning'

        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO data_quality_alerts
                    (check_name, table_name, severity, message, details)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    result.check_name,
                    result.table_name,
                    severity,
                    result.message,
                    json.dumps(result.details) if result.details else None
                ))
                conn.commit()
        finally:
            self.db_pool.putconn(conn)

        logger.warning(f"Quality alert: {result.check_name} - {result.message}")

    def get_quality_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of quality check results"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        status,
                        COUNT(*) as count
                    FROM data_quality_metrics
                    WHERE check_timestamp >= NOW() - INTERVAL '%s hours'
                    GROUP BY status
                """, (hours,))
                status_counts = dict(cursor.fetchall())

                cursor.execute("""
                    SELECT
                        check_name,
                        status,
                        metric_value,
                        message,
                        check_timestamp
                    FROM data_quality_metrics
                    WHERE check_timestamp = (
                        SELECT MAX(check_timestamp)
                        FROM data_quality_metrics m2
                        WHERE m2.check_name = data_quality_metrics.check_name
                    )
                    ORDER BY
                        CASE WHEN status = 'failed' THEN 0
                             WHEN status = 'error' THEN 1
                             WHEN status = 'warning' THEN 2
                             ELSE 3 END
                """)

                latest_results = [
                    {
                        'check_name': r[0],
                        'status': r[1],
                        'metric_value': float(r[2]) if r[2] else None,
                        'message': r[3],
                        'checked_at': r[4].isoformat() if r[4] else None
                    }
                    for r in cursor.fetchall()
                ]

                # Unacknowledged alerts
                cursor.execute("""
                    SELECT COUNT(*) FROM data_quality_alerts
                    WHERE acknowledged = FALSE
                """)
                unacknowledged_alerts = cursor.fetchone()[0]

                return {
                    'period_hours': hours,
                    'status_counts': status_counts,
                    'total_checks': sum(status_counts.values()),
                    'pass_rate': status_counts.get('passed', 0) / max(sum(status_counts.values()), 1),
                    'latest_results': latest_results,
                    'unacknowledged_alerts': unacknowledged_alerts
                }
        finally:
            self.db_pool.putconn(conn)

    def acknowledge_alerts(self, alert_ids: List[int], acknowledged_by: str):
        """Acknowledge quality alerts"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE data_quality_alerts
                    SET acknowledged = TRUE,
                        acknowledged_by = %s,
                        acknowledged_at = NOW()
                    WHERE id = ANY(%s)
                """, (acknowledged_by, alert_ids))
                conn.commit()
        finally:
            self.db_pool.putconn(conn)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    monitor = DataQualityMonitor()

    # Run all checks
    print("\nRunning all quality checks...")
    results = monitor.run_all_checks()

    for result in results:
        status_icon = {
            QualityStatus.PASSED: "OK",
            QualityStatus.WARNING: "WARN",
            QualityStatus.FAILED: "FAIL",
            QualityStatus.ERROR: "ERR"
        }[result.status]

        print(f"  [{status_icon}] {result.check_name}: {result.message}")

    # Get summary
    summary = monitor.get_quality_summary()
    print(f"\nQuality Summary (last 24h):")
    print(f"  Pass rate: {summary['pass_rate']:.1%}")
    print(f"  Unacknowledged alerts: {summary['unacknowledged_alerts']}")
