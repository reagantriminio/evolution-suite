"""WebSocket manager for real-time frontend communication."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Callable

from fastapi import WebSocket, WebSocketDisconnect


class WebSocketManager:
    """Manages WebSocket connections and broadcasts events."""

    def __init__(self):
        self.connections: list[WebSocket] = []
        self._lock = asyncio.Lock()
        self._message_handlers: dict[str, Callable] = {}

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.connections.append(websocket)

        # Send connection confirmation
        await self.send_to(websocket, {
            "type": "connected",
            "timestamp": datetime.now().isoformat(),
            "connectionCount": len(self.connections),
        })

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            if websocket in self.connections:
                self.connections.remove(websocket)

    async def send_to(self, websocket: WebSocket, message: dict[str, Any]) -> None:
        """Send a message to a specific connection."""
        try:
            await websocket.send_json(message)
        except Exception:
            await self.disconnect(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connections."""
        if not self.connections:
            return

        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.now().isoformat()

        # Send to all connections, removing dead ones
        dead_connections = []
        for connection in self.connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)

        # Clean up dead connections
        if dead_connections:
            async with self._lock:
                for conn in dead_connections:
                    if conn in self.connections:
                        self.connections.remove(conn)

    def register_handler(self, message_type: str, handler: Callable) -> None:
        """Register a handler for a specific message type."""
        self._message_handlers[message_type] = handler

    async def handle_message(self, websocket: WebSocket, data: dict[str, Any]) -> None:
        """Handle an incoming message from a client."""
        message_type = data.get("type")
        if not message_type:
            await self.send_to(websocket, {
                "type": "error",
                "error": "Message must have a 'type' field",
            })
            return

        handler = self._message_handlers.get(message_type)
        if handler:
            try:
                result = await handler(data)
                if result:
                    await self.send_to(websocket, result)
            except Exception as e:
                await self.send_to(websocket, {
                    "type": "error",
                    "error": str(e),
                    "originalType": message_type,
                })
        else:
            await self.send_to(websocket, {
                "type": "error",
                "error": f"Unknown message type: {message_type}",
            })

    async def listen(self, websocket: WebSocket) -> None:
        """Listen for messages from a client."""
        try:
            while True:
                data = await websocket.receive_json()
                await self.handle_message(websocket, data)
        except WebSocketDisconnect:
            await self.disconnect(websocket)
        except Exception:
            await self.disconnect(websocket)

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.connections)

    def create_event_callback(self) -> Callable[[dict[str, Any]], None]:
        """Create a callback that broadcasts events."""
        def callback(event: dict[str, Any]) -> None:
            asyncio.create_task(self.broadcast(event))
        return callback
