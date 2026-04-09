from typing import Dict, List, Any
from ..utils.logger import info

class PnLTracker:
    """Отслеживает прибыль/убытки и метрики бэктеста."""

    def __init__(self):
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.trades: List[Dict[str, Any]] = []

    def add_trade(self, trade: Dict[str, Any]):
        """Добавляет завершенную сделку."""
        self.trades.append(trade)
        self.realized_pnl += trade["pnl"]
        self.total_trades += 1
        if trade["pnl"] > 0:
            self.winning_trades += 1
        info(f"✅ Сделка закрыта: P&L {trade['pnl']:.2f}")

    def get_metrics(self) -> Dict[str, Any]:
        """Возвращает метрики."""
        win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        total_pnl = self.realized_pnl + self.unrealized_pnl
        return {
            "total_pnl": total_pnl,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "win_rate": win_rate,
            "total_trades": self.total_trades,
            "sharpe_ratio": self._calculate_sharpe(),  # Упрощено
            "max_drawdown": self._calculate_max_drawdown()
        }

    def _calculate_sharpe(self) -> float:
        """Упрощенный Sharpe ratio."""
        if not self.trades:
            return 0
        returns = [t["pnl"] for t in self.trades]
        avg_return = sum(returns) / len(returns)
        std_dev = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
        return avg_return / std_dev if std_dev > 0 else 0

    def _calculate_max_drawdown(self) -> float:
        """Максимальная просадка."""
        if not self.trades:
            return 0
        cumulative = 0
        peak = 0
        max_dd = 0
        for trade in self.trades:
            cumulative += trade["pnl"]
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd
        return max_dd

class CommissionCalculator:
    """Рассчитывает комиссии на основе конфигурации."""

    def __init__(self, maker_rate: float = 0.0002, taker_rate: float = 0.0005):
        self.maker_rate = maker_rate
        self.taker_rate = taker_rate
        self.total_commission = 0.0

    def calculate_commission(self, position_size: float, is_maker: bool = False) -> float:
        """Рассчитывает комиссию для позиции."""
        rate = self.maker_rate if is_maker else self.taker_rate
        commission = position_size * rate
        self.total_commission += commission
        return commission

    def get_total_commission(self) -> float:
        """Общая комиссия."""
        return self.total_commission