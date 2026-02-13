"""
WebSocket handler for real-time sensor data streaming.

Manages multiple simultaneous client connections and broadcasts
sensor updates at configurable intervals.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from models import (
    SensorData,
    GridData,
    ParticleData,
    GlobalStats,
    ForecastPoint,
    WebSocketMessage,
)
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """
    Manages WebSocket connections for broadcasting real-time updates
    to all connected clients.
    """

    def __init__(self) -> None:
        self._active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self._active_connections.add(websocket)
        logger.info(
            "WebSocket client connected. Total clients: %d",
            len(self._active_connections),
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from the active set."""
        async with self._lock:
            self._active_connections.discard(websocket)
        logger.info(
            "WebSocket client disconnected. Total clients: %d",
            len(self._active_connections),
        )

    async def broadcast(self, message: str) -> None:
        """
        Send a message to all connected clients.
        Disconnects clients that fail to receive.
        """
        dead_connections: List[WebSocket] = []

        async with self._lock:
            connections = list(self._active_connections)

        for websocket in connections:
            try:
                await websocket.send_text(message)
            except Exception:
                dead_connections.append(websocket)

        # Clean up dead connections
        if dead_connections:
            async with self._lock:
                for ws in dead_connections:
                    self._active_connections.discard(ws)
            logger.info("Removed %d dead WebSocket connections", len(dead_connections))

    @property
    def client_count(self) -> int:
        """Number of currently connected clients."""
        return len(self._active_connections)


# Singleton connection manager
manager = ConnectionManager()

# Shared state reference - injected by main.py
_state: dict = {}


def set_state(state: dict) -> None:
    """Called by main.py to inject the shared state dict."""
    global _state
    _state = state


def _build_ws_message() -> str:
    """Build a WebSocketMessage JSON string from current state."""
    sensors_dict: Dict[str, SensorData] = _state.get("sensors", {})
    sensors_list = list(sensors_dict.values())
    grid: Optional[GridData] = _state.get("grid")
    particles: List[ParticleData] = _state.get("particles", [])
    stats: GlobalStats = _state.get("stats", GlobalStats())
    forecast: List[ForecastPoint] = _state.get("forecast", [])

    message = WebSocketMessage(
        type="sensor_update",
        timestamp=datetime.now(timezone.utc).isoformat(),
        sensors=sensors_list,
        grid=grid,
        particles=particles,
        stats=stats,
        forecast=forecast,
    )

    return message.model_dump_json()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time sensor data.

    On connect: immediately sends current state.
    Then sends updates every SENSOR_UPDATE_INTERVAL seconds.
    """
    await manager.connect(websocket)

    try:
        # Send initial state immediately
        initial_message = _build_ws_message()
        await websocket.send_text(initial_message)

        # Keep connection alive and send periodic updates
        while True:
            try:
                # Wait for either a client message or timeout
                # This allows us to detect disconnections via ping/pong
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=float(settings.SENSOR_UPDATE_INTERVAL),
                )

                # Handle client messages (e.g., ping)
                if data == "ping":
                    await websocket.send_text('{"type": "pong"}')

            except asyncio.TimeoutError:
                # Timeout is normal - send an update
                try:
                    update = _build_ws_message()
                    await websocket.send_text(update)
                except Exception:
                    break

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error("WebSocket error: %s", exc)
    finally:
        await manager.disconnect(websocket)


async def broadcast_update() -> None:
    """
    Broadcast the current state to all connected WebSocket clients.
    Called by the main simulation loop after each update.
    """
    if manager.client_count == 0:
        return

    try:
        message = _build_ws_message()
        await manager.broadcast(message)
    except Exception as exc:
        logger.error("Broadcast error: %s", exc)
