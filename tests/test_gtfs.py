"""
Tests for GTFS parser service.
"""
import pytest
import zipfile
import io
from unittest.mock import Mock, patch, MagicMock
from src.services.gtfs_parser import GTFSParser


class TestGTFSParser:
    """Test GTFS parser functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = Mock()
        db.add = Mock()
        db.commit = Mock()
        db.rollback = Mock()
        db.query = Mock()
        return db
    
    @pytest.fixture
    def sample_gtfs_data(self):
        """Create sample GTFS data for testing."""
        routes_csv = """route_id,route_short_name,route_long_name,route_type
RED,Red Line,Red Line - North Springs to Airport,1
GOLD,Gold Line,Gold Line - Doraville to Airport,1"""
        
        stops_csv = """stop_id,stop_name,stop_lat,stop_lon
NS,North Springs,33.9452,-84.3569
AIRPORT,Airport,33.6407,-84.4444"""
        
        trips_csv = """route_id,service_id,trip_id,trip_headsign,direction_id
RED,WEEKDAY,RED_001,Airport,0
RED,WEEKDAY,RED_002,North Springs,1"""
        
        stop_times_csv = """trip_id,arrival_time,departure_time,stop_id,stop_sequence
RED_001,06:00:00,06:00:00,NS,1
RED_001,06:30:00,06:30:00,AIRPORT,2"""
        
        # Create in-memory ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('routes.txt', routes_csv)
            zf.writestr('stops.txt', stops_csv)
            zf.writestr('trips.txt', trips_csv)
            zf.writestr('stop_times.txt', stop_times_csv)
        
        return zip_buffer.getvalue()
    
    def test_parser_initialization(self, mock_db):
        """Test GTFS parser initialization."""
        parser = GTFSParser(mock_db)
        assert parser.db == mock_db
        assert parser.batch_size == 1000
    
    def test_parse_zip_success(self, mock_db, sample_gtfs_data):
        """Test successful GTFS ZIP parsing."""
        parser = GTFSParser(mock_db)
        
        # Mock database operations
        mock_db.query().filter().delete.return_value = 0
        
        result = parser.parse_zip(sample_gtfs_data)
        
        assert "routes" in result
        assert "stops" in result
        assert "trips" in result
        assert "stop_times" in result
        assert result["routes"] == 2
        assert result["stops"] == 2
        mock_db.commit.assert_called()
    
    def test_parse_routes(self, mock_db, sample_gtfs_data):
        """Test parsing routes from GTFS."""
        parser = GTFSParser(mock_db)
        
        with zipfile.ZipFile(io.BytesIO(sample_gtfs_data)) as zf:
            count = parser._parse_routes(zf)
        
        assert count == 2
        assert mock_db.add.call_count == 2
        mock_db.commit.assert_called()
    
    def test_parse_stops(self, mock_db, sample_gtfs_data):
        """Test parsing stops from GTFS."""
        parser = GTFSParser(mock_db)
        
        with zipfile.ZipFile(io.BytesIO(sample_gtfs_data)) as zf:
            count = parser._parse_stops(zf)
        
        assert count == 2
        assert mock_db.add.call_count == 2
        mock_db.commit.assert_called()
    
    def test_parse_with_missing_file(self, mock_db):
        """Test parsing with missing GTFS file."""
        parser = GTFSParser(mock_db)
        
        # Create ZIP with only routes
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('routes.txt', 'route_id,route_short_name,route_long_name,route_type\n')
        
        result = parser.parse_zip(zip_buffer.getvalue())
        
        assert result["routes"] == 0
        assert result["stops"] == 0  # Missing file
        assert result["trips"] == 0  # Missing file
    
    def test_parse_with_invalid_data(self, mock_db):
        """Test parsing with invalid data."""
        parser = GTFSParser(mock_db)
        
        # Create ZIP with invalid stop data (missing required fields)
        invalid_csv = """stop_id,stop_name
NS,North Springs"""  # Missing lat/lon
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('stops.txt', invalid_csv)
        
        result = parser.parse_zip(zip_buffer.getvalue())
        
        # Should handle error gracefully
        assert "error" not in result
        mock_db.rollback.assert_not_called()  # Should handle errors per record
    
    def test_batch_processing(self, mock_db):
        """Test batch processing for large datasets."""
        parser = GTFSParser(mock_db)
        parser.batch_size = 2  # Small batch for testing
        
        # Create CSV with multiple stops
        stops_csv = "stop_id,stop_name,stop_lat,stop_lon\n"
        for i in range(5):
            stops_csv += f"STOP_{i},Stop {i},33.{i},-84.{i}\n"
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('stops.txt', stops_csv)
        
        with zipfile.ZipFile(io.BytesIO(zip_buffer.getvalue())) as zf:
            count = parser._parse_stops(zf)
        
        assert count == 5
        # Should commit multiple times due to batching
        assert mock_db.commit.call_count >= 2