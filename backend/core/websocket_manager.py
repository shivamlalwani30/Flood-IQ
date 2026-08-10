"""
core/websocket_manager.py

Tracks connected WebSocket clients and broadcasts events to all of them.
Used by routers to push flood_zone_update, vehicle_rerouted,
prediction_update, and alert events to every connected dashboard/citizen
view in real time.
"""

import json
import logging
from typing import Any

try:
    from fastapi import WebSocket, WebSocketDisconnect
except ImportError:
    # FastAPI not installed (e.g. unit-test environment without the full
    # dependency set). The manager still loads; WebSocket type hints will
    # be unresolved but no runtime paths use them outside of actual HTTP
    # server contexts.
    WebSocket = object
    WebSocketDisconnect = Exception

logger = logging.getLogger("floodiq.websocket_manager")


class WebSocketManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("Client connected. Total: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("Client disconnected. Total: %d", len(self.active_connections))

    async def broadcast(self, event: str, data: dict[str, Any]):
        """Send an event to every connected client. Drops dead connections silently."""
        payload = json.dumps({"event": event, "data": data})
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception as e:
                logger.warning("Failed to send to a client, marking dead: %s", e)
                dead.append(connection)
        for d in dead:
            self.disconnect(d)

    async def send_personal(self, websocket: WebSocket, event: str, data: dict[str, Any]):
        payload = json.dumps({"event": event, "data": data})
        await websocket.send_text(payload)


# Module-level singleton shared across routers.
manager = WebSocketManager()
