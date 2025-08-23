import os
import logging
import requests
import pandas as pd
import psycopg2
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Event Venues to Scrape
VENUES = {
    'mercedes_benz_stadium': {
        'name': 'Mercedes-Benz Stadium',
        'url': 'https://www.mercedesbenzstadium.com/events/',
        'lat': 33.7553,
        'lon': -84.4006
    },
    'state_farm_arena': {
        'name': 'State Farm Arena',
        'url': 'https://www.statefarmarena.com/events',
        'lat': 33.7573,
        'lon': -84.3963
    },
    'truist_park': {
        'name': 'Truist Park',
        'url': 'https://www.mlb.com/braves/ballpark/events',
        'lat': 33.8907,
        'lon': -84.4677
    }
}

OUTPUT_CSV = "data/external/atlanta_events_data.csv"
EVENTS_TABLE = "atlanta_events_data"

# Database connection details
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "marta_db")
DB_USER = os.getenv("DB_USER", "marta_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "marta_password")

CREATE_EVENTS_TABLE = f'''
CREATE TABLE IF NOT EXISTS {EVENTS_TABLE} (
    id SERIAL PRIMARY KEY,
    venue_name TEXT,
    event_name TEXT,
    event_date DATE,
    event_time TIME,
    event_type TEXT,
    event_description TEXT,
    venue_lat NUMERIC,
    venue_lon NUMERIC,
    estimated_attendance INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
'''

def create_db_connection():
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD)

def setup_events_table(conn):
    with conn.cursor() as cursor:
        cursor.execute(CREATE_EVENTS_TABLE)
        conn.commit()
        logging.info(f"Ensured events table {EVENTS_TABLE} exists.")

