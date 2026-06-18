"""Compatibility wrapper for the BingX WebSocket market-data provider.

New code should import from src.exchanges.bingx_ws_data_provider.
"""

import sys

from src.exchanges import bingx_ws_data_provider as _bingx_ws_data_provider


sys.modules[__name__] = _bingx_ws_data_provider
