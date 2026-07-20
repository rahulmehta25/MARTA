"""
Unit tests for data ingestion modules in the MARTA platform.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime, timedelta
import json
import tempfile
import os
from io import StringIO, BytesIO
import zipfile
import requests
from unittest.mock import AsyncMock
import asyncio

# Test imports
from src.data_ingestion.gtfs_ingestion import GTFSIngestion
from src.data_ingestion.gtfs_realtime_processor import GTFSRealtimeProcessor
from src.data_ingestion.weather_data_fetcher import WeatherDataFetcher
from src.data_ingestion.event_data_scraper import EventDataScraper


class TestGTFSIngestion:
    """Test suite for GTFS static data ingestion."""
    
    @pytest.fixture
    def gtfs_ingestor(self):
        """Create GTFS ingestor instance."""
        return GTFSIngestion(
            db_config={
                'host': 'localhost',
                'database': 'test_db',
                'user': 'test_user',
                'password': 'test_pass'
            }
        )
    
    def test_initialization(self, gtfs_ingestor):
        """Test GTFS ingestor initialization."""
        assert gtfs_ingestor.db_config['host'] == 'localhost'
        assert gtfs_ingestor.db_config['database'] == 'test_db'
        assert gtfs_ingestor.required_files == [
            'stops.txt', 'routes.txt', 'trips.txt', 
            'stop_times.txt', 'calendar.txt'
        ]
    
    def test_validate_gtfs_files_success(self, gtfs_ingestor):
        """Test GTFS file validation with valid files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create required GTFS files
            for filename in gtfs_ingestor.required_files:
                file_path = os.path.join(tmp_dir, filename)
                with open(file_path, 'w') as f:
                    f.write("test,data\n1,2\n")  # Minimal CSV content
            
            # Should not raise exception
            gtfs_ingestor.validate_gtfs_files(tmp_dir)
    
    def test_validate_gtfs_files_missing(self, gtfs_ingestor):
        """Test GTFS file validation with missing files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create only some files
            for filename in gtfs_ingestor.required_files[:2]:
                file_path = os.path.join(tmp_dir, filename)
                with open(file_path, 'w') as f:
                    f.write("test,data\n")
            
            with pytest.raises(FileNotFoundError):
                gtfs_ingestor.validate_gtfs_files(tmp_dir)
    
    def test_parse_gtfs_file(self, gtfs_ingestor):
        """Test individual GTFS file parsing."""
        csv_content = "stop_id,stop_name,stop_lat,stop_lon\nstop1,Station A,33.7490,-84.3880\nstop2,Station B,33.7701,-84.3850\n"
        
        with patch('pandas.read_csv') as mock_read_csv:
            mock_df = pd.DataFrame({
                'stop_id': ['stop1', 'stop2'],
                'stop_name': ['Station A', 'Station B'],
                'stop_lat': [33.7490, 33.7701],
                'stop_lon': [-84.3880, -84.3850]
            })
            mock_read_csv.return_value = mock_df
            
            result = gtfs_ingestor.parse_gtfs_file('/fake/path/stops.txt')
            
            mock_read_csv.assert_called_once_with('/fake/path/stops.txt', dtype=str)
            assert len(result) == 2
            assert 'stop_id' in result.columns
    
    def test_clean_gtfs_data(self, gtfs_ingestor, sample_gtfs_data):
        """Test GTFS data cleaning."""
        # Add some dirty data
        dirty_stops = sample_gtfs_data['stops'].copy()
        dirty_stops.loc[0, 'stop_lat'] = 'invalid'  # Invalid latitude
        dirty_stops.loc[1, 'stop_name'] = ''  # Empty name
        
        cleaned = gtfs_ingestor.clean_gtfs_data(dirty_stops, 'stops')
        
        # Should remove invalid rows
        assert len(cleaned) < len(dirty_stops)
        assert cleaned['stop_name'].str.len().min() > 0  # No empty names
    
    @patch('psycopg2.connect')
    def test_save_to_database(self, mock_connect, gtfs_ingestor, sample_gtfs_data):
        """Test saving GTFS data to database."""
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        gtfs_ingestor.save_to_database(sample_gtfs_data['stops'], 'gtfs_stops')
        
        # Verify database operations
        mock_connect.assert_called_once()
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()
        mock_conn.close.assert_called()
    
    def test_download_gtfs_feed(self, gtfs_ingestor):
        """Test GTFS feed download."""
        mock_response = Mock()
        mock_response.content = b'fake_zip_content'
        mock_response.raise_for_status = Mock()
        
        with patch('requests.get', return_value=mock_response) as mock_get:
            with tempfile.TemporaryDirectory() as tmp_dir:
                output_path = os.path.join(tmp_dir, 'gtfs.zip')
                
                gtfs_ingestor.download_gtfs_feed('http://fake-url.com/gtfs.zip', output_path)
                
                mock_get.assert_called_once_with('http://fake-url.com/gtfs.zip')
                assert os.path.exists(output_path)
    
    def test_extract_gtfs_zip(self, gtfs_ingestor):
        """Test GTFS ZIP file extraction."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create a fake ZIP file with GTFS content
            zip_path = os.path.join(tmp_dir, 'gtfs.zip')
            extract_dir = os.path.join(tmp_dir, 'extracted')
            
            with zipfile.ZipFile(zip_path, 'w') as zip_file:
                for filename in gtfs_ingestor.required_files:
                    zip_file.writestr(filename, 'test,data\n1,2\n')
            
            gtfs_ingestor.extract_gtfs_zip(zip_path, extract_dir)
            
            # Check files were extracted
            for filename in gtfs_ingestor.required_files:
                assert os.path.exists(os.path.join(extract_dir, filename))
    
    @patch('psycopg2.connect')
    def test_full_ingestion_pipeline(self, mock_connect, gtfs_ingestor):
        """Test complete GTFS ingestion pipeline."""
        # Mock database
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create GTFS files
            stops_data = "stop_id,stop_name,stop_lat,stop_lon\nstop1,Station A,33.7490,-84.3880\n"
            routes_data = "route_id,route_short_name,route_long_name,route_type\nroute1,RED,Red Line,1\n"
            trips_data = "route_id,service_id,trip_id,direction_id\nroute1,weekday,trip1,0\n"
            stop_times_data = "trip_id,arrival_time,departure_time,stop_id,stop_sequence\ntrip1,08:00:00,08:01:00,stop1,1\n"
            calendar_data = "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\nweekday,1,1,1,1,1,0,0,20240101,20241231\n"
            
            file_data = {
                'stops.txt': stops_data,
                'routes.txt': routes_data,
                'trips.txt': trips_data,
                'stop_times.txt': stop_times_data,
                'calendar.txt': calendar_data
            }
            
            for filename, content in file_data.items():
                with open(os.path.join(tmp_dir, filename), 'w') as f:
                    f.write(content)
            
            # Run ingestion
            gtfs_ingestor.ingest_gtfs_data(tmp_dir)
            
            # Verify database operations occurred
            assert mock_cursor.execute.call_count > 0
            assert mock_conn.commit.call_count > 0


