"""Communication modules for evolution suite."""

from evolution_suite.comms.file_channel import FileChannel
from evolution_suite.comms.websocket import WebSocketManager

__all__ = ["FileChannel", "WebSocketManager"]
