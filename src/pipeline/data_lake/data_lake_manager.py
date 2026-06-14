#!/usr/bin/env python3
"""
Data Lake Manager - Multi-zone data lake architecture for MARTA
Manages raw, processed, and feature zones with metadata tracking
"""
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import gzip
import hashlib
import shutil
from pathlib import Path
import pandas as pd
import psycopg2
from psycopg2 import pool

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from config.settings import settings

logger = logging.getLogger(__name__)


class DataZone(Enum):
    RAW = "raw"
    PROCESSED = "processed"
    FEATURE = "feature"
    ARCHIVE = "archive"


class DataFormat(Enum):
    PARQUET = "parquet"
    CSV = "csv"
    JSON = "json"
    JSONL = "jsonl"
    GZIP = "gzip"


@dataclass
class DataAsset:
    """Represents a data asset in the data lake"""
    asset_id: str
    name: str
    zone: DataZone
    path: str
    format: DataFormat
    schema: Optional[Dict] = None
    row_count: int = 0
    size_bytes: int = 0
    checksum: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)
    lineage: Dict = field(default_factory=dict)


class DataLakeManager:
    """
    Manages the MARTA data lake with three zones:
    - Raw Zone: Incoming feeds as-is (immutable)
    - Processed Zone: Cleaned, validated, deduplicated data
    - Feature Zone: ML-ready features and aggregations
    """

    def __init__(
        self,
        base_path: str = "data/lake",
        db_pool: Optional[pool.ThreadedConnectionPool] = None
    ):
        self.base_path = base_path
        self.db_pool = db_pool or self._create_db_pool()

        # Create zone directories
        self._init_zones()
        self._init_metadata_tables()

        logger.info(f"DataLakeManager initialized at {base_path}")

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

    def _init_zones(self):
        """Initialize data lake zone directories"""
        for zone in DataZone:
            zone_path = os.path.join(self.base_path, zone.value)
            os.makedirs(zone_path, exist_ok=True)

        # Create standard subdirectories
        subdirs = {
            DataZone.RAW: ['gtfs_static', 'gtfs_realtime', 'weather', 'events', 'kpi'],
            DataZone.PROCESSED: ['gtfs', 'weather', 'events', 'unified'],
            DataZone.FEATURE: ['demand', 'delay', 'service', 'ml_training'],
            DataZone.ARCHIVE: ['2024', '2025', '2026']
        }

        for zone, dirs in subdirs.items():
            for subdir in dirs:
                path = os.path.join(self.base_path, zone.value, subdir)
                os.makedirs(path, exist_ok=True)

    def _init_metadata_tables(self):
        """Initialize metadata tracking tables"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    -- Data asset catalog
                    CREATE TABLE IF NOT EXISTS data_lake_catalog (
                        asset_id VARCHAR(64) PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        zone VARCHAR(50) NOT NULL,
                        path TEXT NOT NULL,
                        format VARCHAR(50),
                        schema_definition JSONB,
                        row_count BIGINT,
                        size_bytes BIGINT,
                        checksum VARCHAR(64),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata JSONB,
                        lineage JSONB
                    );

                    CREATE INDEX IF NOT EXISTS idx_catalog_zone
                        ON data_lake_catalog(zone);
                    CREATE INDEX IF NOT EXISTS idx_catalog_name
                        ON data_lake_catalog(name);

                    -- Data lineage tracking
                    CREATE TABLE IF NOT EXISTS data_lineage (
                        id SERIAL PRIMARY KEY,
                        source_asset_id VARCHAR(64),
                        target_asset_id VARCHAR(64) NOT NULL,
                        transformation_type VARCHAR(100),
                        transformation_params JSONB,
                        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        execution_duration_ms INTEGER,
                        records_input BIGINT,
                        records_output BIGINT,
                        metadata JSONB
                    );

                    CREATE INDEX IF NOT EXISTS idx_lineage_source
                        ON data_lineage(source_asset_id);
                    CREATE INDEX IF NOT EXISTS idx_lineage_target
                        ON data_lineage(target_asset_id);

                    -- Data quality scores by asset
                    CREATE TABLE IF NOT EXISTS data_lake_quality (
                        id SERIAL PRIMARY KEY,
                        asset_id VARCHAR(64) NOT NULL,
                        quality_score NUMERIC,
                        completeness_score NUMERIC,
                        validity_score NUMERIC,
                        consistency_score NUMERIC,
                        timeliness_score NUMERIC,
                        check_details JSONB,
                        checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE INDEX IF NOT EXISTS idx_lake_quality_asset
                        ON data_lake_quality(asset_id);

                    -- Zone statistics
                    CREATE TABLE IF NOT EXISTS data_lake_stats (
                        id SERIAL PRIMARY KEY,
                        zone VARCHAR(50) NOT NULL,
                        stat_date DATE NOT NULL,
                        total_assets INTEGER,
                        total_size_bytes BIGINT,
                        total_rows BIGINT,
                        assets_added INTEGER,
                        assets_updated INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(zone, stat_date)
                    );
                """)
                conn.commit()
        finally:
            self.db_pool.putconn(conn)

    def _generate_asset_id(self, name: str, zone: DataZone) -> str:
        """Generate unique asset ID"""
        content = f"{name}:{zone.value}:{datetime.now().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate MD5 checksum of a file"""
        hash_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def get_zone_path(self, zone: DataZone) -> str:
        """Get the path for a zone"""
        return os.path.join(self.base_path, zone.value)

    def ingest_to_raw(
        self,
        name: str,
        data: Union[pd.DataFrame, Dict, List, bytes, str],
        subdir: str = "misc",
        format: DataFormat = DataFormat.JSONL,
        metadata: Optional[Dict] = None
    ) -> DataAsset:
        """Ingest data into the raw zone (immutable)"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{name}_{timestamp}.{format.value}"
        if format == DataFormat.GZIP:
            filename += ".gz"

        file_path = os.path.join(
            self.base_path,
            DataZone.RAW.value,
            subdir,
            filename
        )

        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Write data based on type
        if isinstance(data, pd.DataFrame):
            if format == DataFormat.PARQUET:
                data.to_parquet(file_path, index=False)
            elif format == DataFormat.CSV:
                data.to_csv(file_path, index=False)
            elif format == DataFormat.JSONL:
                data.to_json(file_path, orient='records', lines=True)
            row_count = len(data)
        elif isinstance(data, (dict, list)):
            with open(file_path, 'w') as f:
                if format == DataFormat.JSONL and isinstance(data, list):
                    for item in data:
                        f.write(json.dumps(item) + '\n')
                else:
                    json.dump(data, f)
            row_count = len(data) if isinstance(data, list) else 1
        elif isinstance(data, bytes):
            mode = 'wb'
            if format == DataFormat.GZIP:
                with gzip.open(file_path, 'wb') as f:
                    f.write(data)
            else:
                with open(file_path, 'wb') as f:
                    f.write(data)
            row_count = 0
        else:
            with open(file_path, 'w') as f:
                f.write(str(data))
            row_count = 0

        # Create asset record
        asset = DataAsset(
            asset_id=self._generate_asset_id(name, DataZone.RAW),
            name=name,
            zone=DataZone.RAW,
            path=file_path,
            format=format,
            row_count=row_count,
            size_bytes=os.path.getsize(file_path),
            checksum=self._calculate_checksum(file_path),
            metadata=metadata or {}
        )

        self._save_asset_metadata(asset)
        logger.info(f"Ingested {name} to raw zone: {file_path}")

        return asset

    def process_to_zone(
        self,
        source_asset: DataAsset,
        name: str,
        target_zone: DataZone,
        transform_func: callable,
        subdir: str = "misc",
        format: DataFormat = DataFormat.PARQUET,
        metadata: Optional[Dict] = None
    ) -> DataAsset:
        """Process data from one zone to another with transformation"""
        start_time = datetime.now()

        # Load source data
        source_data = self.load_asset(source_asset)

        # Apply transformation
        processed_data = transform_func(source_data)

        # Determine output path
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{name}_{timestamp}.{format.value}"
        file_path = os.path.join(
            self.base_path,
            target_zone.value,
            subdir,
            filename
        )

        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Write processed data
        if isinstance(processed_data, pd.DataFrame):
            if format == DataFormat.PARQUET:
                processed_data.to_parquet(file_path, index=False)
            elif format == DataFormat.CSV:
                processed_data.to_csv(file_path, index=False)
            elif format == DataFormat.JSONL:
                processed_data.to_json(file_path, orient='records', lines=True)
            row_count = len(processed_data)
        else:
            with open(file_path, 'w') as f:
                json.dump(processed_data, f)
            row_count = len(processed_data) if isinstance(processed_data, list) else 1

        # Create asset record
        target_asset = DataAsset(
            asset_id=self._generate_asset_id(name, target_zone),
            name=name,
            zone=target_zone,
            path=file_path,
            format=format,
            row_count=row_count,
            size_bytes=os.path.getsize(file_path),
            checksum=self._calculate_checksum(file_path),
            metadata=metadata or {},
            lineage={
                'source_asset_id': source_asset.asset_id,
                'source_name': source_asset.name,
                'transformation': transform_func.__name__ if hasattr(transform_func, '__name__') else 'custom'
            }
        )

        self._save_asset_metadata(target_asset)

        # Record lineage
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        self._record_lineage(
            source_asset.asset_id,
            target_asset.asset_id,
            transform_func.__name__ if hasattr(transform_func, '__name__') else 'custom',
            duration_ms,
            source_asset.row_count,
            target_asset.row_count
        )

        logger.info(f"Processed {source_asset.name} -> {name} in {target_zone.value} zone")

        return target_asset

    def load_asset(self, asset: DataAsset) -> Union[pd.DataFrame, Dict, List]:
        """Load data from an asset"""
        if not os.path.exists(asset.path):
            raise FileNotFoundError(f"Asset file not found: {asset.path}")

        if asset.format == DataFormat.PARQUET:
            return pd.read_parquet(asset.path)
        elif asset.format == DataFormat.CSV:
            return pd.read_csv(asset.path)
        elif asset.format == DataFormat.JSONL:
            return pd.read_json(asset.path, lines=True)
        elif asset.format == DataFormat.JSON:
            with open(asset.path, 'r') as f:
                return json.load(f)
        elif asset.format == DataFormat.GZIP:
            with gzip.open(asset.path, 'rt') as f:
                return json.load(f)
        else:
            with open(asset.path, 'r') as f:
                return f.read()

    def _save_asset_metadata(self, asset: DataAsset):
        """Save asset metadata to database"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO data_lake_catalog
                    (asset_id, name, zone, path, format, schema_definition,
                     row_count, size_bytes, checksum, metadata, lineage)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (asset_id) DO UPDATE SET
                        row_count = EXCLUDED.row_count,
                        size_bytes = EXCLUDED.size_bytes,
                        checksum = EXCLUDED.checksum,
                        metadata = EXCLUDED.metadata,
                        lineage = EXCLUDED.lineage,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    asset.asset_id,
                    asset.name,
                    asset.zone.value,
                    asset.path,
                    asset.format.value,
                    json.dumps(asset.schema) if asset.schema else None,
                    asset.row_count,
                    asset.size_bytes,
                    asset.checksum,
                    json.dumps(asset.metadata),
                    json.dumps(asset.lineage)
                ))
                conn.commit()
        finally:
            self.db_pool.putconn(conn)

    def _record_lineage(
        self,
        source_id: str,
        target_id: str,
        transformation: str,
        duration_ms: float,
        records_in: int,
        records_out: int
    ):
        """Record data lineage"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO data_lineage
                    (source_asset_id, target_asset_id, transformation_type,
                     execution_duration_ms, records_input, records_output)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (source_id, target_id, transformation,
                      duration_ms, records_in, records_out))
                conn.commit()
        finally:
            self.db_pool.putconn(conn)

    def get_asset(self, asset_id: str) -> Optional[DataAsset]:
        """Get asset by ID"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT asset_id, name, zone, path, format, schema_definition,
                           row_count, size_bytes, checksum, created_at, updated_at,
                           metadata, lineage
                    FROM data_lake_catalog
                    WHERE asset_id = %s
                """, (asset_id,))
                row = cursor.fetchone()

                if not row:
                    return None

                return DataAsset(
                    asset_id=row[0],
                    name=row[1],
                    zone=DataZone(row[2]),
                    path=row[3],
                    format=DataFormat(row[4]) if row[4] else DataFormat.JSON,
                    schema=row[5],
                    row_count=row[6] or 0,
                    size_bytes=row[7] or 0,
                    checksum=row[8],
                    created_at=row[9],
                    updated_at=row[10],
                    metadata=row[11] or {},
                    lineage=row[12] or {}
                )
        finally:
            self.db_pool.putconn(conn)

    def list_assets(
        self,
        zone: Optional[DataZone] = None,
        name_pattern: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """List assets in the data lake"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                query = """
                    SELECT asset_id, name, zone, path, format,
                           row_count, size_bytes, created_at, updated_at
                    FROM data_lake_catalog
                    WHERE 1=1
                """
                params = []

                if zone:
                    query += " AND zone = %s"
                    params.append(zone.value)

                if name_pattern:
                    query += " AND name ILIKE %s"
                    params.append(f"%{name_pattern}%")

                query += " ORDER BY created_at DESC LIMIT %s"
                params.append(limit)

                cursor.execute(query, params)

                return [
                    {
                        'asset_id': row[0],
                        'name': row[1],
                        'zone': row[2],
                        'path': row[3],
                        'format': row[4],
                        'row_count': row[5],
                        'size_bytes': row[6],
                        'created_at': row[7].isoformat() if row[7] else None,
                        'updated_at': row[8].isoformat() if row[8] else None
                    }
                    for row in cursor.fetchall()
                ]
        finally:
            self.db_pool.putconn(conn)

    def get_zone_stats(self) -> Dict[str, Any]:
        """Get statistics for each zone"""
        stats = {}

        for zone in DataZone:
            zone_path = os.path.join(self.base_path, zone.value)
            total_size = 0
            file_count = 0

            for root, dirs, files in os.walk(zone_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)
                    file_count += 1

            stats[zone.value] = {
                'file_count': file_count,
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'path': zone_path
            }

        # Add database stats
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                for zone in DataZone:
                    cursor.execute("""
                        SELECT
                            COUNT(*) as assets,
                            COALESCE(SUM(row_count), 0) as total_rows
                        FROM data_lake_catalog
                        WHERE zone = %s
                    """, (zone.value,))
                    row = cursor.fetchone()
                    stats[zone.value]['catalog_assets'] = row[0]
                    stats[zone.value]['total_rows'] = row[1]
        finally:
            self.db_pool.putconn(conn)

        return stats

    def get_lineage_graph(self, asset_id: str) -> Dict[str, Any]:
        """Get lineage graph for an asset"""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # Get upstream lineage
                cursor.execute("""
                    WITH RECURSIVE upstream AS (
                        SELECT source_asset_id, target_asset_id, transformation_type, 1 as depth
                        FROM data_lineage
                        WHERE target_asset_id = %s

                        UNION ALL

                        SELECT dl.source_asset_id, dl.target_asset_id, dl.transformation_type, u.depth + 1
                        FROM data_lineage dl
                        JOIN upstream u ON dl.target_asset_id = u.source_asset_id
                        WHERE u.depth < 10
                    )
                    SELECT * FROM upstream
                """, (asset_id,))
                upstream = cursor.fetchall()

                # Get downstream lineage
                cursor.execute("""
                    WITH RECURSIVE downstream AS (
                        SELECT source_asset_id, target_asset_id, transformation_type, 1 as depth
                        FROM data_lineage
                        WHERE source_asset_id = %s

                        UNION ALL

                        SELECT dl.source_asset_id, dl.target_asset_id, dl.transformation_type, d.depth + 1
                        FROM data_lineage dl
                        JOIN downstream d ON dl.source_asset_id = d.target_asset_id
                        WHERE d.depth < 10
                    )
                    SELECT * FROM downstream
                """, (asset_id,))
                downstream = cursor.fetchall()

                return {
                    'asset_id': asset_id,
                    'upstream': [
                        {
                            'source': row[0],
                            'target': row[1],
                            'transformation': row[2],
                            'depth': row[3]
                        }
                        for row in upstream
                    ],
                    'downstream': [
                        {
                            'source': row[0],
                            'target': row[1],
                            'transformation': row[2],
                            'depth': row[3]
                        }
                        for row in downstream
                    ]
                }
        finally:
            self.db_pool.putconn(conn)

    def archive_old_assets(self, zone: DataZone, older_than_days: int = 90) -> int:
        """Move old assets to archive zone"""
        cutoff_date = datetime.now() - timedelta(days=older_than_days)
        archived_count = 0

        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # Get assets to archive
                cursor.execute("""
                    SELECT asset_id, path
                    FROM data_lake_catalog
                    WHERE zone = %s AND created_at < %s
                """, (zone.value, cutoff_date))

                for row in cursor.fetchall():
                    asset_id, old_path = row

                    if not os.path.exists(old_path):
                        continue

                    # Create archive path
                    year = datetime.now().strftime('%Y')
                    new_path = os.path.join(
                        self.base_path,
                        DataZone.ARCHIVE.value,
                        year,
                        os.path.basename(old_path)
                    )

                    os.makedirs(os.path.dirname(new_path), exist_ok=True)
                    shutil.move(old_path, new_path)

                    # Update catalog
                    cursor.execute("""
                        UPDATE data_lake_catalog
                        SET zone = %s, path = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE asset_id = %s
                    """, (DataZone.ARCHIVE.value, new_path, asset_id))

                    archived_count += 1

                conn.commit()
        finally:
            self.db_pool.putconn(conn)

        logger.info(f"Archived {archived_count} assets from {zone.value} zone")
        return archived_count


# Standard transformations
def clean_gtfs_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean GTFS data - remove nulls, validate coordinates"""
    # Remove rows with missing required fields
    required_cols = ['stop_id', 'stop_name', 'stop_lat', 'stop_lon']
    for col in required_cols:
        if col in df.columns:
            df = df.dropna(subset=[col])

    # Validate coordinates
    if 'stop_lat' in df.columns and 'stop_lon' in df.columns:
        df = df[
            (df['stop_lat'].between(33.5, 34.1)) &
            (df['stop_lon'].between(-84.8, -84.0))
        ]

    return df


def deduplicate_realtime(df: pd.DataFrame) -> pd.DataFrame:
    """Deduplicate realtime data keeping latest"""
    if 'timestamp' in df.columns:
        df = df.sort_values('timestamp', ascending=False)
        key_cols = [c for c in ['vehicle_id', 'trip_id', 'stop_id'] if c in df.columns]
        if key_cols:
            df = df.drop_duplicates(subset=key_cols, keep='first')
    return df


def create_ml_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create ML features from processed data"""
    if 'timestamp' in df.columns:
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.dayofweek
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)

        # Cyclical encoding
        import numpy as np
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        df['dow_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['dow_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)

    return df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    lake = DataLakeManager()

    # Show zone stats
    stats = lake.get_zone_stats()
    print("\nData Lake Statistics:")
    for zone, stat in stats.items():
        print(f"  {zone}:")
        print(f"    Files: {stat['file_count']}")
        print(f"    Size: {stat['total_size_mb']:.2f} MB")
        print(f"    Catalog assets: {stat.get('catalog_assets', 0)}")
