#!/usr/bin/env python3
"""
Скрипт для запуска бэктеста.
Использование: python scripts/run_backtest.py --symbol BTCUSDT --strategy MACDX --balance 1000
"""

import argparse
import os
import sys

# Добавить src в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.backtest.engine import BacktestEngine
from src.utils.logger import error, info


def main():
    parser = argparse.ArgumentParser(description="Запуск бэктеста")
    parser.add_argument(
        "--symbol",
        default="BTCUSDT",
        help="Символ для бэктеста (по умолчанию первый из конфига)",
    )
    parser.add_argument(
        "--strategy", default="MACDX", help="Стратегия (по умолчанию MACDX)"
    )
    parser.add_argument(
        "--balance", type=float, default=1000.0, help="Начальный баланс"
    )
    args = parser.parse_args()

    try:
        # Определить символ: если не указан, взять первый из конфига
        if args.symbol == "BTCUSDT":  # Заглушка, в реале из config
            from src.config_loader import load_active_config

            config = load_active_config()
            symbols = config.get("symbols", {}).get("bingx", [])
            if symbols:
                args.symbol = symbols[0]

        info(
            f"Запуск бэктеста для {args.symbol} стратегии {args.strategy} с балансом {args.balance}"
        )

        try:
            engine = BacktestEngine(args.symbol, args.strategy, args.balance)
            result = engine.run()
        except Exception as e:
            error(f"Exception in backtest: {e}")
            result = {}

        if result and "metrics" in result:
            metrics = result["metrics"]
            print("\nРезультаты бэктеста:")
            print(f"Символ: {result.get('symbol', 'N/A')}")
            print(f"Стратегия: {result.get('strategy', 'N/A')}")
            print(f"Total P&L: {metrics.get('total_pnl', 0):.2f}")
            print(f"Realized P&L: {metrics.get('realized_pnl', 0):.2f}")
            print(f"Unrealized P&L: {metrics.get('unrealized_pnl', 0):.2f}")
            print(f"Win Rate: {metrics.get('win_rate', 0):.2%}")
            print(f"Total Trades: {metrics.get('total_trades', 0)}")
            print(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
            print(f"Max Drawdown: {metrics.get('max_drawdown', 0):.2f}")
            print(f"Commission Impact: {metrics.get('commission_impact', 0):.4f}")
            print(f"Отчет сохранен в data/backtest_result.json")
            print("✅ Бэктест завершен")
        else:
            # error("Бэктест не выполнен")
            print(
                f"Debug: result={bool(result)}, metrics in result={'metrics' in result if result else False}"
            )

    except Exception as e:
        error(f"Ошибка запуска бэктеста: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
