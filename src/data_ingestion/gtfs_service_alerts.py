#!/usr/bin/env python3
"""
GTFS-RT Service Alerts Processor
Processes and stores service alerts from MARTA GTFS-RT API
"""
import os
import sys
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
import requests
import psycopg2
from psycopg2 import pool
import json

try:
    from google.transit import gtfs_realtime_pb2
except ImportError:
    gtfs_realtime_pb2 = None
    print("Warning: gtfs-realtime-bindings not installed")

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import settings

logger = logging.getLogger(__name__)


class GTFSServiceAlertsProcessor:
    """Process GTFS-RT Service Alerts"""

    def __init__(self, db_pool: Optional[pool.ThreadedConnectionPool] = None):
        self.alerts_url = os.getenv(
            "MARTA_GTFS_RT_ALERTS_URL",
            "https://api.marta.io/gtfs-rt/alerts/alerts.pb"
        )
        self.api_key = os.getenv("MARTA_API_KEY")
        self.db_pool = db_pool or self._create_db_pool()
        self._init_tables()

        logger.info("GTFSServiceAlertsProcessor initialized")

    def _create_db_pool(self) -> pool.ThreadedConnectionPool:
        return pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=5,
            host=settings.DB_HOST,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            port=settings.DB_PORT
        )

    def _init_tables(self):
        """Initialize service alerts tables"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    -- Service alerts table
                    CREATE TABLE IF NOT EXISTS gtfs_service_alerts (
                        id SERIAL PRIMARY KEY,
                        alert_id VARCHAR(255) UNIQUE,
                        cause VARCHAR(100),
                        effect VARCHAR(100),

                        -- Active period
                        active_period_start TIMESTAMP,
                        active_period_end TIMESTAMP,

                        -- Header and description
                        header_text TEXT,
                        description_text TEXT,
                        url TEXT,

                        -- Severity
                        severity_level VARCHAR(50),

                        -- Affected entities (JSON)
                        informed_entities JSONB,
                        affected_routes TEXT[],
                        affected_stops TEXT[],
                        affected_trips TEXT[],
                        affected_agencies TEXT[],

                        -- Timestamps
                        fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE,

                        -- Metadata
                        raw_data JSONB
                    );

                    CREATE INDEX IF NOT EXISTS idx_alerts_active
                        ON gtfs_service_alerts(is_active);
                    CREATE INDEX IF NOT EXISTS idx_alerts_cause
                        ON gtfs_service_alerts(cause);
                    CREATE INDEX IF NOT EXISTS idx_alerts_effect
                        ON gtfs_service_alerts(effect);
                    CREATE INDEX IF NOT EXISTS idx_alerts_routes
                        ON gtfs_service_alerts USING GIN(affected_routes);

                    -- Alert history for analytics
                    CREATE TABLE IF NOT EXISTS gtfs_service_alerts_history (
                        id SERIAL PRIMARY KEY,
                        alert_id VARCHAR(255),
                        status VARCHAR(50),
                        cause VARCHAR(100),
                        effect VARCHAR(100),
                        header_text TEXT,
                        duration_minutes INTEGER,
                        affected_routes_count INTEGER,
                        affected_stops_count INTEGER,
                        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE INDEX IF NOT EXISTS idx_alert_history_date
                        ON gtfs_service_alerts_history(recorded_at);
                """)
                conn.commit()
        finally:
            self.db_pool.putconn(conn)

    def _get_text(self, translated_string) -> str:
        """Extract text from TranslatedString"""
        if not translated_string or not translated_string.translation:
            return ""

        for translation in translated_string.translation:
            if translation.language == 'en' or not translation.language:
                return translation.text

        return translated_string.translation[0].text if translated_string.translation else ""

    def _parse_cause(self, cause_enum) -> str:
        """Parse cause enum to string"""
        cause_map = {
            1: 'UNKNOWN_CAUSE',
            2: 'OTHER_CAUSE',
            3: 'TECHNICAL_PROBLEM',
            4: 'STRIKE',
            5: 'DEMONSTRATION',
            6: 'ACCIDENT',
            7: 'HOLIDAY',
            8: 'WEATHER',
            9: 'MAINTENANCE',
            10: 'CONSTRUCTION',
            11: 'POLICE_ACTIVITY',
            12: 'MEDICAL_EMERGENCY',
        }
        return cause_map.get(cause_enum, 'UNKNOWN_CAUSE')

    def _parse_effect(self, effect_enum) -> str:
        """Parse effect enum to string"""
        effect_map = {
            1: 'NO_SERVICE',
            2: 'REDUCED_SERVICE',
            3: 'SIGNIFICANT_DELAYS',
            4: 'DETOUR',
            5: 'ADDITIONAL_SERVICE',
            6: 'MODIFIED_SERVICE',
            7: 'OTHER_EFFECT',
            8: 'UNKNOWN_EFFECT',
            9: 'STOP_MOVED',
        }
        return effect_map.get(effect_enum, 'UNKNOWN_EFFECT')

    def _parse_severity(self, severity_enum) -> str:
        """Parse severity enum to string"""
        severity_map = {
            1: 'UNKNOWN_SEVERITY',
            2: 'INFO',
            3: 'WARNING',
            4: 'SEVERE',
        }
        return severity_map.get(severity_enum, 'INFO')

    def fetch_alerts(self) -> Optional[List[Dict]]:
        """Fetch service alerts from GTFS-RT API"""
        if not gtfs_realtime_pb2:
            logger.error("gtfs-realtime-bindings not available")
            return None

        try:
            headers = {}
            if self.api_key:
                headers['x-api-key'] = self.api_key

            response = requests.get(
                self.alerts_url,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)

            alerts = []

            for entity in feed.entity:
                if entity.HasField('alert'):
                    alert = entity.alert

                    # Parse active periods
                    active_start = None
                    active_end = None
                    if alert.active_period:
                        period = alert.active_period[0]
                        if period.start:
                            active_start = datetime.fromtimestamp(period.start)
                        if period.end:
                            active_end = datetime.fromtimestamp(period.end)

                    # Parse informed entities
                    affected_routes = []
                    affected_stops = []
                    affected_trips = []
                    affected_agencies = []
                    informed_entities = []

                    for ie in alert.informed_entity:
                        entity_dict = {}
                        if ie.HasField('agency_id'):
                            affected_agencies.append(ie.agency_id)
                            entity_dict['agency_id'] = ie.agency_id
                        if ie.HasField('route_id'):
                            affected_routes.append(ie.route_id)
                            entity_dict['route_id'] = ie.route_id
                        if ie.HasField('stop_id'):
                            affected_stops.append(ie.stop_id)
                            entity_dict['stop_id'] = ie.stop_id
                        if ie.HasField('trip'):
                            if ie.trip.trip_id:
                                affected_trips.append(ie.trip.trip_id)
                                entity_dict['trip_id'] = ie.trip.trip_id
                        informed_entities.append(entity_dict)

                    alert_data = {
                        'alert_id': entity.id,
                        'cause': self._parse_cause(alert.cause),
                        'effect': self._parse_effect(alert.effect),
                        'active_period_start': active_start,
                        'active_period_end': active_end,
                        'header_text': self._get_text(alert.header_text),
                        'description_text': self._get_text(alert.description_text),
                        'url': self._get_text(alert.url) if alert.HasField('url') else None,
                        'severity_level': self._parse_severity(
                            alert.severity_level if alert.HasField('severity_level') else 2
                        ),
                        'informed_entities': informed_entities,
                        'affected_routes': list(set(affected_routes)),
                        'affected_stops': list(set(affected_stops)),
                        'affected_trips': list(set(affected_trips)),
                        'affected_agencies': list(set(affected_agencies)),
                    }

                    alerts.append(alert_data)

            logger.info(f"Fetched {len(alerts)} service alerts")
            return alerts

        except Exception as e:
            logger.error(f"Error fetching service alerts: {e}")
            return None

    def store_alerts(self, alerts: List[Dict]) -> int:
        """Store service alerts in database"""
        if not alerts:
            return 0

        conn = self.db_pool.getconn()
        stored = 0

        try:
            with conn.cursor() as cursor:
                # Get current active alert IDs
                cursor.execute("""
                    SELECT alert_id FROM gtfs_service_alerts WHERE is_active = TRUE
                """)
                current_active = set(row[0] for row in cursor.fetchall())

                # New alert IDs from this fetch
                new_alert_ids = set()

                for alert in alerts:
                    new_alert_ids.add(alert['alert_id'])

                    cursor.execute("""
                        INSERT INTO gtfs_service_alerts (
                            alert_id, cause, effect,
                            active_period_start, active_period_end,
                            header_text, description_text, url, severity_level,
                            informed_entities, affected_routes, affected_stops,
                            affected_trips, affected_agencies,
                            is_active, last_seen_at
                        )
                        VALUES (
                            %(alert_id)s, %(cause)s, %(effect)s,
                            %(active_period_start)s, %(active_period_end)s,
                            %(header_text)s, %(description_text)s, %(url)s, %(severity_level)s,
                            %(informed_entities)s, %(affected_routes)s, %(affected_stops)s,
                            %(affected_trips)s, %(affected_agencies)s,
                            TRUE, CURRENT_TIMESTAMP
                        )
                        ON CONFLICT (alert_id) DO UPDATE SET
                            cause = EXCLUDED.cause,
                            effect = EXCLUDED.effect,
                            active_period_start = EXCLUDED.active_period_start,
                            active_period_end = EXCLUDED.active_period_end,
                            header_text = EXCLUDED.header_text,
                            description_text = EXCLUDED.description_text,
                            severity_level = EXCLUDED.severity_level,
                            is_active = TRUE,
                            last_seen_at = CURRENT_TIMESTAMP
                    """, {
                        **alert,
                        'informed_entities': json.dumps(alert['informed_entities']),
                        'affected_routes': alert['affected_routes'] or [],
                        'affected_stops': alert['affected_stops'] or [],
                        'affected_trips': alert['affected_trips'] or [],
                        'affected_agencies': alert['affected_agencies'] or [],
                    })
                    stored += 1

                # Mark alerts no longer present as inactive
                expired_alerts = current_active - new_alert_ids
                if expired_alerts:
                    cursor.execute("""
                        UPDATE gtfs_service_alerts
                        SET is_active = FALSE
                        WHERE alert_id = ANY(%s)
                    """, (list(expired_alerts),))

                    # Record in history
                    for alert_id in expired_alerts:
                        cursor.execute("""
                            INSERT INTO gtfs_service_alerts_history
                            (alert_id, status, cause, effect, header_text,
                             duration_minutes, affected_routes_count, affected_stops_count)
                            SELECT
                                alert_id, 'resolved', cause, effect, header_text,
                                EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - first_seen_at)) / 60,
                                COALESCE(array_length(affected_routes, 1), 0),
                                COALESCE(array_length(affected_stops, 1), 0)
                            FROM gtfs_service_alerts
                            WHERE alert_id = %s
                        """, (alert_id,))

                conn.commit()
                logger.info(f"Stored {stored} alerts, {len(expired_alerts)} expired")

        except Exception as e:
            logger.error(f"Error storing alerts: {e}")
            conn.rollback()

        finally:
            self.db_pool.putconn(conn)

        return stored

    def get_active_alerts(self) -> List[Dict]:
        """Get currently active service alerts"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        alert_id, cause, effect, severity_level,
                        header_text, description_text,
                        affected_routes, affected_stops,
                        active_period_start, active_period_end,
                        first_seen_at
                    FROM gtfs_service_alerts
                    WHERE is_active = TRUE
                    ORDER BY
                        CASE severity_level
                            WHEN 'SEVERE' THEN 1
                            WHEN 'WARNING' THEN 2
                            ELSE 3
                        END,
                        first_seen_at DESC
                """)

                return [
                    {
                        'alert_id': row[0],
                        'cause': row[1],
                        'effect': row[2],
                        'severity': row[3],
                        'header': row[4],
                        'description': row[5],
                        'affected_routes': row[6] or [],
                        'affected_stops': row[7] or [],
                        'start': row[8].isoformat() if row[8] else None,
                        'end': row[9].isoformat() if row[9] else None,
                        'first_seen': row[10].isoformat() if row[10] else None
                    }
                    for row in cursor.fetchall()
                ]
        finally:
            self.db_pool.putconn(conn)

    def get_alert_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get alert statistics for analysis"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # Current active alerts
                cursor.execute("""
                    SELECT COUNT(*), SUM(array_length(affected_routes, 1))
                    FROM gtfs_service_alerts WHERE is_active = TRUE
                """)
                active = cursor.fetchone()

                # Historical statistics
                cursor.execute("""
                    SELECT
                        cause,
                        COUNT(*) as count,
                        AVG(duration_minutes) as avg_duration
                    FROM gtfs_service_alerts_history
                    WHERE recorded_at >= NOW() - INTERVAL '%s days'
                    GROUP BY cause
                    ORDER BY count DESC
                """, (days,))
                by_cause = [
                    {'cause': r[0], 'count': r[1], 'avg_duration_min': float(r[2]) if r[2] else 0}
                    for r in cursor.fetchall()
                ]

                return {
                    'active_alerts': active[0] or 0,
                    'affected_routes_count': active[1] or 0,
                    'last_30_days_by_cause': by_cause
                }
        finally:
            self.db_pool.putconn(conn)

    def run_ingestion(self) -> Dict[str, Any]:
        """Run complete service alerts ingestion"""
        alerts = self.fetch_alerts()
        if alerts is None:
            return {'success': False, 'error': 'Failed to fetch alerts'}

        stored = self.store_alerts(alerts)
        active = self.get_active_alerts()

        return {
            'success': True,
            'fetched': len(alerts),
            'stored': stored,
            'active_count': len(active)
        }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    processor = GTFSServiceAlertsProcessor()
    result = processor.run_ingestion()

    print(f"\nService Alerts Ingestion:")
    print(f"  Success: {result['success']}")
    print(f"  Fetched: {result.get('fetched', 0)}")
    print(f"  Active: {result.get('active_count', 0)}")

    # Show active alerts
    alerts = processor.get_active_alerts()
    if alerts:
        print("\nActive Alerts:")
        for alert in alerts[:5]:
            print(f"  [{alert['severity']}] {alert['header'][:50]}...")
