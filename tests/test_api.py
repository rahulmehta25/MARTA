"""
API tests for MARTA Transit Analytics Platform.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api.main import app
from src.database import Base, get_db


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)


@pytest.fixture
def setup_database():
    """Setup test database."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_root_endpoint(self):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "status" in data
    
    def test_health_endpoint(self):
        """Test basic health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_health_detailed_endpoint(self):
        """Test detailed health endpoint."""
        response = client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "database" in data
        assert "system" in data
        assert "features" in data


class TestRouteEndpoints:
    """Test route-related endpoints."""
    
    def test_get_routes(self, setup_database):
        """Test getting all routes."""
        response = client.get("/api/v1/routes")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_route_not_found(self, setup_database):
        """Test getting non-existent route."""
        response = client.get("/api/v1/routes/NONEXISTENT")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_get_route_performance(self, setup_database):
        """Test getting route performance metrics."""
        # First create a route
        from src.database.models import Route
        db = TestingSessionLocal()
        route = Route(
            route_id="RED",
            route_short_name="Red Line",
            route_long_name="Red Line - North Springs to Airport",
            route_type=1
        )
        db.add(route)
        db.commit()
        db.close()
        
        # Test performance endpoint
        response = client.get("/api/v1/routes/RED/performance")
        assert response.status_code == 200
        data = response.json()
        assert "route_id" in data
        assert "on_time_performance" in data


class TestStopEndpoints:
    """Test stop-related endpoints."""
    
    def test_get_stops(self, setup_database):
        """Test getting all stops."""
        response = client.get("/api/v1/stops")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_stops_with_location_filter(self, setup_database):
        """Test getting stops with location filter."""
        response = client.get("/api/v1/stops?lat=33.7490&lon=-84.3880&radius=1.0")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_stop_not_found(self, setup_database):
        """Test getting non-existent stop."""
        response = client.get("/api/v1/stops/NONEXISTENT")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestWebSocketEndpoints:
    """Test WebSocket endpoints."""
    
    def test_websocket_realtime_connection(self):
        """Test WebSocket real-time connection."""
        with client.websocket_connect("/ws/real-time") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connection"
            assert data["channel"] == "real-time"
    
    def test_websocket_alerts_connection(self):
        """Test WebSocket alerts connection."""
        with client.websocket_connect("/ws/alerts") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connection"
            assert data["channel"] == "alerts"