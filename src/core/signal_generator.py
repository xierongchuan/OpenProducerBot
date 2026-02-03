"""
Deterministic Signal Generator for HYBRID mode.
Generates trading signals based on technical indicators with scoring system.
AI only confirms/rejects these signals - it cannot generate its own.
"""

from src.config import BOT_CONFIG
from src.utils.logger import info, warning


class SignalGenerator:
    """
    Детерминированный генератор сигналов.

    Система очков:
    - EMA alignment (EMA9 > EMA21 для LONG): +2
    - RSI в благоприятной зоне: +1
    - Volume подтверждение: +1
    - Близость к S/R уровню: +2

    Минимум очков для сигнала: 4 (настраивается)
    """

    def __init__(self):
        self.settings = BOT_CONFIG.get("HYBRID_SETTINGS", {})
        self.rules = self.settings.get("signal_rules", {})

    def generate_signal(self, analysis: dict) -> dict:
        """
        Генерирует детерминированный сигнал на основе анализа.

        Returns:
            {
                "signal": "BUY" | "SELL" | "HOLD",
                "score": int,
                "max_score": int,
                "reasons": list[str],
                "filters_passed": bool,
                "details": dict
            }
        """
        score = 0
        max_score = 0
        reasons = []
        details = {}

        # Извлекаем данные из анализа
        global_trend = analysis.get("global_trend", "N/A")
        local_trend = analysis.get("local_trend", "N/A")
        rsi = analysis.get("rsi", 50)
        volume_ratio = analysis.get("volume_ratio", 1.0)
        current_price = analysis.get("current_price", 0)
        support = analysis.get("support", 0)
        resistance = analysis.get("resistance", 0)
        ema9 = analysis.get("ema9", 0)
        ema21 = analysis.get("ema21", 0)

        # Веса из конфига
        ema_weight = self.rules.get("ema_cross_weight", 2)
        rsi_weight = self.rules.get("rsi_zone_weight", 1)
        volume_weight = self.rules.get("volume_weight", 1)
        sr_weight = self.rules.get("sr_weight", 2)

        max_score = ema_weight + rsi_weight + volume_weight + sr_weight

        # Пороги
        min_volume = self.rules.get("min_volume_ratio", 0.7)
        rsi_long_max = self.rules.get("rsi_long_max", 65)
        rsi_long_min = self.rules.get("rsi_long_min", 35)
        rsi_short_max = self.rules.get("rsi_short_max", 65)
        rsi_short_min = self.rules.get("rsi_short_min", 35)
        sr_proximity_pct = self.rules.get("sr_proximity_pct", 1.0)
        min_score = self.rules.get("min_score_for_signal", 4)

        # === ОПРЕДЕЛЯЕМ НАПРАВЛЕНИЕ ===

        long_score = 0
        short_score = 0
        long_reasons = []
        short_reasons = []

        # 1. EMA Alignment
        if ema9 > 0 and ema21 > 0:
            if ema9 > ema21:
                long_score += ema_weight
                long_reasons.append(f"EMA9 > EMA21 (+{ema_weight})")
            elif ema9 < ema21:
                short_score += ema_weight
                short_reasons.append(f"EMA9 < EMA21 (+{ema_weight})")

        # 2. Trend Alignment (опционально)
        if self.rules.get("trend_alignment_required", True):
            if global_trend == "UP" and local_trend == "BULLISH":
                long_score += 1
                long_reasons.append("Trend aligned UP (+1)")
            elif global_trend == "DOWN" and local_trend == "BEARISH":
                short_score += 1
                short_reasons.append("Trend aligned DOWN (+1)")

        # 3. RSI Zone
        if rsi_long_min <= rsi <= rsi_long_max:
            long_score += rsi_weight
            long_reasons.append(f"RSI {rsi:.1f} in LONG zone [{rsi_long_min}-{rsi_long_max}] (+{rsi_weight})")

        if rsi_short_min <= rsi <= rsi_short_max:
            short_score += rsi_weight
            short_reasons.append(f"RSI {rsi:.1f} in SHORT zone [{rsi_short_min}-{rsi_short_max}] (+{rsi_weight})")

        # 4. Volume Confirmation
        if volume_ratio >= min_volume:
            # Добавляем к обоим, т.к. volume подтверждает любое движение
            long_score += volume_weight
            short_score += volume_weight
            long_reasons.append(f"Volume {volume_ratio:.2f}x >= {min_volume}x (+{volume_weight})")
            short_reasons.append(f"Volume {volume_ratio:.2f}x >= {min_volume}x (+{volume_weight})")

        # 5. S/R Proximity
        if current_price > 0 and support > 0 and resistance > 0:
            support_dist_pct = abs((current_price - support) / current_price * 100)
            resistance_dist_pct = abs((resistance - current_price) / current_price * 100)

            # Близко к support = хорошо для LONG
            if support_dist_pct <= sr_proximity_pct:
                long_score += sr_weight
                long_reasons.append(f"Near support {support:.2f} ({support_dist_pct:.2f}%) (+{sr_weight})")

            # Близко к resistance = хорошо для SHORT
            if resistance_dist_pct <= sr_proximity_pct:
                short_score += sr_weight
                short_reasons.append(f"Near resistance {resistance:.2f} ({resistance_dist_pct:.2f}%) (+{sr_weight})")

        # === ВЫБИРАЕМ СИГНАЛ ===

        signal = "HOLD"
        score = 0
        reasons = []

        # Выбираем направление с большим счётом
        if long_score >= min_score and long_score > short_score:
            signal = "BUY"
            score = long_score
            reasons = long_reasons
        elif short_score >= min_score and short_score > long_score:
            signal = "SELL"
            score = short_score
            reasons = short_reasons
        elif long_score >= min_score and short_score >= min_score:
            # Оба направления имеют достаточно очков - конфликт, HOLD
            signal = "HOLD"
            score = max(long_score, short_score)
            reasons = ["CONFLICT: Both directions have signals - staying out"]
        else:
            signal = "HOLD"
            score = max(long_score, short_score)
            reasons = [f"Score {score}/{min_score} - not enough for signal"]

        details = {
            "long_score": long_score,
            "short_score": short_score,
            "long_reasons": long_reasons,
            "short_reasons": short_reasons,
            "min_score_required": min_score,
            "ema9": ema9,
            "ema21": ema21,
            "rsi": rsi,
            "volume_ratio": volume_ratio,
            "support": support,
            "resistance": resistance
        }

        result = {
            "signal": signal,
            "score": score,
            "max_score": max_score,
            "reasons": reasons,
            "filters_passed": score >= min_score,
            "details": details
        }

        # Логируем результат
        if signal != "HOLD":
            info(f"📊 [SIGNAL] {signal} | Score: {score}/{max_score} | Reasons: {', '.join(reasons[:3])}")
        else:
            info(f"📊 [SIGNAL] HOLD | Score: {score}/{min_score} required")

        return result

    def should_close_position(self, analysis: dict, position: dict) -> dict:
        """
        Детерминированная проверка на закрытие позиции.

        Returns:
            {
                "should_close": bool,
                "reason": str,
                "urgency": "low" | "medium" | "high"
            }
        """
        if not position:
            return {"should_close": False, "reason": "No position", "urgency": "low"}

        pos_type = position.get("type", "").upper()
        entry_price = float(position.get("entry", position.get("avgPrice", 0)))
        current_price = analysis.get("current_price", 0)
        rsi = analysis.get("rsi", 50)

        if entry_price <= 0 or current_price <= 0:
            return {"should_close": False, "reason": "Invalid prices", "urgency": "low"}

        # Рассчитываем P/L
        if pos_type == "BUY":
            pnl_pct = (current_price - entry_price) / entry_price * 100
        else:
            pnl_pct = (entry_price - current_price) / entry_price * 100

        # === ПРАВИЛА ЗАКРЫТИЯ ===

        # 1. RSI экстремум против позиции
        if pos_type == "BUY" and rsi > 80:
            return {
                "should_close": True,
                "reason": f"RSI {rsi:.1f} > 80 (overbought) - LONG exit signal",
                "urgency": "high"
            }

        if pos_type == "SELL" and rsi < 20:
            return {
                "should_close": True,
                "reason": f"RSI {rsi:.1f} < 20 (oversold) - SHORT exit signal",
                "urgency": "high"
            }

        # 2. Хорошая прибыль + RSI начинает разворачиваться
        if pnl_pct >= 2.0:
            if pos_type == "BUY" and rsi > 70:
                return {
                    "should_close": True,
                    "reason": f"Profit {pnl_pct:.2f}% + RSI {rsi:.1f} > 70 - take profit",
                    "urgency": "medium"
                }
            if pos_type == "SELL" and rsi < 30:
                return {
                    "should_close": True,
                    "reason": f"Profit {pnl_pct:.2f}% + RSI {rsi:.1f} < 30 - take profit",
                    "urgency": "medium"
                }

        # 3. Разворот тренда против позиции
        global_trend = analysis.get("global_trend", "N/A")
        local_trend = analysis.get("local_trend", "N/A")

        if pos_type == "BUY" and global_trend == "DOWN" and local_trend == "BEARISH":
            if pnl_pct < 0:  # В минусе + тренд против
                return {
                    "should_close": True,
                    "reason": f"Trend reversed to DOWN + loss {pnl_pct:.2f}%",
                    "urgency": "high"
                }

        if pos_type == "SELL" and global_trend == "UP" and local_trend == "BULLISH":
            if pnl_pct < 0:
                return {
                    "should_close": True,
                    "reason": f"Trend reversed to UP + loss {pnl_pct:.2f}%",
                    "urgency": "high"
                }

        return {"should_close": False, "reason": "No exit signal", "urgency": "low"}


# Singleton instance
_generator = None

def get_signal_generator() -> SignalGenerator:
    global _generator
    if _generator is None:
        _generator = SignalGenerator()
    return _generator


def generate_signal(analysis: dict) -> dict:
    """Convenience function for generating signals."""
    return get_signal_generator().generate_signal(analysis)


def should_close(analysis: dict, position: dict) -> dict:
    """Convenience function for close check."""
    return get_signal_generator().should_close_position(analysis, position)
