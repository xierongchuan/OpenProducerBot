import math
from typing import List, Dict, Any, Tuple
from ..core.predict import get_prediction
from ..core.signals.macdx import MacdxSignalGenerator

class SignalGenerator:
    """Генерирует сигналы для детерминированных стратегий, таких как MACDX."""

    def __init__(self, strategy: str = "MACDX"):
        self.strategy = strategy
        # Параметры из конфига MACDX
        self.rules = {
            "macd_cross_weight": 2,
            "rsi_zone_weight": 2,
            "ema_alignment_weight": 2,
            "not_sideways_weight": 1,
            "no_exhaustion_weight": 1,
            "volume_weight": 1,
            "min_score": 4,
            "min_confirmations": 3,
            "rsi_long_min": 25,
            "rsi_long_max": 65,
            "rsi_short_min": 35,
            "rsi_short_max": 75,
            "bb_width_threshold": 0.5,
            "adx_threshold": 20,
            "atr_ratio_threshold": 0.01,
            "volume_ratio_threshold": 0.8,
            "counter_trend_ema_threshold": 1.0
        }

    def calculate_indicators(self, klines: List[Dict[str, Any]], index: int) -> Dict[str, Any]:
        """Рассчитывает индикаторы на основе последних свечей."""
        if index < 30:  # Минимум данных
            return {}

        closes = [k["closePrice"] for k in klines[:index+1]]
        highs = [k["highPrice"] for k in klines[:index+1]]
        lows = [k["lowPrice"] for k in klines[:index+1]]
        volumes = [k["volume"] for k in klines[:index+1]]

        # RSI (14)
        rsi = self._calculate_rsi(closes, 14)

        # EMA9, EMA21
        ema9 = self._calculate_ema(closes, 9)
        ema21 = self._calculate_ema(closes, 21)

        # MACD (12,26,9)
        macd_line, macd_signal, macd_hist = self._calculate_macd(closes)
        macd_hist_prev = self._calculate_macd_hist_prev(closes[:-1]) if len(closes) > 1 else 0

        # BB width
        bb_width = self._calculate_bb_width(closes, 20)

        # ADX (14)
        adx = self._calculate_adx(highs, lows, closes, 14)

        # ATR (14)
        atr = self._calculate_atr(highs, lows, closes, 14)
        atr_ratio = atr / closes[-1] if closes[-1] > 0 else 0

        # Volume ratio
        volume_ratio = volumes[-1] / (sum(volumes[-20:]) / 20) if len(volumes) >= 20 else 1

        return {
            "rsi": rsi,
            "rsi_values": self._rsi_values(closes, 14),
            "ema9": ema9,
            "ema21": ema21,
            "macd_line": macd_line,
            "macd_signal": macd_signal,
            "macd_hist": macd_hist,
            "macd_hist_prev": macd_hist_prev,
            "bb_width": bb_width,
            "adx": adx,
            "atr": atr,
            "atr_ratio": atr_ratio,
            "volume_ratio": volume_ratio,
            "close_prices": closes
        }

    def generate_signal(self, klines: List[Dict[str, Any]], index: int) -> Dict[str, Any]:
        """Генерирует сигнал на основе индикаторов."""
        analysis = self.calculate_indicators(klines, index)
        if not analysis:
            return {"action": "HOLD", "reason": "Недостаточно данных"}

        # Логика скоринга MACDX
        rsi = analysis["rsi"]
        ema9 = analysis["ema9"]
        ema21 = analysis["ema21"]
        macd_hist = analysis["macd_hist"]
        macd_hist_prev = analysis["macd_hist_prev"]
        bb_width = analysis["bb_width"]
        adx = analysis["adx"]
        atr_ratio = analysis["atr_ratio"]
        volume_ratio = analysis["volume_ratio"]

        # Фильтры
        # if atr_ratio < self.rules["atr_ratio_threshold"]:
        #     return {"action": "HOLD", "reason": f"Низкая волатильность: ATR ratio {atr_ratio:.4f} < {self.rules['atr_ratio_threshold']}"}
        if volume_ratio < self.rules["volume_ratio_threshold"] and self.rules.get("enable_volume_filter", True):
            return {"action": "HOLD", "reason": "Низкий объем"}

        # MACD crossover
        macd_cross_long = macd_hist_prev <= 0 and macd_hist > 0
        macd_cross_short = macd_hist_prev >= 0 and macd_hist < 0

        if not macd_cross_long and not macd_cross_short:
            return {"action": "HOLD", "reason": "Нет MACD crossover"}

        long_score = short_score = 0
        long_confirmations = short_confirmations = 0

        # RSI zone
        if macd_cross_long:
            if self.rules["rsi_long_min"] <= rsi <= self.rules["rsi_long_max"]:
                long_score += self.rules["rsi_zone_weight"]
                long_confirmations += 1
        if macd_cross_short:
            if self.rules["rsi_short_min"] <= rsi <= self.rules["rsi_short_max"]:
                short_score += self.rules["rsi_zone_weight"]
                short_confirmations += 1

        # EMA alignment
        if ema9 > ema21:
            if macd_cross_long:
                long_score += self.rules["ema_alignment_weight"]
                long_confirmations += 1
        elif ema9 < ema21:
            if macd_cross_short:
                short_score += self.rules["ema_alignment_weight"]
                short_confirmations += 1

        # Not sideways
        if bb_width >= self.rules["bb_width_threshold"] and adx >= self.rules["adx_threshold"]:
            if macd_cross_long:
                long_score += self.rules["not_sideways_weight"]
                long_confirmations += 1
            if macd_cross_short:
                short_score += self.rules["not_sideways_weight"]
                short_confirmations += 1

        # No exhaustion (упрощено: нет экстремального RSI)
        if rsi <= 70 and rsi >= 30:
            if macd_cross_long:
                long_score += self.rules["no_exhaustion_weight"]
                long_confirmations += 1
            if macd_cross_short:
                short_score += self.rules["no_exhaustion_weight"]
                short_confirmations += 1

        # Volume
        if volume_ratio >= self.rules["volume_ratio_threshold"]:
            if macd_cross_long:
                long_score += self.rules["volume_weight"]
                long_confirmations += 1
            if macd_cross_short:
                short_score += self.rules["volume_weight"]
                short_confirmations += 1

        # Decision
        signal = None
        score = 0
        if long_score >= self.rules["min_score"] and long_confirmations >= self.rules["min_confirmations"]:
            signal = "BUY"
            score = long_score
            reason = f"Long signal, score {long_score}"
        elif short_score >= self.rules["min_score"] and short_confirmations >= self.rules["min_confirmations"]:
            signal = "SELL"
            score = short_score
            reason = f"Short signal, score {short_score}"
        else:
            return {"action": "HOLD", "reason": "Недостаточный скор"}

        # AI confirmation for strategies with AI
        if self.strategy.upper() in ["HYBRID", "HYBRID_VETO"] and signal:
            ai_decision = self._get_ai_confirmation(signal, score, klines, index)
            if ai_decision == "hold":
                return {"action": "HOLD", "reason": f"AI rejected {signal.lower()} signal"}
            elif ai_decision == signal.lower():
                reason += " (AI approved)"
            else:
                return {"action": "HOLD", "reason": f"AI changed signal to {ai_decision}"}

        return {"action": signal, "score": score, "reason": reason}

    # Вспомогательные методы для расчетов индикаторов
    def _calculate_rsi(self, closes: List[float], period: int) -> float:
        if len(closes) < period + 1:
            return 50
        gains = []
        losses = []
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _rsi_values(self, closes: List[float], period: int) -> List[float]:
        values = []
        for i in range(period, len(closes)):
            values.append(self._calculate_rsi(closes[:i+1], period))
        return values

    def _calculate_ema(self, closes: List[float], period: int) -> float:
        if len(closes) < period:
            return closes[-1] if closes else 0
        multiplier = 2 / (period + 1)
        ema = sum(closes[:period]) / period
        for price in closes[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        return ema

    def _calculate_macd(self, closes: List[float]) -> Tuple[float, float, float]:
        if len(closes) < 26:
            return 0, 0, 0
        ema12 = self._calculate_ema(closes, 12)
        ema26 = self._calculate_ema(closes, 26)
        macd_line = ema12 - ema26
        macd_signal = self._calculate_ema([macd_line] * len(closes), 9)  # Упрощено
        macd_hist = macd_line - macd_signal
        return macd_line, macd_signal, macd_hist

    def _calculate_macd_hist_prev(self, closes: List[float]) -> float:
        macd_line, macd_signal, _ = self._calculate_macd(closes)
        return macd_line - macd_signal

    def _calculate_bb_width(self, closes: List[float], period: int) -> float:
        if len(closes) < period:
            return 0
        sma = sum(closes[-period:]) / period
        variance = sum((x - sma) ** 2 for x in closes[-period:]) / period
        std = math.sqrt(variance)
        return (std / sma) * 100 if sma > 0 else 0

    def _calculate_adx(self, highs: List[float], lows: List[float], closes: List[float], period: int) -> float:
        # Упрощенный ADX (требует DM+/DM-)
        if len(highs) < period:
            return 0
        # Полная реализация сложна, упрощаем до среднего диапазона
        ranges = [highs[i] - lows[i] for i in range(len(highs))]
        return sum(ranges[-period:]) / period

    def _calculate_atr(self, highs: List[float], lows: List[float], closes: List[float], period: int) -> float:
        if len(highs) < period:
            return 0
        trs = []
        for i in range(1, len(highs)):
            tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
            trs.append(tr)
        return sum(trs[-period:]) / period

    def _get_ai_confirmation(self, signal: str, score: int, klines: List[Dict[str, Any]], index: int) -> str:
        """Получить подтверждение от AI."""
        try:
            from ..prompts.strategies.hybrid import HybridStrategy
            strategy = HybridStrategy()
            current_price = klines[index]["closePrice"]
            rsi = self.calculate_indicators(klines, index).get("rsi", 50)
            volume_ratio = self.calculate_indicators(klines, index).get("volume_ratio", 1.0)

            ctx = {
                "signal_data": {
                    "signal": signal,
                    "score": score,
                    "max_score": self.rules.get("max_score", 8),
                    "quality": score / self.rules.get("max_score", 8),
                    "reasons": [f"Score {score}"],
                    "details": {"long_score": score if signal == "BUY" else 0, "short_score": score if signal == "SELL" else 0}
                },
                "current_price": current_price,
                "rsi": rsi,
                "volume_ratio": volume_ratio,
                "volume_status": "High" if volume_ratio > 1.0 else "Low",
                "global_trend": "UP",  # Упрощено
                "local_trend": "UP" if signal == "BUY" else "DOWN",
                "last_5_direction": "UP",  # Упрощено
                "support": current_price * 0.95,
                "resistance": current_price * 1.05,
                "seb_status": "INSIDE",
                "trend_quality_desc": "High",
                "long_sl": current_price * 0.99,
                "long_tp": current_price * 1.03,
                "short_sl": current_price * 1.01,
                "short_tp": current_price * 0.97
            }

            prompt = strategy.get_role() + "\n\n" + strategy.get_objective() + "\n\n" + strategy.get_time_horizon() + "\n\n" + strategy.get_strategy_section(ctx)
            prompt += "\n\nОтветь только JSON: {\"action\": \"buy\" или \"sell\" или \"hold\"}"

            response = get_prediction(prompt)
            # Парсить JSON из ответа
            import json
            try:
                ai_response = json.loads(response.strip())
                return ai_response.get("action", "hold").lower()
            except:
                # Если не JSON, искать buy/sell/hold
                response_lower = response.lower()
                if "buy" in response_lower and signal == "BUY":
                    return "buy"
                elif "sell" in response_lower and signal == "SELL":
                    return "sell"
                else:
                    return "hold"
        except Exception as e:
            print(f"AI error: {e}")
            return "hold"  # Если AI не работает, HOLD