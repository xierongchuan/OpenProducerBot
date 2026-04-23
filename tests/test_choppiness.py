"""Unit tests for Choppiness Index (CHOP) indicator."""

import pytest
from src.core.indicators import calculate_chop, calculate_chop_series


def _make_klines(count, base_price=50000.0, volatility="normal"):
    """Generate synthetic kline data for testing."""
    import random
    random.seed(42)

    klines = []
    price = base_price
    trend = 0

    for i in range(count):
        if volatility == "flat":
            price = base_price
        elif volatility == "trending":
            trend = 50 if i % 20 < 10 else -50
            price += trend
        else:
            if i % 4 == 0:
                price += 30
            elif i % 4 == 2:
                price -= 30

        open_p = price + (random.random() - 0.5) * 10
        high = price + random.random() * 30 + 10
        low = price - random.random() * 30 - 10
        close = price + (random.random() - 0.5) * 15

        klines.append({
            "openPrice": open_p,
            "highPrice": high,
            "lowPrice": low,
            "closePrice": close,
        })

    return klines


class TestCalculateCHOP:

    def test_insufficient_data(self):
        """Should return 0 for insufficient data."""
        klines = _make_klines(5)
        result = calculate_chop(klines, period=14)
        assert result["chop"] == 0.0
        assert result["trend"] == "UNKNOWN"

    def test_exact_period_data(self):
        """Should work with exactly period+1 candles."""
        klines = _make_klines(15)
        result = calculate_chop(klines, period=14)
        assert 0.0 <= result["chop"] <= 100.0

    def test_flat_market_high_chop(self):
        """Flat market (no price movement) should return high CHOP."""
        base = 50000.0
        klines = [
            {
                "openPrice": base,
                "highPrice": base,
                "lowPrice": base,
                "closePrice": base,
            }
            for _ in range(50)
        ]
        result = calculate_chop(klines, period=14)
        assert result["chop"] == 100.0

    def test_trending_market_low_chop(self):
        """Strong trending market should return lower CHOP."""
        klines = _make_klines(50, volatility="trending")
        result = calculate_chop(klines, period=14)
        assert result["chop"] < 60

    def test_custom_period(self):
        """Should respect custom period parameter."""
        klines = _make_klines(50)
        result_14 = calculate_chop(klines, period=14)
        result_7 = calculate_chop(klines, period=7)
        assert 0.0 <= result_14["chop"] <= 100.0
        assert 0.0 <= result_7["chop"] <= 100.0

    def test_result_keys(self):
        """Result should contain all expected keys."""
        klines = _make_klines(50)
        result = calculate_chop(klines, period=14)
        assert set(result.keys()) == {"chop", "trend"}

    def test_chop_in_valid_range(self):
        """CHOP should always be in range [0, 100]."""
        klines = _make_klines(50)
        result = calculate_chop(klines, period=14)
        assert 0.0 <= result["chop"] <= 100.0

    def test_trend_classification(self):
        """Test trend classification based on CHOP values."""
        result = calculate_chop(_make_klines(50, volatility="trending"), period=14)
        if result["chop"] < 40:
            assert result["trend"] == "TRENDING"
        elif result["chop"] < 60:
            assert result["trend"] == "NEUTRAL"
        else:
            assert result["trend"] == "CHOPPING"


class TestCalculateCHOPSeries:

    def test_series_length_matches_klines(self):
        """Series length should match input klines length."""
        klines = _make_klines(30)
        result = calculate_chop_series(klines, period=14)
        assert len(result["chop"]) == 30
        assert len(result["trend"]) == 30

    def test_series_insufficient_data(self):
        """Should return zeros for insufficient data."""
        klines = _make_klines(5)
        result = calculate_chop_series(klines, period=14)
        assert all(v == 0.0 for v in result["chop"])
        assert all(t == "UNKNOWN" for t in result["trend"])

    def test_series_has_valid_trends(self):
        """Trend series should contain valid trend strings."""
        klines = _make_klines(50, volatility="trending")
        result = calculate_chop_series(klines, period=14)
        valid_trends = {"TRENDING", "NEUTRAL", "CHOPPING", "UNKNOWN"}
        for trend in result["trend"]:
            assert trend in valid_trends

    def test_series_chop_non_negative(self):
        """CHOP series should be non-negative."""
        klines = _make_klines(50)
        result = calculate_chop_series(klines, period=14)
        assert all(v >= 0.0 for v in result["chop"])

    def test_series_trending_classification(self):
        """Trending market should have TRENDING classification."""
        klines = _make_klines(100, volatility="trending")
        result = calculate_chop_series(klines, period=14)
        trending_count = sum(1 for t in result["trend"] if t == "TRENDING")
        assert trending_count > 0


class TestCHOPUsageExample:
    """Examples showing correct CHOP usage in strategies."""

    def test_filter_choppy_markets(self):
        """Example: avoid trading when CHOP > 60 (too choppy)."""
        klines = _make_klines(50)
        chop_result = calculate_chop(klines, period=14)

        if chop_result["chop"] > 60:
            trade_allowed = False
        else:
            trade_allowed = True

        assert isinstance(trade_allowed, bool)

    def test_regime_detection(self):
        """Example: detect market regime using CHOP."""
        klines = _make_klines(50)
        chop_result = calculate_chop(klines, period=14)

        if chop_result["chop"] < 40:
            regime = "TRENDING"
        elif chop_result["chop"] < 60:
            regime = "NEUTRAL"
        else:
            regime = "CHOPPING"

        assert regime in ("TRENDING", "NEUTRAL", "CHOPPING")

    def test_combine_with_other_indicators(self):
        """Example: combine CHOP with ADX for regime detection."""
        from src.core.indicators import calculate_adx
        klines = _make_klines(50, volatility="trending")
        chop_result = calculate_chop(klines, period=14)
        adx_result = calculate_adx(klines, period=14)

        is_trending = chop_result["chop"] < 60 and adx_result["adx"] > 20
        assert isinstance(is_trending, bool)