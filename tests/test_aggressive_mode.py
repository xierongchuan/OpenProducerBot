import sys
import os
import time
import json
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.predict import should_call_ai

def test_aggressive_mode():
    print("🧪 Testing Aggressive Mode Logic...")

    # Scenario: Uptrend Pullback (Price > SMA, RSI = 50)
    # Standard Mode: Should return False (Auto-HOLD)
    # Aggressive Mode: Should return True (Call AI)

    analysis = {
        "symbol": "BTCUSDT",
        "rsi": 50,
        "current_price": 95000,
        "sma": 94000, # Uptrend
        "has_position": False
    }

    # Test 1: Standard Mode (AGGRESSIVE_MODE = False)
    with patch('src.config.AGGRESSIVE_MODE', False):
        result = should_call_ai(analysis)
        print(f"Standard Mode (RSI 50, Uptrend): {result}")
        if not result:
            print("✅ Standard Mode correctly skipped (Auto-HOLD)")
        else:
            print("❌ Standard Mode failed (Should skip)")

    # Test 2: Aggressive Mode (AGGRESSIVE_MODE = True)
    with patch('src.config.AGGRESSIVE_MODE', True):
        result = should_call_ai(analysis)
        print(f"Aggressive Mode (RSI 50, Uptrend): {result}")
        if result:
            print("✅ Aggressive Mode correctly triggered AI")
        else:
            print("❌ Aggressive Mode failed (Should trigger)")

if __name__ == "__main__":
    test_aggressive_mode()