def scrape_mercedes_benz_events():
    """Scrape events from Mercedes-Benz Stadium"""
    logging.info("Scraping Mercedes-Benz Stadium events")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(VENUES['mercedes_benz_stadium']['url'], headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        events = []
        
        # Look for event containers (this will need adjustment based on actual HTML structure)
        event_containers = soup.find_all(['div', 'article'], class_=re.compile(r'event|Event'))
        
        for container in event_containers:
            try:
                # Extract event name
                name_elem = container.find(['h1', 'h2', 'h3', 'h4'], class_=re.compile(r'title|name'))
                event_name = name_elem.get_text(strip=True) if name_elem else "Unknown Event"
                
                # Extract date
                date_elem = container.find(['span', 'div'], class_=re.compile(r'date|Date'))
                event_date = None
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    # Try to parse various date formats
                    for fmt in ['%B %d, %Y', '%m/%d/%Y', '%Y-%m-%d']:
                        try:
                            event_date = datetime.strptime(date_text, fmt).date()
                            break
                        except ValueError:
                            continue
                
                # Extract time
                time_elem = container.find(['span', 'div'], class_=re.compile(r'time|Time'))
                event_time = None
                if time_elem:
                    time_text = time_elem.get_text(strip=True)
                    # Try to parse time
                    try:
                        event_time = datetime.strptime(time_text, '%I:%M %p').time()
                    except ValueError:
                        pass
                
                # Determine event type based on keywords
                event_type = "Other"
                event_lower = event_name.lower()
                if any(word in event_lower for word in ['football', 'falcons', 'nfl']):
                    event_type = "Football"
                elif any(word in event_lower for word in ['soccer', 'atlanta united']):
                    event_type = "Soccer"
                elif any(word in event_lower for word in ['concert', 'music']):
                    event_type = "Concert"
                elif any(word in event_lower for word in ['conference', 'convention']):
                    event_type = "Conference"
                
                # Estimate attendance based on event type
                estimated_attendance = 50000  # Default for stadium events
                if event_type == "Concert":
                    estimated_attendance = 70000
                elif event_type == "Conference":
                    estimated_attendance = 20000
                
                if event_date:  # Only add if we have a valid date
                    events.append({
                        'venue_name': VENUES['mercedes_benz_stadium']['name'],
                        'event_name': event_name,
                        'event_date': event_date,
                        'event_time': event_time,
                        'event_type': event_type,
                        'event_description': f"{event_type} event at Mercedes-Benz Stadium",
                        'venue_lat': VENUES['mercedes_benz_stadium']['lat'],
                        'venue_lon': VENUES['mercedes_benz_stadium']['lon'],
                        'estimated_attendance': estimated_attendance
                    })
                    
            except Exception as e:
                logging.warning(f"Error parsing event container: {e}")
                continue
        
        logging.info(f"Scraped {len(events)} events from Mercedes-Benz Stadium")
        return events
        
    except Exception as e:
        logging.error(f"Error scraping Mercedes-Benz Stadium: {e}")
        return []

def scrape_state_farm_arena_events():
    """Scrape events from State Farm Arena"""
    logging.info("Scraping State Farm Arena events")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(VENUES['state_farm_arena']['url'], headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        events = []
        
        # Similar parsing logic as Mercedes-Benz Stadium
        event_containers = soup.find_all(['div', 'article'], class_=re.compile(r'event|Event'))
        
        for container in event_containers:
            try:
                name_elem = container.find(['h1', 'h2', 'h3', 'h4'], class_=re.compile(r'title|name'))
                event_name = name_elem.get_text(strip=True) if name_elem else "Unknown Event"
                
                date_elem = container.find(['span', 'div'], class_=re.compile(r'date|Date'))
                event_date = None
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    for fmt in ['%B %d, %Y', '%m/%d/%Y', '%Y-%m-%d']:
                        try:
                            event_date = datetime.strptime(date_text, fmt).date()
                            break
                        except ValueError:
                            continue
                
                # Determine event type
                event_type = "Other"
                event_lower = event_name.lower()
                if any(word in event_lower for word in ['basketball', 'hawks', 'nba']):
                    event_type = "Basketball"
                elif any(word in event_lower for word in ['concert', 'music']):
                    event_type = "Concert"
                elif any(word in event_lower for word in ['hockey', 'nhl']):
                    event_type = "Hockey"
                
                estimated_attendance = 20000  # Default for arena events
                if event_type == "Basketball":
                    estimated_attendance = 18000
                elif event_type == "Concert":
                    estimated_attendance = 21000
                
                if event_date:
                    events.append({
                        'venue_name': VENUES['state_farm_arena']['name'],
                        'event_name': event_name,
                        'event_date': event_date,
                        'event_time': None,
                        'event_type': event_type,
                        'event_description': f"{event_type} event at State Farm Arena",
                        'venue_lat': VENUES['state_farm_arena']['lat'],
                        'venue_lon': VENUES['state_farm_arena']['lon'],
                        'estimated_attendance': estimated_attendance
                    })
                    
            except Exception as e:
                logging.warning(f"Error parsing event container: {e}")
                continue
        
        logging.info(f"Scraped {len(events)} events from State Farm Arena")
        return events
        
    except Exception as e:
        logging.error(f"Error scraping State Farm Arena: {e}")
        return []

def generate_sample_events():
    """Generate sample events for demonstration when scraping fails"""
    logging.info("Generating sample events data")
    
    events = []
    base_date = datetime.now()
    
    # Sample events for next 30 days
    for i in range(30):
        event_date = base_date + timedelta(days=i)
        
        # Mercedes-Benz Stadium events
        if i % 7 == 0:  # Weekly football games
            events.append({
                'venue_name': 'Mercedes-Benz Stadium',
                'event_name': f'Atlanta Falcons vs Opponent {i//7 + 1}',
                'event_date': event_date.date(),
                'event_time': datetime.strptime('13:00', '%H:%M').time(),
                'event_type': 'Football',
                'event_description': 'NFL Football Game',
                'venue_lat': 33.7553,
                'venue_lon': -84.4006,
                'estimated_attendance': 70000
            })
        
        # State Farm Arena events
        if i % 3 == 0:  # Basketball games
            events.append({
                'venue_name': 'State Farm Arena',
                'event_name': f'Atlanta Hawks vs Team {i//3 + 1}',
                'event_date': event_date.date(),
                'event_time': datetime.strptime('19:30', '%H:%M').time(),
                'event_type': 'Basketball',
                'event_description': 'NBA Basketball Game',
                'venue_lat': 33.7573,
                'venue_lon': -84.3963,
                'estimated_attendance': 18000
            })
        
        # Concerts
        if i % 10 == 0:  # Concerts
            events.append({
                'venue_name': 'Mercedes-Benz Stadium',
                'event_name': f'Concert Artist {i//10 + 1}',
                'event_date': event_date.date(),
                'event_time': datetime.strptime('20:00', '%H:%M').time(),
                'event_type': 'Concert',
                'event_description': 'Music Concert',
                'venue_lat': 33.7553,
                'venue_lon': -84.4006,
                'estimated_attendance': 65000
            })
    
    return events

def store_events_data(conn, events_data):
    if not events_data:
        return
    
    with conn.cursor() as cursor:
        for event in events_data:
            cursor.execute(f'''
                INSERT INTO {EVENTS_TABLE} (
                    venue_name, event_name, event_date, event_time, event_type,
                    event_description, venue_lat, venue_lon, estimated_attendance
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (venue_name, event_name, event_date) DO UPDATE SET
                    event_time = EXCLUDED.event_time,
                    event_type = EXCLUDED.event_type,
                    event_description = EXCLUDED.event_description,
                    estimated_attendance = EXCLUDED.estimated_attendance,
                    created_at = CURRENT_TIMESTAMP;
            ''', (
                event['venue_name'],
                event['event_name'],
                event['event_date'],
                event['event_time'],
                event['event_type'],
                event['event_description'],
                event['venue_lat'],
                event['venue_lon'],
                event['estimated_attendance']
            ))
        conn.commit()
        logging.info(f"Inserted/updated {len(events_data)} events.")

def save_to_csv(events_data):
    if not events_data:
        return
    
    df = pd.DataFrame(events_data)
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)
    logging.info(f"Saved events data to {OUTPUT_CSV}")

def main():
    logging.info("Starting events data scraping")
    
    all_events = []
    
    # Try to scrape from real venues
    try:
        mbs_events = scrape_mercedes_benz_events()
        all_events.extend(mbs_events)
    except Exception as e:
        logging.error(f"Failed to scrape Mercedes-Benz Stadium: {e}")
    
    try:
        sfa_events = scrape_state_farm_arena_events()
        all_events.extend(sfa_events)
    except Exception as e:
        logging.error(f"Failed to scrape State Farm Arena: {e}")
    
    # If no real data, generate sample data
    if not all_events:
        logging.info("No real events scraped, generating sample data")
        all_events = generate_sample_events()
    
    if all_events:
        # Store in database
        conn = create_db_connection()
        setup_events_table(conn)
        store_events_data(conn, all_events)
        conn.close()
        
        # Save to CSV
        save_to_csv(all_events)
        
        logging.info(f"Events scraping complete. Total events: {len(all_events)}")
    else:
        logging.error("No events data retrieved")

if __name__ == "__main__":
    main() 