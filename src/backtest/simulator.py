from typing import Dict, List, Any, Optional
from src.backtest.metrics import PnLTracker, CommissionCalculator
from src.utils.logger import info, warning

class BacktestSimulator:
    """Симулирует торговлю: позиции, ордера, SL/TP."""

    def __init__(self, initial_balance: float = 1000.0, leverage: float = 5.0, position_size_percent: float = 0.1):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.leverage = leverage
        self.position_size_percent = position_size_percent
        self.positions: Dict[str, Dict[str, Any]] = {}  # symbol -> position
        self.pnl_tracker = PnLTracker()
        self.commission_calculator = CommissionCalculator()
        self.total_pnl_without_commissions = 0.0

    def open_position(self, symbol: str, side: str, entry_price: float, sl_percent: float = 0.01, tp_percent: float = 0.03) -> bool:
        """Открывает позицию. Если позиция уже открыта, не открывает новую."""
        if symbol in self.positions:
            warning(f"⚠️ Позиция для {symbol} уже открыта")
            return False

        position_size = self.balance * self.position_size_percent * self.leverage
        # Комиссия на открытие (taker)
        commission = self.commission_calculator.calculate_commission(position_size)
        self.balance -= commission

        position = {
            "symbol": symbol,
            "side": side,
            "entry_price": entry_price,
            "size": position_size,
            "sl_price": entry_price * (1 - sl_percent) if side == "LONG" else entry_price * (1 + sl_percent),
            "tp_price": entry_price * (1 + tp_percent) if side == "LONG" else entry_price * (1 - tp_percent),
            "unrealized_pnl": 0.0,
            "entry_time": None  # Можно добавить timestamp
        }
        self.positions[symbol] = position
        info(f"✅ Открыта позиция {side} для {symbol} по {entry_price:.2f}, размер {position_size:.2f}")
        return True

    def close_position(self, symbol: str, exit_price: float, reason: str = "manual") -> Optional[Dict[str, Any]]:
        """Закрывает позицию."""
        if symbol not in self.positions:
            warning(f"⚠️ Нет открытой позиции для {symbol}")
            return None

        position = self.positions.pop(symbol)
        side = position["side"]
        entry_price = position["entry_price"]
        size = position["size"]

        # Рассчитать P&L без комиссий
        if side == "LONG":
            pnl_without_comm = (exit_price - entry_price) * size / entry_price
        else:
            pnl_without_comm = (entry_price - exit_price) * size / entry_price

        # Комиссия на закрытие (maker, если limit)
        commission = self.commission_calculator.calculate_commission(size, is_maker=True)
        pnl = pnl_without_comm - commission

        self.total_pnl_without_commissions += pnl_without_comm

        self.balance += pnl
        position["pnl"] = pnl
        position["exit_price"] = exit_price
        position["exit_reason"] = reason

        self.pnl_tracker.add_trade(position)
        info(f"❌ Закрыта позиция {side} для {symbol} по {exit_price:.2f}, P&L {pnl:.2f}, причина: {reason}")
        return position

    def update_positions(self, current_prices: Dict[str, float]):
        """Обновляет позиции: проверяет SL/TP, рассчитывает unrealized P&L."""
        to_close = []
        for symbol, position in self.positions.items():
            if symbol not in current_prices:
                continue
            current_price = current_prices[symbol]
            side = position["side"]
            entry_price = position["entry_price"]
            size = position["size"]
            sl_price = position["sl_price"]
            tp_price = position["tp_price"]

            # Unrealized P&L
            if side == "LONG":
                unrealized_pnl = (current_price - entry_price) * size / entry_price
            else:
                unrealized_pnl = (entry_price - current_price) * size / entry_price
            position["unrealized_pnl"] = unrealized_pnl

            # SL/TP
            if side == "LONG":
                if current_price <= sl_price:
                    to_close.append((symbol, current_price, "SL"))
                elif current_price >= tp_price:
                    to_close.append((symbol, current_price, "TP"))
            else:
                if current_price >= sl_price:
                    to_close.append((symbol, current_price, "SL"))
                elif current_price <= tp_price:
                    to_close.append((symbol, current_price, "TP"))

        # Закрыть позиции
        for symbol, price, reason in to_close:
            self.close_position(symbol, price, reason)

    def check_exit_conditions(self, symbol: str, current_price: float, rsi: float, macd_hist: float) -> bool:
        """Проверяет условия выхода по стратегии (для MACDX)."""
        if symbol not in self.positions:
            return False
        position = self.positions[symbol]
        side = position["side"]

        # MACD reversal
        macd_hist_prev = position.get("macd_hist_prev", 0)
        if (side == "LONG" and macd_hist < 0 and macd_hist_prev >= 0) or \
           (side == "SHORT" and macd_hist > 0 and macd_hist_prev <= 0):
            if position["unrealized_pnl"] >= 0.005 or position["unrealized_pnl"] < -0.01:
                self.close_position(symbol, current_price, "MACD reversal")
                return True

        # RSI extreme
        if (side == "LONG" and rsi > 80) or (side == "SHORT" and rsi < 20):
            self.close_position(symbol, current_price, "RSI extreme")
            return True

        return False

    def get_current_balance(self) -> float:
        """Текущий баланс."""
        return self.balance

    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """Открытые позиции."""
        return self.positions

    def get_metrics(self) -> Dict[str, Any]:
        """Метрики."""
        metrics = self.pnl_tracker.get_metrics()
        total_commission = self.commission_calculator.get_total_commission()
        metrics["total_pnl_without_commissions"] = self.total_pnl_without_commissions
        metrics["total_commission"] = total_commission
        return metrics