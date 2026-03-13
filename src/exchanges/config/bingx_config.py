"""
BingX exchange configuration.
"""

import os
from typing import Optional, Dict

from .base import ExchangeConfig


class BingXConfig(ExchangeConfig):
    """
    Конфигурация для BingX биржи.
    """

    @property
    def name(self) -> str:
        return "bingx"

    @property
    def env_prefix(self) -> str:
        return "BINGX"

    @property
    def api_key(self) -> Optional[str]:
        return self._api_key

    @property
    def secret_key(self) -> Optional[str]:
        return self._secret_key

    @property
    def base_url(self) -> str:
        if self._is_demo:
            return "https://open-api-vst.bingx.com"
        return "https://open-api.bingx.com"

    @property
    def ws_url(self) -> str:
        # BingX WebSocket URL одинаковый для demo и real (публичные данные)
        return "wss://open-api-ws.bingx.com/market"

    @property
    def testnet_url(self) -> str:
        return "https://open-api-vst.bingx.com"

    @property
    def supported_intervals(self) -> Dict[str, str]:
        """Маппинг интервалов BingX"""
        return {
            "1m": "1min",
            "3m": "3min",
            "5m": "5min",
            "15m": "15min",
            "30m": "30min",
            "1h": "1hour",
            "2h": "2hour",
            "4h": "4hour",
            "6h": "6hour",
            "12h": "12hour",
            "1d": "1day",
            "1w": "1week",
            "1M": "1month",
        }

    @property
    def default_leverage(self) -> int:
        return 10

    @property
    def max_leverage(self) -> int:
        return 100  # BingX max leverage

    @property
    def positions_cache_ttl(self) -> int:
        return 10

    @property
    def balance_cache_ttl(self) -> int:
        return 10

    def _load_from_env(self) -> None:
        """Загрузить настройки из переменных окружения"""
        self._api_key = os.getenv("BINGX_API_KEY", "")
        self._secret_key = os.getenv("BINGX_SECRET_KEY", "")

        # Также поддерживаем старые переменные (для совместимости)
        if not self._api_key:
            self._api_key = os.getenv("BINGX_KEY", "")
        if not self._secret_key:
            self._secret_key = os.getenv("BINGX_SECRET", "")

    def __init__(self, is_demo: bool = False):
        super().__init__(is_demo)

    def to_dict(self) -> dict:
        base = super().to_dict()
        base.update({
            "intervals": list(self.supported_intervals.keys()),
        })
        return base


