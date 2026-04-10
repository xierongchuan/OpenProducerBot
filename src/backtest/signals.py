import math
from typing import List, Dict, Any, Tuple
from ..core.predict import get_prediction

class SignalGenerator:
    """Генерирует сигналы для детерминированных стратегий, таких как MACDX."""

    def __init__(self, strategy: str = "MACDX", config: Dict[str, Any] = None):
        self.strategy = strategy
        self.config = config or {}
        # Параметры из конфига
        self.rules = self.config.get("signal_rules", {})

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
        """Генерирует сигнал, используя оригинальный код стратегии MACDX."""
        analysis = self.calculate_indicators(klines, index)
        if not analysis:
            return {"action": "HOLD", "reason": "Недостаточно данных"}

        # Добавить current_price и другие ключи
        analysis["current_price"] = klines[index]["closePrice"]

        # Динамический импорт SignalGenerator для стратегии
        strategy_lower = self.strategy.lower()
        try:
            if strategy_lower == "macdx":
                from ..core.signals.macdx import MacdxSignalGenerator as SignalGen
            elif strategy_lower == "hybrid":
                from ..core.signals.hybrid import HybridSignalGenerator as SignalGen
            elif strategy_lower == "aiscalp":
                from ..core.signals.aiscalp import AiscalpSignalGenerator as SignalGen
            else:
                return {"action": "HOLD", "reason": f"Unsupported strategy: {self.strategy}"}

            generator = SignalGen(self.config)
            result = generator.generate(analysis)
        except ImportError:
            return {"action": "HOLD", "reason": f"Signal generator for {self.strategy} not found"}
        except Exception as e:
            return {"action": "HOLD", "reason": f"Error generating signal: {e}"}

        # Нормализовать ключи
        normalized = {
            "action": result.get("signal", "HOLD"),
            "score": result.get("score", 0),
            "reason": result.get("reasons", ["нет"])[0] if result.get("reasons") else "нет"
        }

        # Если есть AI, добавить подтверждение
        if self.strategy.upper() in ["HYBRID", "HYBRID_VETO"] and normalized["action"] in ["BUY", "SELL"]:
            signal = normalized["action"]
            score = normalized["score"]
            ai_decision = self._get_ai_confirmation(signal, score, klines, index)
            if ai_decision == "hold":
                normalized = {"action": "HOLD", "reason": f"AI rejected {signal.lower()} signal"}
            elif ai_decision == signal.lower():
                normalized["reason"] = (normalized.get("reason", "") + " (AI approved)").strip()
            else:
                normalized = {"action": "HOLD", "reason": f"AI changed signal to {ai_decision}"}

        return normalized

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
        # Рассчитать серию MACD line для корректного EMA сигнальной линии
        macd_series = self._calculate_macd_series(closes)
        if not macd_series:
            return 0, 0, 0
        macd_line = macd_series[-1]
        macd_signal = self._calculate_ema(macd_series, 9) if len(macd_series) >= 9 else macd_line
        macd_hist = macd_line - macd_signal
        return macd_line, macd_signal, macd_hist

    def _calculate_macd_series(self, closes: List[float]) -> List[float]:
        """Рассчитывает серию MACD line для всех точек данных."""
        if len(closes) < 26:
            return []
        series = []
        for i in range(26, len(closes) + 1):
            subset = closes[:i]
            ema12 = self._calculate_ema(subset, 12)
            ema26 = self._calculate_ema(subset, 26)
            series.append(ema12 - ema26)
        return series

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