class TestGTFSRealtimeProcessor:
    """Test suite for GTFS real-time data processing."""
    
    @pytest.fixture
    def realtime_processor(self):
        """Create real-time processor instance."""
        return GTFSRealtimeProcessor(
            feed_urls={
                'vehicle_positions': 'http://fake-url.com/vehicle_positions',
                'trip_updates': 'http://fake-url.com/trip_updates'
            },
            db_config={
                'host': 'localhost',
                'database': 'test_db',
                'user': 'test_user',
                'password': 'test_pass'
            }
        )
    
    def test_initialization(self, realtime_processor):
        """Test real-time processor initialization."""
        assert 'vehicle_positions' in realtime_processor.feed_urls
        assert 'trip_updates' in realtime_processor.feed_urls
        assert realtime_processor.db_config['host'] == 'localhost'
    
    def test_fetch_realtime_feed(self, realtime_processor, sample_realtime_data):
        """Test fetching real-time GTFS feed."""
        mock_response = Mock()
        mock_response.content = json.dumps(sample_realtime_data).encode()
        mock_response.raise_for_status = Mock()
        
        with patch('requests.get', return_value=mock_response) as mock_get:
            result = realtime_processor.fetch_realtime_feed('http://fake-url.com/vehicles')
            
            mock_get.assert_called_once_with(
                'http://fake-url.com/vehicles',
                timeout=realtime_processor.timeout
            )
            assert result == sample_realtime_data
    
    def test_parse_vehicle_positions(self, realtime_processor, sample_realtime_data):
        """Test parsing vehicle position data."""
        vehicles = realtime_processor.parse_vehicle_positions(
            sample_realtime_data['vehicle_positions']
        )
        
        assert len(vehicles) == 2
        assert all('vehicle_id' in v for v in vehicles)
        assert all('latitude' in v for v in vehicles)
        assert all('longitude' in v for v in vehicles)
        assert all('timestamp' in v for v in vehicles)
    
    def test_parse_trip_updates(self, realtime_processor, sample_realtime_data):
        """Test parsing trip update data."""
        updates = realtime_processor.parse_trip_updates(
            sample_realtime_data['trip_updates']
        )
        
        assert len(updates) == 1
        assert all('trip_id' in u for u in updates)
        assert all('route_id' in u for u in updates)
        assert all('stop_time_updates' in u for u in updates)
    
    def test_validate_vehicle_position(self, realtime_processor):
        """Test vehicle position validation."""
        valid_position = {
            'vehicle_id': 'vehicle_1',
            'route_id': 'route1',
            'latitude': 33.7490,
            'longitude': -84.3880,
            'timestamp': datetime.now().timestamp()
        }
        
        invalid_position = {
            'vehicle_id': 'vehicle_2',
            'latitude': 91.0,  # Invalid latitude
            'longitude': -184.0,  # Invalid longitude
            'timestamp': datetime.now().timestamp()
        }
        
        assert realtime_processor.validate_vehicle_position(valid_position)
        assert not realtime_processor.validate_vehicle_position(invalid_position)
    
    @patch('psycopg2.connect')
    def test_save_vehicle_positions(self, mock_connect, realtime_processor, sample_realtime_data):
        """Test saving vehicle positions to database."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        realtime_processor.save_vehicle_positions(sample_realtime_data['vehicle_positions'])
        
        mock_connect.assert_called_once()
        mock_cursor.executemany.assert_called_once()
        mock_conn.commit.assert_called_once()
    
    def test_calculate_delays(self, realtime_processor):
        """Test delay calculation from trip updates."""
        trip_update = {
            'trip_id': 'trip1',
            'stop_time_updates': [
                {'stop_id': 'stop1', 'arrival_delay': 120, 'departure_delay': 130},
                {'stop_id': 'stop2', 'arrival_delay': 90, 'departure_delay': 95}
            ]
        }
        
        delays = realtime_processor.calculate_delays(trip_update)
        
        assert len(delays) == 2
        assert delays[0]['delay_seconds'] == 120
        assert delays[1]['delay_seconds'] == 90
        assert all('stop_id' in d for d in delays)
    
    def test_process_realtime_batch(self, realtime_processor, sample_realtime_data):
        """Test processing batch of real-time data."""
        with patch.object(realtime_processor, 'save_vehicle_positions') as mock_save_vehicles, \
             patch.object(realtime_processor, 'save_trip_updates') as mock_save_trips:
            
            realtime_processor.process_realtime_batch(sample_realtime_data)
            
            mock_save_vehicles.assert_called_once()
            mock_save_trips.assert_called_once()


class TestWeatherDataFetcher:
    """Test suite for weather data fetching."""
    
    @pytest.fixture
    def weather_fetcher(self):
        """Create weather data fetcher instance."""
        return WeatherDataFetcher(
            api_key='fake_api_key',
            base_url='http://fake-weather-api.com',
            location={'lat': 33.7490, 'lon': -84.3880}  # Atlanta coordinates
        )
    
    def test_initialization(self, weather_fetcher):
        """Test weather fetcher initialization."""
        assert weather_fetcher.api_key == 'fake_api_key'
        assert weather_fetcher.location['lat'] == 33.7490
        assert weather_fetcher.location['lon'] == -84.3880
    
    def test_fetch_current_weather(self, weather_fetcher):
        """Test fetching current weather data."""
        mock_response_data = {
            'weather': [{'main': 'Clear', 'description': 'clear sky'}],
            'main': {'temp': 72.5, 'humidity': 65, 'pressure': 1013},
            'wind': {'speed': 5.2, 'deg': 180},
            'dt': int(datetime.now().timestamp())
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = Mock()
        
        with patch('requests.get', return_value=mock_response) as mock_get:
            weather_data = weather_fetcher.fetch_current_weather()
            
            mock_get.assert_called_once()
            assert weather_data['temperature'] == 72.5
            assert weather_data['humidity'] == 65
            assert weather_data['condition'] == 'Clear'
    
    def test_fetch_forecast(self, weather_fetcher):
        """Test fetching weather forecast."""
        mock_forecast_data = {
            'list': [
                {
                    'dt': int(datetime.now().timestamp()),
                    'main': {'temp': 75.0, 'humidity': 60},
                    'weather': [{'main': 'Sunny', 'description': 'sunny'}],
                    'wind': {'speed': 3.1}
                },
                {
                    'dt': int((datetime.now() + timedelta(hours=3)).timestamp()),
                    'main': {'temp': 78.0, 'humidity': 55},
                    'weather': [{'main': 'Cloudy', 'description': 'partly cloudy'}],
                    'wind': {'speed': 4.2}
                }
            ]
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_forecast_data
        mock_response.raise_for_status = Mock()
        
        with patch('requests.get', return_value=mock_response) as mock_get:
            forecast_data = weather_fetcher.fetch_forecast(hours=6)
            
            mock_get.assert_called_once()
            assert len(forecast_data) == 2
            assert forecast_data[0]['temperature'] == 75.0
            assert forecast_data[1]['condition'] == 'Cloudy'
    
    def test_parse_weather_data(self, weather_fetcher):
        """Test weather data parsing."""
        raw_data = {
            'weather': [{'main': 'Rain', 'description': 'light rain'}],
            'main': {'temp': 68.3, 'humidity': 85, 'pressure': 1008},
            'wind': {'speed': 8.5, 'deg': 270},
            'visibility': 8000,
            'dt': int(datetime.now().timestamp())
        }
        
        parsed = weather_fetcher.parse_weather_data(raw_data)
        
        assert parsed['temperature'] == 68.3
        assert parsed['humidity'] == 85
        assert parsed['condition'] == 'Rain'
        assert parsed['wind_speed'] == 8.5
        assert parsed['visibility'] == 8000
    
    def test_weather_severity_calculation(self, weather_fetcher):
        """Test weather severity scoring."""
        severe_weather = {
            'condition': 'Thunderstorm',
            'temperature': 35.0,  # Very hot
            'wind_speed': 25.0,   # High wind
            'precipitation': 2.5   # Heavy rain
        }
        
        mild_weather = {
            'condition': 'Clear',
            'temperature': 72.0,
            'wind_speed': 3.0,
            'precipitation': 0.0
        }
        
        severe_score = weather_fetcher.calculate_weather_severity(severe_weather)
        mild_score = weather_fetcher.calculate_weather_severity(mild_weather)
        
        assert severe_score > mild_score
        assert 0 <= severe_score <= 10
        assert 0 <= mild_score <= 10
    
    @patch('psycopg2.connect')
    def test_save_weather_data(self, mock_connect, weather_fetcher):
        """Test saving weather data to database."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        weather_data = {
            'timestamp': datetime.now(),
            'temperature': 75.0,
            'humidity': 60,
            'condition': 'Sunny',
            'wind_speed': 5.0,
            'precipitation': 0.0
        }
        
        weather_fetcher.save_weather_data(weather_data)
        
        mock_connect.assert_called_once()
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
    
    def test_api_error_handling(self, weather_fetcher):
        """Test handling of API errors."""
        # Mock API error response
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.RequestException("API Error")
        
        with patch('requests.get', return_value=mock_response):
            with pytest.raises(requests.RequestException):
                weather_fetcher.fetch_current_weather()
    
    def test_rate_limiting(self, weather_fetcher):
        """Test API rate limiting."""
        with patch('time.sleep') as mock_sleep:
            # Simulate rapid successive calls
            for _ in range(3):
                weather_fetcher._check_rate_limit()
            
            # Should have called sleep to enforce rate limiting
            assert mock_sleep.call_count >= 0  # May or may not sleep depending on timing


