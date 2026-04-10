"""
Пример: Бэктест через TradeCommand на базе адаптированного src/backtest/.

Демонстрирует, как BacktestSimulator (реализующий BaseCommandExecutor)
исполняет TradeCommand точно так же, как реальный CommandExecutor
исполняет команды на бирже.

Стратегия генерирует TradeCommand → BacktestSimulator.execute() исполняет
на виртуальном балансе.

Использование:
    python examples/backtest_executor.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.commands.models import TradeCommand
from src.backtest.simulator import BacktestSimulator


def demo():
    """
    Демо: BacktestSimulator как BaseCommandExecutor.

    BacktestSimulator реализует тот же интерфейс BaseCommandExecutor,
    что и реальный CommandExecutor. Стратегия генерирует TradeCommand,
    а движок (реальный или бэктест) их исполняет.
    """
    # BacktestSimulator — это BaseCommandExecutor для бэктестов
    bt = BacktestSimulator(initial_balance=10000.0, leverage=5.0, position_size_percent=0.1)

    # Имитация последовательности команд от стратегии
    commands = [
        # Цикл 1: сигнал BUY
        TradeCommand.entry(
            symbol="BTC-USDT", side="BUY", current_price=50000.0,
            confidence=0.85, stop_loss=49000.0, take_profit=52000.0,
            size_pct=10.0, strategy="MACDX", score=7, max_score=9,
        ),
        # Цикл 2: удержание
        TradeCommand.hold(symbol="BTC-USDT", current_price=50500.0, strategy="MACDX"),
        # Цикл 3: проверка SL/TP (не сработал)
        # (в реальном бэктесте check_sl_tp_command вызывается на каждой свече)
        # Цикл 4: закрытие с прибылью
        TradeCommand.close(
            symbol="BTC-USDT", current_price=51500.0,
            reason="[MACDX] Take profit signal", strategy="MACDX",
        ),
        # Цикл 5: новый вход SELL
        TradeCommand.entry(
            symbol="BTC-USDT", side="SELL", current_price=51500.0,
            confidence=0.80, stop_loss=52000.0, take_profit=50000.0,
            size_pct=8.0, strategy="MACDX", score=6, max_score=9,
        ),
        # Цикл 6: SL сработал
        TradeCommand.close(
            symbol="BTC-USDT", current_price=52100.0,
            reason="[MACDX] Stop loss hit", strategy="MACDX",
        ),
    ]

    print("Running backtest demo (BacktestSimulator as BaseCommandExecutor)...")
    print(f"Initial balance: ${bt.balance:.2f}")
    print()

    for i, cmd in enumerate(commands, 1):
        result = bt.execute(cmd)
        print(f"  Cycle {i}: {cmd.action.value:>6} @ ${cmd.current_price:.2f} -> {result.message}")

    # Итог
    metrics = bt.get_metrics()
    trades = bt.pnl_tracker.trades
    win_rate = (sum(1 for t in trades if t["pnl"] > 0) / len(trades) * 100) if trades else 0

    print(f"\n{'='*50}")
    print(f"Backtest Summary")
    print(f"{'='*50}")
    print(f"Initial balance:  ${bt.initial_balance:.2f}")
    print(f"Final balance:    ${bt.balance:.2f}")
    print(f"Total PnL:        ${metrics['total_pnl']:.2f}")
    print(f"Total trades:     {metrics['total_trades']}")
    print(f"Win rate:         {win_rate:.1f}%")
    print(f"Commands issued:  {len(bt.command_history)}")
    print(f"{'='*50}")

    # Показываем, что все команды сериализуемы
    print("\nCommand history (JSON):")
    for cmd in bt.command_history:
        print(f"  {cmd.to_json()}")


if __name__ == "__main__":
    demo()
