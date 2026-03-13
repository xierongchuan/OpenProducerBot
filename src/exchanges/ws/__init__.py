"""
WebSocket providers for different exchanges.

Этот модуль экспортирует базовые классы и фабрику для создания провайдеров.
"""

from .base import (
    WebSocketProvider,
    WebSocketConfig,
    WebSocketState,
)

__all__ = [
    "WebSocketProvider",
    "WebSocketConfig",
    "WebSocketState",
]
