"""MARTA GTFS-realtime ingestion worker.

Pulls MARTA's GTFS-realtime VehiclePositions and TripUpdates feeds, decodes
the protobuf payload, and writes normalized rows into `vehicle_positions` and
`arrivals`.

Run on Cloud Scheduler -> Cloud Run every 30 seconds. Idempotent: duplicate
trip-update emissions are deduped by (gtfs_trip_id, stop_id, observed_at).

Environment:
    DATABASE_URL                Cloud SQL DSN pointing at the marta DB
    MARTA_VEHICLE_FEED_URL      default https://gtfs-rt.itsmarta.com/vehiclePositions.pb
    MARTA_TRIPUPDATES_FEED_URL  default https://gtfs-rt.itsmarta.com/tripUpdates.pb
    INGEST_TIMEOUT_SECONDS      HTTP timeout (default 20)
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Iterable, Optional

import asyncpg
import httpx
from google.transit import gtfs_realtime_pb2

log = logging.getLogger("marta.ingest")
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))

VEHICLE_FEED = os.environ.get(
    "MARTA_VEHICLE_FEED_URL", "https://gtfs-rt.itsmarta.com/vehiclePositions.pb"
)
TRIP_FEED = os.environ.get(
    "MARTA_TRIPUPDATES_FEED_URL", "https://gtfs-rt.itsmarta.com/tripUpdates.pb"
)
HTTP_TIMEOUT = int(os.environ.get("INGEST_TIMEOUT_SECONDS", "20"))


def _normalize_dsn(dsn: str) -> str:
    if dsn.startswith("postgresql+asyncpg://"):
        return "postgresql://" + dsn[len("postgresql+asyncpg://"):]
    return dsn


async def _fetch_feed(url: str) -> gtfs_realtime_pb2.FeedMessage:
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        res = await client.get(url)
        res.raise_for_status()
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(res.content)
        return feed


def _ts(value: int) -> datetime:
    return datetime.fromtimestamp(value, tz=timezone.utc)


async def _insert_vehicle_positions(
    conn: asyncpg.Connection, feed: gtfs_realtime_pb2.FeedMessage
) -> int:
    rows: list[tuple] = []
    for ent in feed.entity:
        if not ent.HasField("vehicle"):
            continue
        v = ent.vehicle
        vehicle_id = v.vehicle.id or ent.id or ""
        if not vehicle_id:
            continue
        observed = _ts(v.timestamp) if v.timestamp else datetime.now(tz=timezone.utc)
        rows.append(
            (
                vehicle_id,
                v.trip.route_id or None,
                v.trip.trip_id or None,
                v.position.latitude,
                v.position.longitude,
                v.position.bearing if v.position.HasField("bearing") else None,
                v.position.speed if v.position.HasField("speed") else None,
                gtfs_realtime_pb2.VehiclePosition.OccupancyStatus.Name(v.occupancy_status)
                if v.HasField("occupancy_status")
                else None,
                observed,
            )
        )

    if not rows:
        return 0

    await conn.executemany(
        """
        INSERT INTO vehicle_positions
            (gtfs_vehicle_id, gtfs_route_id, gtfs_trip_id, lat, lon,
             bearing, speed, occupancy_status, observed_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
        """,
        rows,
    )
    return len(rows)


async def _insert_arrivals(
    conn: asyncpg.Connection, feed: gtfs_realtime_pb2.FeedMessage
) -> int:
    stops_map = {
        r["gtfs_stop_id"]: r["id"]
        for r in await conn.fetch("SELECT id, gtfs_stop_id FROM stops")
    }

    rows: list[tuple] = []
    for ent in feed.entity:
        if not ent.HasField("trip_update"):
            continue
        tu = ent.trip_update
        trip_id = tu.trip.trip_id or None
        for stu in tu.stop_time_update:
            stop_pk = stops_map.get(stu.stop_id)
            if stop_pk is None:
                continue
            scheduled: Optional[datetime] = None
            predicted: Optional[datetime] = None
            delay: Optional[int] = None
            if stu.HasField("departure"):
                if stu.departure.time:
                    predicted = _ts(stu.departure.time)
                if stu.departure.HasField("delay"):
                    delay = stu.departure.delay
            elif stu.HasField("arrival"):
                if stu.arrival.time:
                    predicted = _ts(stu.arrival.time)
                if stu.arrival.HasField("delay"):
                    delay = stu.arrival.delay
            if predicted is None and delay is None:
                continue
            rows.append((stop_pk, trip_id, scheduled or predicted, predicted, None, delay))

    if not rows:
        return 0

    await conn.executemany(
        """
        INSERT INTO arrivals
            (stop_id, gtfs_trip_id, scheduled_time, predicted_time, actual_time, delay_seconds)
        VALUES ($1,$2,$3,$4,$5,$6)
        """,
        rows,
    )
    return len(rows)


async def ingest_once() -> dict:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL not set")

    pool = await asyncpg.create_pool(dsn=_normalize_dsn(dsn), min_size=1, max_size=3)
    try:
        vehicle_feed, trip_feed = await asyncio.gather(
            _fetch_feed(VEHICLE_FEED),
            _fetch_feed(TRIP_FEED),
        )
        async with pool.acquire() as conn:
            async with conn.transaction():
                vp = await _insert_vehicle_positions(conn, vehicle_feed)
                arr = await _insert_arrivals(conn, trip_feed)
        log.info("ingest cycle complete: vehicle_positions=%s arrivals=%s", vp, arr)
        return {"vehicle_positions": vp, "arrivals": arr}
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(ingest_once())
