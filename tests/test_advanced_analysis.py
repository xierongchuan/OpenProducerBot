import sys
import os
import json

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.analyzer import analyze_symbol
from src.config import ENABLE_ADVANCED_ANALYSIS

def test_advanced_analysis():
    print(f"🧪 Testing Advanced Analysis (Enabled: {ENABLE_ADVANCED_ANALYSIS})...")

    # Mock data
    prices = []
    base_price = 50000
    for i in range(100):
        prices.append({
            "closePrice": base_price + (i % 10) * 100, # Zigzag
            "volume": 1000 + (i % 5) * 500
        })

    # Mock collector.fetch_prices
    # We need to patch collector.fetch_prices or just call analyze_symbol if it accepts data?
    # analyze_symbol calls fetch_prices internally.
    # Let's patch it.

    from unittest.mock import patch, mock_open

    # Mock json.load to return our prices
    with patch("builtins.open", mock_open(read_data="data")) as mock_file:
        with patch("json.load") as mock_json:
            # First call is prices, second is news
            mock_json.side_effect = [prices, []]

            result = analyze_symbol("BTCUSDT")

            prompt = result["prompt"]
            print("\n📝 Generated Prompt:")
            print("-" * 40)
            print(prompt)
            print("-" * 40)

            if "РЫНОЧНАЯ СТРУКТУРА И ПСИХОЛОГИЯ" in prompt:
                print("✅ Advanced Analysis section found!")
            else:
                print("❌ Advanced Analysis section MISSING!")

            if "ПСИХОЛОГИЧЕСКИЙ АНАЛИЗ" in prompt:
                print("✅ Psychology section found!")
            else:
                print("❌ Psychology section MISSING!")

if __name__ == "__main__":
    test_advanced_analysis()
