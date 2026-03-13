"""
Factory for creating exchange client instances.

Этот модуль предоставляет унифицированный способ создания клиентов бирж.
"""

import logging
import traceback
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .exchange_client import ExchangeClient


logger = logging.getLogger(__name__)


_client_instance: Optional["ExchangeClient"] = None


def get_exchange_client(use_new_impl: bool = True):
    """
    Factory function to get the appropriate exchange client instance.

    Args:
        use_new_impl: Использовать новую реализацию (по умолчанию True).

    Returns:
        Экземпляр ExchangeClient (singleton per process)

    Raises:
        ValueError: Если биржа не поддерживается
    """
    global _client_instance

    # Если инстанс уже создан - возвращаем его
    if _client_instance is not None:
        return _client_instance

    from src.config import EXCHANGE, MODE

    exchange = EXCHANGE.lower()

    if use_new_impl:
        # Новая реализация (с использованием SOLID архитектуры)
        try:
            from .config.base import ConfigFactory

            # Инициализация конфигурации
            config = ConfigFactory.create(exchange, is_demo=(MODE == "demo"))

            # Выбор клиента
            if exchange == "bingx":
                from .impl.bingx_client import BingXClient
                _client_instance = BingXClient(config)
            else:
                raise ValueError(f"Unknown exchange: {EXCHANGE}")

        except Exception as e:
            # Fallback на новую реализацию без конфига
            logger.warning(f"⚠️ New implementation failed for {exchange}, falling back: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            if exchange == "bingx":
                from .impl.bingx_client import BingXClient
                _client_instance = BingXClient()
            else:
                raise ValueError(f"Unknown exchange: {EXCHANGE}")
    else:
        # Старая реализация (для обратной совместимости)
        if exchange == "bingx":
            from .bingx_client import BingXClient
            _client_instance = BingXClient()
        else:
            raise ValueError(f"Unknown exchange: {EXCHANGE}")

    return _client_instance


def reset_client():
    """
    Сбросить singleton экземпляр (для тестирования или смены биржи).
    """
    global _client_instance
    _client_instance = None


# Alias
__all__ = [
    "get_exchange_client",
    "reset_client",
]
