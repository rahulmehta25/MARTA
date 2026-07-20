#!/usr/bin/env python3
"""
Create and populate SQLite database with sample MARTA data
This script generates realistic sample data for development and testing
"""

import os
import sys
from datetime import datetime, timedelta
import random
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models_sqlite import Base, Route, Stop, Trip, StopTime, RealTimeArrival, ServiceAlert, VehiclePosition

def create_database():
    """Create SQLite database and tables"""
    db_path = Path(__file__).parent.parent / "marta_data.db"
    
    # Remove existing database if it exists
    if db_path.exists():
        os.remove(db_path)
        print(f"Removed existing database: {db_path}")
    
    # Create new database
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    print(f"Created new database: {db_path}")
    
    return engine


def create_sample_data():
    """Main function to create and populate the database"""
    print("=" * 60)
    print("MARTA Sample Data Generator")
    print("=" * 60)
    
    # Create database
    engine = create_database()
    
    # Create session
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        
        print("\nCreating sample data...")
        
        # Create Routes (MARTA's actual rail lines)
        routes = [
            Route(
                route_id="RED",
                route_short_name="Red",
                route_long_name="Red Line - North Springs to Airport",
                route_type=1,  # Subway/Metro
                route_color="E51636",
                route_text_color="FFFFFF"
            ),
            Route(
                route_id="GOLD",
                route_short_name="Gold",
                route_long_name="Gold Line - Doraville to Airport",
                route_type=1,
                route_color="FDB913",
                route_text_color="000000"
            ),
            Route(
                route_id="BLUE",
                route_short_name="Blue",
                route_long_name="Blue Line - Hamilton E Holmes to Indian Creek",
                route_type=1,
                route_color="0092D0",
                route_text_color="FFFFFF"
            ),
            Route(
                route_id="GREEN",
                route_short_name="Green",
                route_long_name="Green Line - Bankhead to Edgewood/Candler Park",
                route_type=1,
                route_color="00AA4F",
                route_text_color="FFFFFF"
            ),
            # Bus routes
            Route(
                route_id="1",
                route_short_name="1",
                route_long_name="Route 1 - Marietta Blvd",
                route_type=3,  # Bus
                route_color="008850",
                route_text_color="FFFFFF"
            )
        ]
        
        for route in routes:
            db.add(route)
        db.commit()
        print(f"Created {len(routes)} routes")
        
        # Create Stops (Major MARTA stations)
        stops_data = [
            ("900001", "Five Points Station", 33.7540, -84.3916, 1),
            ("900002", "Airport Station", 33.6407, -84.4467, 1),
            ("900003", "North Springs Station", 33.9449, -84.3570, 1),
            ("900004", "Doraville Station", 33.9032, -84.2802, 1),
            ("900005", "Indian Creek Station", 33.7698, -84.2295, 1),
            ("900006", "Hamilton E Holmes Station", 33.7545, -84.4701, 1),
            ("900007", "Bankhead Station", 33.7723, -84.4287, 1),
            ("900008", "Edgewood/Candler Park Station", 33.7619, -84.3396, 1),
            ("900009", "Lindbergh Center Station", 33.8233, -84.3694, 1),
            ("900010", "Arts Center Station", 33.7892, -84.3872, 1),
            ("900011", "Midtown Station", 33.7808, -84.3864, 1),
            ("900012", "North Avenue Station", 33.7719, -84.3870, 1),
            ("900013", "Civic Center Station", 33.7665, -84.3871, 1),
            ("900014", "Peachtree Center Station", 33.7595, -84.3878, 1),
            ("900015", "Buckhead Station", 33.8478, -84.3679, 1),
            # Bus stops
            ("100001", "Marietta St @ Peachtree St", 33.7628, -84.3901, 0),
            ("100002", "Ponce de Leon Ave @ Highland Ave", 33.7725, -84.3644, 0)
        ]
        
        stops = []
        for stop_id, name, lat, lon, location_type in stops_data:
            stop = Stop(
                stop_id=stop_id,
                stop_code=stop_id,
                stop_name=name,
                stop_lat=lat,
                stop_lon=lon,
                location_type=location_type,
                zone_id="Zone1"
            )
            stops.append(stop)
            db.add(stop)
        db.commit()
        print(f"Created {len(stops)} stops")
        
        # Create Trips for each route
        trips = []
        trip_count = 0
        for route in routes:
            # Create multiple trips per route
            for i in range(10):  # 10 trips per direction
                for direction in [0, 1]:  # Both directions
                    trip = Trip(
                        trip_id=f"{route.route_id}_{i:03d}_{direction}",
                        route_id=route.route_id,
                        service_id="WEEKDAY",
                        trip_headsign="Airport" if direction == 0 else "North Springs",
                        direction_id=direction
                    )
                    trips.append(trip)
                    db.add(trip)
                    trip_count += 1
        db.commit()
        print(f"Created {trip_count} trips")
        
        # Create StopTimes (simplified schedule)
        stop_time_count = 0
        
        for trip in trips[:20]:  # Just do first 20 trips for sample data
            # Get relevant stops for this route
            if "RED" in trip.trip_id:
                route_stops = ["900003", "900009", "900001", "900002"]  # North Springs to Airport
            elif "GOLD" in trip.trip_id:
                route_stops = ["900004", "900009", "900001", "900002"]  # Doraville to Airport
            elif "BLUE" in trip.trip_id:
                route_stops = ["900006", "900001", "900005"]  # Hamilton to Indian Creek
            elif "GREEN" in trip.trip_id:
                route_stops = ["900007", "900001", "900008"]  # Bankhead to Candler Park
            else:
                route_stops = ["100001", "100002"]  # Bus stops
            
            # Reverse stops for opposite direction
            if trip.direction_id == 1:
                route_stops = list(reversed(route_stops))
            
            base_hour = 6 + (int(trip.trip_id.split('_')[1]) // 2)
            base_minute = 0
            
            for seq, stop_id in enumerate(route_stops):
                minutes_from_start = seq * random.randint(3, 5)
                hour = base_hour + (base_minute + minutes_from_start) // 60
                minute = (base_minute + minutes_from_start) % 60
                
                arrival_time = f"{hour:02d}:{minute:02d}:00"
                departure_time = f"{hour:02d}:{minute + 1:02d}:00"
                
                stop_time = StopTime(
                    trip_id=trip.trip_id,
                    arrival_time=arrival_time,
                    departure_time=departure_time,
                    stop_id=stop_id,
                    stop_sequence=seq + 1
                )
                db.add(stop_time)
                stop_time_count += 1
        db.commit()
        print(f"Created {stop_time_count} stop times")
        
        # Create some real-time arrivals (current/upcoming)
        arrival_count = 0
        now = datetime.now()
        
        for stop in stops[:10]:  # First 10 stops
            for i in range(5):  # 5 arrivals per stop
                arrival_time = now + timedelta(minutes=random.randint(1, 15))
                predicted_time = arrival_time + timedelta(seconds=random.randint(-60, 120))
                
                arrival = RealTimeArrival(
                    stop_id=stop.stop_id,
                    route_id=random.choice(["RED", "GOLD", "BLUE", "GREEN"]),
                    trip_id=trips[i].trip_id if i < len(trips) else trips[0].trip_id,
                    arrival_time=arrival_time,
                    predicted_time=predicted_time,
                    delay_seconds=(predicted_time - arrival_time).seconds,
                    vehicle_id=f"VEH_{random.randint(100, 200)}",
                    last_updated=now
                )
                db.add(arrival)
                arrival_count += 1
        db.commit()
        print(f"Created {arrival_count} real-time arrivals")
        
        # Create service alerts
        alerts = [
            ServiceAlert(
                alert_id="ALERT_001",
                header_text="Red Line Delay",
                description_text="Red Line experiencing 10-15 minute delays",
                severity_level="WARNING",
                effect="REDUCED_SERVICE",
                cause="MAINTENANCE",
                start_time=now,
                end_time=now + timedelta(hours=2),
                affected_routes=["RED"],
                affected_stops=["900009"]
            )
        ]
        for alert in alerts:
            db.add(alert)
        db.commit()
        print(f"Created {len(alerts)} service alerts")
        
        print("\n" + "=" * 60)
        print("Sample data creation completed successfully!")
        print("=" * 60)
        print(f"\nDatabase Summary:")
        print(f"  - Routes: {len(routes)}")
        print(f"  - Stops: {len(stops)}")
        print(f"  - Trips: {trip_count}")
        print(f"  - Stop Times: {stop_time_count}")
        print(f"  - Real-time Arrivals: {arrival_count}")
        print(f"  - Service Alerts: {len(alerts)}")
        print("\nDatabase file: marta_data.db")
        
    except Exception as e:
        print(f"\nError creating sample data: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_sample_data()