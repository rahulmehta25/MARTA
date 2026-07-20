"""
WebSocket implementation for real-time updates.
"""
from fastapi import WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
import json
import asyncio
from typing import Dict, Set
import logging

from src.database import get_db
from src.services.realtime_service import RealTimeService

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "real-time": set(),
            "alerts": set(),
            "analytics": set()
        }
    
    async def connect(self, websocket: WebSocket, channel: str = "real-time"):
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        self.active_connections[channel].add(websocket)
        logger.info(f"WebSocket connected to channel: {channel}")
    
    def disconnect(self, websocket: WebSocket, channel: str = "real-time"):
        """Remove a WebSocket connection."""
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
            logger.info(f"WebSocket disconnected from channel: {channel}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket."""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    async def broadcast(self, message: dict, channel: str = "real-time"):
        """Broadcast a message to all connections in a channel."""
        if channel not in self.active_connections:
            return
        
        disconnected = set()
        message_str = json.dumps(message)
        
        for connection in self.active_connections[channel]:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected connections
        for conn in disconnected:
            self.active_connections[channel].discard(conn)


# Global connection manager
manager = ConnectionManager()


async def websocket_endpoint(
    websocket: WebSocket,
    channel: str = "real-time",
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time updates.
    
    Channels:
    - real-time: Live arrival updates
    - alerts: Service alerts and disruptions
    - analytics: System metrics and analytics
    """
    await manager.connect(websocket, channel)
    
    try:
        # Send initial connection message
        await websocket.send_text(json.dumps({
            "type": "connection",
            "channel": channel,
            "message": "Connected to MARTA real-time updates"
        }))
        
        # Start appropriate update loop based on channel
        if channel == "real-time":
            await handle_realtime_updates(websocket, db)
        elif channel == "alerts":
            await handle_alert_updates(websocket, db)
        elif channel == "analytics":
            await handle_analytics_updates(websocket, db)
        else:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Unknown channel: {channel}"
            }))
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
        logger.info(f"Client disconnected from {channel}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, channel)


async def handle_realtime_updates(websocket: WebSocket, db: Session):
    """Handle real-time arrival updates."""
    realtime_service = RealTimeService(db)
    
    while True:
        try:
            # Fetch latest arrivals
            data = await realtime_service.fetch_real_time_data()
            
            if data:
                # Process and send updates
                processed = await realtime_service.process_arrivals(data)
                
                message = {
                    "type": "arrival_update",
                    "timestamp": asyncio.get_event_loop().time(),
                    "arrivals_count": processed,
                    "data": data[:10]  # Send first 10 arrivals
                }
                
                await websocket.send_text(json.dumps(message))
            
            # Wait before next update
            await asyncio.sleep(30)  # 30 seconds
            
        except WebSocketDisconnect:
            break
        except Exception as e:
            logger.error(f"Error in realtime updates: {e}")
            await asyncio.sleep(30)


async def handle_alert_updates(websocket: WebSocket, db: Session):
    """Handle service alert updates."""
    while True:
        try:
            # Query for active alerts
            from src.database.models import ServiceAlert
            alerts = db.query(ServiceAlert).filter(
                ServiceAlert.is_active == True
            ).limit(10).all()
            
            message = {
                "type": "alert_update",
                "timestamp": asyncio.get_event_loop().time(),
                "alerts": [alert.to_dict() for alert in alerts]
            }
            
            await websocket.send_text(json.dumps(message))
            
            # Wait before next update
            await asyncio.sleep(60)  # 1 minute
            
        except WebSocketDisconnect:
            break
        except Exception as e:
            logger.error(f"Error in alert updates: {e}")
            await asyncio.sleep(60)


async def handle_analytics_updates(websocket: WebSocket, db: Session):
    """Handle analytics updates."""
    realtime_service = RealTimeService(db)
    
    while True:
        try:
            # Get system status
            status = realtime_service.get_system_status()
            
            # Calculate additional metrics
            from src.database.models import Route, Stop
            total_routes = db.query(Route).count()
            total_stops = db.query(Stop).count()
            
            message = {
                "type": "analytics_update",
                "timestamp": asyncio.get_event_loop().time(),
                "metrics": {
                    "system_status": status,
                    "total_routes": total_routes,
                    "total_stops": total_stops,
                    "active_trains": status.get("total_active_arrivals", 0),
                    "delay_percentage": status.get("delay_percentage", 0)
                }
            }
            
            await websocket.send_text(json.dumps(message))
            
            # Wait before next update
            await asyncio.sleep(15)  # 15 seconds
            
        except WebSocketDisconnect:
            break
        except Exception as e:
            logger.error(f"Error in analytics updates: {e}")
            await asyncio.sleep(15)


async def broadcast_update(channel: str, data: dict):
    """
    Broadcast an update to all connections in a channel.
    This can be called from other parts of the application.
    """
    await manager.broadcast(data, channel)