"""
Abstract WebSocket provider for real-time market data.
Provides unified interface for WebSocket connections across different exchanges.

Этот модуль определяет контракт для WebSocket провайдеров.
При добавлении новой биржи нужно реализовать этот интерфейс.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
import threading


class WebSocketState(Enum):
    """Состояние WebSocket соединения"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class WebSocketConfig:
    """Конфигурация WebSocket соединения"""
    ws_url: str
    reconnect_delay: float = 1.0
    max_reconnect_delay: float = 60.0
    ping_interval: float = 20.0
    cache_size: int = 600  # Количество свечей в кэше


class WebSocketProvider(ABC):
    """
    Абстрактный провайдер для получения real-time данных через WebSocket.

    Каждая биржа должна реализовать этот интерфейс.
    """

    def __init__(self, config: Optional[WebSocketConfig] = None):
        self._config = config
        self._state = WebSocketState.DISCONNECTED
        self._symbols: List[str] = []
        self._interval: str = "5m"
        self._running = False
        self._lock = threading.RLock()

        # Callback для обработки событий
        self._on_kline_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
        self._on_ticker_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
        self._on_error_callback: Optional[Callable[[str], None]] = None
        self._on_connect_callback: Optional[Callable[[], None]] = None
        self._on_disconnect_callback: Optional[Callable[[], None]] = None

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def state(self) -> WebSocketState:
        """Текущее состояние соединения"""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Проверка подключения"""
        return self._state == WebSocketState.CONNECTED

    @property
    def symbols(self) -> List[str]:
        """Список отслеживаемых символов"""
        return self._symbols.copy()

    # =========================================================================
    # Abstract methods - должны быть реализованы в подклассах
    # =========================================================================

    @abstractmethod
    def start(self, symbols: List[str], interval: str = "5m") -> None:
        """
        Запустить WebSocket провайдер.

        Args:
            symbols: Список символов для подписки
            interval: Интервал свечей (1m, 5m, 15m, etc.)
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Остановить WebSocket провайдер.
        """
        pass

    @abstractmethod
    def get_klines(self, symbol: str, limit: int = 288) -> List[Dict[str, Any]]:
        """
        Получить свечи из кэша.

        Args:
            symbol: Символ
            limit: Количество свечей

        Returns:
            Список свечей в универсальном формате
        """
        pass

    @abstractmethod
    def is_ready(self, symbol: str) -> bool:
        """
        Проверить готовность данных для символа.

        Args:
            symbol: Символ

        Returns:
            True если данные готовы
        """
        pass

    @abstractmethod
    def subscribe(self, symbols: List[str], interval: Optional[str] = None) -> None:
        """
        Подписаться на новые символы.

        Args:
            symbols: Список символов
            interval: Интервал (если отличается от текущего)
        """
        pass

    @abstractmethod
    def unsubscribe(self, symbols: List[str]) -> None:
        """
        Отписаться от символов.

        Args:
            symbols: Список символов
        """
        pass

    # =========================================================================
    # Callback methods - могут быть переопределены для кастомизации
    # =========================================================================

    def on_kline(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """
        Установить callback для обработки новых свечей.

        Args:
            callback: Функция(symbol: str, kline: dict)
        """
        self._on_kline_callback = callback

    def on_ticker(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """
        Установить callback для обработки тикера.

        Args:
            callback: Функция(symbol: str, ticker: dict)
        """
        self._on_ticker_callback = callback

    def on_error(self, callback: Callable[[str], None]) -> None:
        """
        Установить callback для обработки ошибок.

        Args:
            callback: Функция(error_message: str)
        """
        self._on_error_callback = callback

    def on_connect(self, callback: Callable[[], None]) -> None:
        """
        Установить callback при подключении.

        Args:
            callback: Функция()
        """
        self._on_connect_callback = callback

    def on_disconnect(self, callback: Callable[[], None]) -> None:
        """
        Установить callback при отключении.

        Args:
            callback: Функция()
        """
        self._on_disconnect_callback = callback

    # =========================================================================
    # Protected methods - утилиты для подклассов
    # =========================================================================

    def _set_state(self, state: WebSocketState) -> None:
        """Установить состояние соединения"""
        with self._lock:
            old_state = self._state
            self._state = state

            # Вызов callback при изменении состояния
            if state == WebSocketState.CONNECTED and old_state != WebSocketState.CONNECTED:
                if self._on_connect_callback:
                    try:
                        self._on_connect_callback()
                    except Exception:
                        pass
            elif state == WebSocketState.DISCONNECTED and old_state == WebSocketState.CONNECTED:
                if self._on_disconnect_callback:
                    try:
                        self._on_disconnect_callback()
                    except Exception:
                        pass

    def _notify_kline(self, symbol: str, kline: Dict[str, Any]) -> None:
        """Уведомить о новой свече"""
        if self._on_kline_callback:
            try:
                self._on_kline_callback(symbol, kline)
            except Exception:
                pass

    def _notify_ticker(self, symbol: str, ticker: Dict[str, Any]) -> None:
        """Уведомить о тикере"""
        if self._on_ticker_callback:
            try:
                self._on_ticker_callback(symbol, ticker)
            except Exception:
                pass

    def _notify_error(self, error: str) -> None:
        """Уведомить об ошибке"""
        if self._on_error_callback:
            try:
                self._on_error_callback(error)
            except Exception:
                pass

    def _normalize_symbol(self, symbol: str) -> str:
        """
        Нормализовать символ (упрощенная версия).
        Переопределить в подклассе для специфичной логики.
        """
        return symbol.replace("/", "").replace("-", "")

    def _format_symbol(self, symbol: str) -> str:
        """
        Форматировать символ обратно.
        Переопределить в подклассе для специфичной логики.
        """
        return symbol
