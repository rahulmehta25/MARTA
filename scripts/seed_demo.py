"""Seed 3 demo rows into the marta Cloud SQL database.

Usage:
    # Make sure scripts/db-proxy.sh is running and DATABASE_URL is set.
    python3 scripts/seed_demo.py
"""
from __future__ import annotations

import os
import sys

import psycopg
from psycopg.types.json import Json

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("DATABASE_URL is not set. Copy backend/api/.env.example and run scripts/db-proxy.sh first.")

DEMO_STOPS = [
    {
        "gtfs_stop_id": "DEMO-FIVEPOINTS",
        "name": "Five Points Station",
        "description": "MARTA central hub",
        "lat": 33.7540,
        "lon": -84.3920,
        "zone_id": "ATL-CORE",
        "wheelchair_boarding": True,
        "route_ids": ["RED", "GOLD", "BLUE", "GREEN"],
    },
    {
        "gtfs_stop_id": "DEMO-LINDBERGH",
        "name": "Lindbergh Center Station",
        "description": "MARTA transfer point",
        "lat": 33.8230,
        "lon": -84.3690,
        "zone_id": "ATL-NORTH",
        "wheelchair_boarding": True,
        "route_ids": ["RED", "GOLD"],
    },
    {
        "gtfs_stop_id": "DEMO-AIRPORT",
        "name": "Airport Station",
        "description": "Hartsfield-Jackson terminus",
        "lat": 33.6400,
        "lon": -84.4460,
        "zone_id": "ATL-SOUTH",
        "wheelchair_boarding": True,
        "route_ids": ["RED", "GOLD"],
    },
]


def main() -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            inserted = 0
            for s in DEMO_STOPS:
                cur.execute(
                    """
                    INSERT INTO stops (gtfs_stop_id, name, description, lat, lon,
                                       zone_id, wheelchair_boarding, route_ids)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (gtfs_stop_id) DO NOTHING
                    RETURNING id
                    """,
                    (
                        s["gtfs_stop_id"],
                        s["name"],
                        s["description"],
                        s["lat"],
                        s["lon"],
                        s["zone_id"],
                        s["wheelchair_boarding"],
                        s["route_ids"],
                    ),
                )
                if cur.fetchone():
                    inserted += 1
        conn.commit()
    print(f"Seeded marta stops (new: {inserted}, attempted: {len(DEMO_STOPS)}).")


if __name__ == "__main__":
    main()
