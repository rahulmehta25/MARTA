#!/usr/bin/env python3
"""
Create sample MARTA-like data for testing.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import random
from src.database import SessionLocal, engine
from src.database.models import Base, Route, Stop, Trip, StopTime, RealTimeArrival

def create_sample_data():
    """Create sample MARTA data."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Clear existing data
        db.query(RealTimeArrival).delete()
        db.query(StopTime).delete()
        db.query(Trip).delete()
        db.query(Stop).delete()
        db.query(Route).delete()
        db.commit()
        
        print("Creating sample MARTA data...")
        
        # Create Routes (MARTA's actual rail lines)
        routes = [
            Route(
                route_id="RED",
                route_short_name="Red Line",
                route_long_name="Red Line - North Springs to Airport",
                route_type=1,  # Subway/Metro
                route_color="FF0000",
                on_time_performance=92.5,
                daily_ridership=45000
            ),
            Route(
                route_id="GOLD",
                route_short_name="Gold Line",
                route_long_name="Gold Line - Doraville to Airport",
                route_type=1,
                route_color="FFD700",
                on_time_performance=94.2,
                daily_ridership=42000
            ),
            Route(
                route_id="BLUE",
                route_short_name="Blue Line",
                route_long_name="Blue Line - Hamilton E Holmes to Indian Creek",
                route_type=1,
                route_color="0000FF",
                on_time_performance=91.8,
                daily_ridership=38000
            ),
            Route(
                route_id="GREEN",
                route_short_name="Green Line",
                route_long_name="Green Line - Bankhead to Edgewood/Candler Park",
                route_type=1,
                route_color="00FF00",
                on_time_performance=93.1,
                daily_ridership=35000
            )
        ]
        
        for route in routes:
            db.add(route)
        db.commit()
        print(f"Created {len(routes)} routes")
        
        # Create Stops (Major MARTA stations)
        stops_data = [
            ("AIRPORT", "Airport", 33.6407, -84.4444),
            ("FIVE_POINTS", "Five Points", 33.7540, -84.3915),
            ("NORTH_SPRINGS", "North Springs", 33.9452, -84.3569),
            ("DORAVILLE", "Doraville", 33.9026, -84.2803),
            ("INDIAN_CREEK", "Indian Creek", 33.7698, -84.2295),
            ("HAMILTON", "Hamilton E Holmes", 33.7545, -84.4700),
            ("BANKHEAD", "Bankhead", 33.7722, -84.4285),
            ("CANDLER_PARK", "Edgewood/Candler Park", 33.7619, -84.3397),
            ("MIDTOWN", "Midtown", 33.7808, -84.3865),
            ("BUCKHEAD", "Buckhead", 33.8475, -84.3681),
            ("LENOX", "Lenox", 33.8457, -84.3570),
            ("LINDBERGH", "Lindbergh Center", 33.8226, -84.3696),
            ("ARTS_CENTER", "Arts Center", 33.7892, -84.3872),
            ("CIVIC_CENTER", "Civic Center", 33.7666, -84.3873),
            ("PEACHTREE", "Peachtree Center", 33.7579, -84.3877),
            ("DECATUR", "Decatur", 33.7747, -84.2957),
            ("AVONDALE", "Avondale", 33.7751, -84.2821),
            ("KENSINGTON", "Kensington", 33.7728, -84.2520)
        ]
        
        stops = []
        for stop_id, name, lat, lon in stops_data:
            stop = Stop(
                stop_id=stop_id,
                stop_name=name + " Station",
                stop_lat=lat,
                stop_lon=lon,
                wheelchair_boarding=1,
                has_bike_parking=True,
                has_car_parking=(stop_id in ["NORTH_SPRINGS", "DORAVILLE", "INDIAN_CREEK", "HAMILTON"]),
                parking_capacity=1000 if stop_id in ["NORTH_SPRINGS", "DORAVILLE"] else 500,
                avg_daily_boardings=random.randint(2000, 8000),
                demand_level=random.choice(["high", "medium", "low"])
            )
            stops.append(stop)
            db.add(stop)
        db.commit()
        print(f"Created {len(stops)} stops")
        
        # Create Trips for each route
        trip_count = 0
        for route in routes:
            # Create multiple trips per route
            for i in range(10):  # 10 trips per direction
                for direction in [0, 1]:  # Both directions
                    trip = Trip(
                        trip_id=f"{route.route_id}_{i:03d}_{direction}",
                        route_id=route.route_id,
                        service_id="WEEKDAY",
                        trip_headsign=stops_data[0][1] if direction == 0 else stops_data[2][1],
                        direction_id=direction
                    )
                    db.add(trip)
                    trip_count += 1
        db.commit()
        print(f"Created {trip_count} trips")
        
        # Create StopTimes (simplified schedule)
        stop_time_count = 0
        base_time = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)
        
        trips = db.query(Trip).all()
        for trip in trips[:20]:  # Just do first 20 trips for sample data
            # Get relevant stops for this route
            route_stops = stops[:5] if "RED" in trip.trip_id else stops[5:10]
            
            arrival_time = base_time
            for seq, stop in enumerate(route_stops):
                stop_time = StopTime(
                    trip_id=trip.trip_id,
                    arrival_time=arrival_time.time(),
                    departure_time=arrival_time.time(),
                    stop_id=stop.stop_id,
                    stop_sequence=seq + 1
                )
                db.add(stop_time)
                stop_time_count += 1
                arrival_time += timedelta(minutes=3)  # 3 minutes between stops
        db.commit()
        print(f"Created {stop_time_count} stop times")
        
        # Create some real-time arrivals (current/upcoming)
        arrival_count = 0
        now = datetime.now()
        
        for stop in stops[:10]:  # First 10 stops
            for i in range(5):  # 5 arrivals per stop
                arrival = RealTimeArrival(
                    stop_id=stop.stop_id,
                    route_id=random.choice(["RED", "GOLD", "BLUE", "GREEN"]),
                    trip_id=trips[i].trip_id if i < len(trips) else trips[0].trip_id,
                    arrival_time=f"{random.randint(1, 10)} min",
                    predicted_time=now + timedelta(minutes=random.randint(1, 10)),
                    delay_seconds=random.randint(-60, 300),  # -1 to 5 minutes
                    train_id=f"TRAIN_{random.randint(100, 200)}",
                    destination=random.choice(["Airport", "North Springs", "Doraville", "Indian Creek"]),
                    direction=random.choice(["N", "S", "E", "W"]),
                    is_active=True
                )
                db.add(arrival)
                arrival_count += 1
        db.commit()
        print(f"Created {arrival_count} real-time arrivals")
        
        print("\nSample data created successfully!")
        print("Database now contains:")
        print(f"  - {db.query(Route).count()} routes")
        print(f"  - {db.query(Stop).count()} stops")
        print(f"  - {db.query(Trip).count()} trips")
        print(f"  - {db.query(StopTime).count()} stop times")
        print(f"  - {db.query(RealTimeArrival).count()} real-time arrivals")
        
    finally:
        db.close()

if __name__ == "__main__":
    create_sample_data()