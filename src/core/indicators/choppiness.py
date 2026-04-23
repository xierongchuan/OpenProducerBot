"""Индикатор Choppiness Index (CHOP) — измеряет рыночную волатильность и боковое движение."""

import math
from typing import Dict, List


def calculate_chop(klines: List[Dict], period: int = 14) -> Dict:
    """
    Рассчитывает Choppiness Index (CHOP) для последней точки.
    CHOP показывает, насколько рынок "застревает" в боковом движении vs тренде.
    Значение: 0-100 (ниже = более трендовый, выше = более боковой/вялый).

    Args:
        klines: Список свечей с highPrice, lowPrice, closePrice
        period: Период расчёта (по умолчанию 14)

    Returns:
        {"chop": float, "trend": str}
    """
    if len(klines) < period + 1:
        return {"chop": 0.0, "trend": "UNKNOWN"}

    tr_values = []
    for i in range(1, len(klines)):
        high = klines[i]["highPrice"]
        low = klines[i]["lowPrice"]
        prev_close = klines[i - 1]["closePrice"]

        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_values.append(tr)

    if len(tr_values) < period:
        return {"chop": 0.0, "trend": "UNKNOWN"}

    sum_tr = sum(tr_values[-period:])

    max_high = max(klines[i]["highPrice"] for i in range(-period, 0))
    min_low = min(klines[i]["lowPrice"] for i in range(-period, 0))
    price_range = max_high - min_low

    if price_range == 0 or sum_tr == 0:
        return {"chop": 100.0, "trend": "UNKNOWN"}

    chop = 100 * (math.log10(sum_tr / price_range) / math.log10(period))
    chop = max(0.0, min(100.0, round(chop, 2)))

    if chop < 40:
        trend = "TRENDING"
    elif chop < 60:
        trend = "NEUTRAL"
    else:
        trend = "CHOPPING"

    return {"chop": chop, "trend": trend}


def calculate_chop_series(klines: List[Dict], period: int = 14) -> Dict[str, List[float]]:
    """
    Рассчитывает полную историю CHOP для визуализации.
    Возвращает массивы значений, выровненные по времени с входными данными.

    Args:
        klines: Список свечей с highPrice, lowPrice, closePrice
        period: Период расчёта (по умолчанию 14)

    Returns:
        {"chop": List[float], "trend": List[str]}
    """
    n = len(klines)
    if n < period + 1:
        return {"chop": [0.0] * n, "trend": ["UNKNOWN"] * n}

    tr_values = []
    for i in range(1, n):
        high = klines[i]["highPrice"]
        low = klines[i]["lowPrice"]
        prev_close = klines[i - 1]["closePrice"]

        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_values.append(tr)

    chop_series = [0.0] * n
    trend_series = ["UNKNOWN"] * n

    for i in range(period, n):
        sum_tr = sum(tr_values[i - period:i])

        window = klines[i - period + 1:i + 1]
        max_high = max(c["highPrice"] for c in window)
        min_low = min(c["lowPrice"] for c in window)
        price_range = max_high - min_low

        if price_range == 0 or sum_tr == 0:
            chop = 100.0
        else:
            chop = 100 * (math.log10(sum_tr / price_range) / math.log10(period))
            chop = max(0.0, min(100.0, round(chop, 2)))

        chop_series[i] = chop

        if chop < 40:
            trend_series[i] = "TRENDING"
        elif chop < 60:
            trend_series[i] = "NEUTRAL"
        else:
            trend_series[i] = "CHOPPING"

    return {"chop": chop_series, "trend": trend_series}