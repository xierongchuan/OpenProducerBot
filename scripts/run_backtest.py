#!/usr/bin/env python3
"""
Скрипт для запуска бэктеста.
Использование: python scripts/run_backtest.py --symbol BTCUSDT --strategy MACDX --balance 1000
"""

import argparse
import sys
import os

# Добавить src в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.backtest.engine import BacktestEngine
from src.utils.logger import info, error

def main():
    parser = argparse.ArgumentParser(description="Запуск бэктеста")
    parser.add_argument("--symbol", default="BTCUSDT", help="Символ для бэктеста (по умолчанию первый из конфига)")
    parser.add_argument("--strategy", default="MACDX", help="Стратегия (по умолчанию MACDX)")
    parser.add_argument("--balance", type=float, default=1000.0, help="Начальный баланс")
    args = parser.parse_args()

    try:
        # Определить символ: если не указан, взять первый из конфига
        if args.symbol == "BTCUSDT":  # Заглушка, в реале из config
            from src.config_loader import load_active_config
            config = load_active_config()
            symbols = config.get("symbols", {}).get("bingx", [])
            if symbols:
                args.symbol = symbols[0]

        info(f"Запуск бэктеста для {args.symbol} стратегии {args.strategy} с балансом {args.balance}")

        engine = BacktestEngine(args.symbol, args.strategy, args.balance)
        result = engine.run()

        if result:
            metrics = result["metrics"]
            print("\nРезультаты бэктеста:")
            print(f"Символ: {result['symbol']}")
            print(f"Стратегия: {result['strategy']}")
            print(f"Total P&L: {metrics['total_pnl']:.2f}")
            print(f"Realized P&L: {metrics['realized_pnl']:.2f}")
            print(f"Unrealized P&L: {metrics['unrealized_pnl']:.2f}")
            print(f"Win Rate: {metrics['win_rate']:.2%}")
            print(f"Total Trades: {metrics['total_trades']}")
            print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
            print(f"Max Drawdown: {metrics['max_drawdown']:.2f}")
            print(f"Commission Impact: {metrics['commission_impact']:.2%}")
            print(f"Отчет сохранен в data/backtest_result.json")
        else:
            error("Бэктест не выполнен")

    except Exception as e:
        error(f"Ошибка запуска бэктеста: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()