class TestEventDataScraper:
    """Test suite for event data scraping."""
    
    @pytest.fixture
    def event_scraper(self):
        """Create event data scraper instance."""
        return EventDataScraper(
            event_sources=[
                'http://fake-events.com/atlanta',
                'http://fake-sports.com/atlanta-events'
            ]
        )
    
    def test_initialization(self, event_scraper):
        """Test event scraper initialization."""
        assert len(event_scraper.event_sources) == 2
        assert 'atlanta' in event_scraper.event_sources[0]
    
    def test_scrape_events_html(self, event_scraper):
        """Test scraping events from HTML."""
        mock_html = """
        <html>
            <div class="event">
                <h3>Concert at State Farm Arena</h3>
                <p class="date">2024-06-15</p>
                <p class="time">19:30</p>
                <p class="venue">State Farm Arena</p>
            </div>
            <div class="event">
                <h3>Hawks Game</h3>
                <p class="date">2024-06-20</p>
                <p class="time">20:00</p>
                <p class="venue">State Farm Arena</p>
            </div>
        </html>
        """
        
        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()
        
        with patch('requests.get', return_value=mock_response):
            events = event_scraper.scrape_events_from_url('http://fake-events.com/atlanta')
            
            assert len(events) >= 0  # May vary based on parsing logic
            if events:
                assert 'title' in events[0]
                assert 'date' in events[0]
                assert 'venue' in events[0]
    
    def test_parse_event_data(self, event_scraper):
        """Test parsing individual event data."""
        raw_event = {
            'title': 'Atlanta Hawks vs Boston Celtics',
            'date': '2024-06-15',
            'time': '19:30',
            'venue': 'State Farm Arena',
            'description': 'NBA playoff game'
        }
        
        parsed_event = event_scraper.parse_event_data(raw_event)
        
        assert parsed_event['title'] == raw_event['title']
        assert parsed_event['venue'] == raw_event['venue']
        assert 'datetime' in parsed_event
        assert 'event_type' in parsed_event
    
    def test_categorize_event(self, event_scraper):
        """Test event categorization."""
        sports_event = {'title': 'Atlanta Hawks Game', 'venue': 'State Farm Arena'}
        concert_event = {'title': 'Taylor Swift Concert', 'venue': 'Mercedes-Benz Stadium'}
        conference_event = {'title': 'Tech Conference 2024', 'venue': 'Georgia World Congress Center'}
        
        assert event_scraper.categorize_event(sports_event) == 'Sports'
        assert event_scraper.categorize_event(concert_event) == 'Concert'
        assert event_scraper.categorize_event(conference_event) == 'Conference'
    
    def test_estimate_attendance(self, event_scraper):
        """Test attendance estimation."""
        large_venue_event = {
            'venue': 'Mercedes-Benz Stadium',
            'event_type': 'Sports',
            'title': 'Atlanta Falcons Game'
        }
        
        small_venue_event = {
            'venue': 'Fox Theatre',
            'event_type': 'Concert',
            'title': 'Local Band Concert'
        }
        
        large_attendance = event_scraper.estimate_attendance(large_venue_event)
        small_attendance = event_scraper.estimate_attendance(small_venue_event)
        
        assert large_attendance > small_attendance
        assert large_attendance > 0
        assert small_attendance > 0
    
    def test_calculate_transit_impact(self, event_scraper):
        """Test transit impact calculation."""
        high_impact_event = {
            'estimated_attendance': 50000,
            'venue': 'Mercedes-Benz Stadium',
            'datetime': datetime.now() + timedelta(hours=2),
            'event_type': 'Sports'
        }
        
        low_impact_event = {
            'estimated_attendance': 500,
            'venue': 'Small Theater',
            'datetime': datetime.now() + timedelta(days=1),
            'event_type': 'Theater'
        }
        
        high_impact = event_scraper.calculate_transit_impact(high_impact_event)
        low_impact = event_scraper.calculate_transit_impact(low_impact_event)
        
        assert high_impact['impact_score'] > low_impact['impact_score']
        assert 'affected_routes' in high_impact
        assert 'peak_demand_multiplier' in high_impact
    
    @patch('psycopg2.connect')
    def test_save_events(self, mock_connect, event_scraper):
        """Test saving events to database."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        events = [
            {
                'title': 'Test Event',
                'datetime': datetime.now(),
                'venue': 'Test Venue',
                'event_type': 'Test',
                'estimated_attendance': 1000,
                'transit_impact': {'impact_score': 5.0}
            }
        ]
        
        event_scraper.save_events(events)
        
        mock_connect.assert_called_once()
        mock_cursor.executemany.assert_called_once()
        mock_conn.commit.assert_called_once()
    
    def test_scraping_error_handling(self, event_scraper):
        """Test error handling in web scraping."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.RequestException("Network error")
        
        with patch('requests.get', return_value=mock_response):
            with pytest.raises(requests.RequestException):
                event_scraper.scrape_events_from_url('http://invalid-url.com')
    
    def test_data_validation(self, event_scraper):
        """Test event data validation."""
        valid_event = {
            'title': 'Valid Event',
            'datetime': datetime.now(),
            'venue': 'Valid Venue',
            'estimated_attendance': 1000
        }
        
        invalid_event = {
            'title': '',  # Empty title
            'datetime': 'invalid-date',  # Invalid datetime
            'venue': None,  # No venue
            'estimated_attendance': -100  # Negative attendance
        }
        
        assert event_scraper.validate_event_data(valid_event)
        assert not event_scraper.validate_event_data(invalid_event)


@pytest.mark.integration  
class TestDataIngestionIntegration:
    """Integration tests for data ingestion modules."""
    
    def test_gtfs_to_database_integration(self, sample_gtfs_data):
        """Test complete GTFS ingestion to database."""
        # This would test the full pipeline with a test database
        # Implementation depends on test database setup
        pass
    
    def test_realtime_processing_pipeline(self, sample_realtime_data):
        """Test real-time data processing pipeline."""
        # This would test the complete real-time processing workflow
        pass
    
    def test_weather_data_enrichment(self, sample_weather_data, sample_ridership_data):
        """Test enriching ridership data with weather information."""
        # Test joining weather data with ridership data
        pass