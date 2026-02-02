from src.config import EXCHANGE
from .bingx_client import BingXClient
from src.utils.logger import info

def get_exchange_client():
    """
    Factory function to get the appropriate exchange client instance.
    """
    exchange = EXCHANGE.lower()

    if exchange == "bingx":
        # info("🏭 Using BingX Exchange Client")
        return BingXClient()
    else:
        raise ValueError(f"Unknown exchange: {EXCHANGE}")
