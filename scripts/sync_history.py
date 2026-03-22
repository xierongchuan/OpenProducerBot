#!/usr/bin/env python3
"""
Скрипт для полного обновления trade_history.json данными с биржи.
匹配 ордера входа и выхода для каждой позиции.
"""

import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def load_history(path: str) -> list:
    """Загрузить историю сделок."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"Ошибка загрузки {path}: {e}")
        return []

def save_history(path: str, history: list) -> None:
    """Сохранить историю сделок."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    print(f"✅ Сохранено {len(history)} сделок в {path}")

def get_orders_from_exchange(symbol: str) -> list:
    """Получить ордера с биржи для символа."""
    try:
        from src.exchanges.impl.bingx_client import BingXClient
        client = BingXClient()
        orders = client.get_recent_orders(symbol, limit=20)
        return orders
    except Exception as e:
        print(f"❌ Ошибка получения ордеров для {symbol}: {e}")
        return []

def match_entry_exit_orders(orders: list, side: str) -> tuple:
    """
    Найти соответствующие ордера входа и выхода.
    Для LONG: BUY (entry) -> SELL (exit)
    Для SHORT: SELL (entry) -> BUY (exit)
    """
    from src.exchanges.dto import OrderSide, OrderStatus

    entry_side = OrderSide.BUY if side.upper() == "LONG" else OrderSide.SELL
    exit_side = OrderSide.SELL if side.upper() == "LONG" else OrderSide.BUY

    entry_order = None
    exit_order = None

    # Sort by order_id (which correlates with time)
    sorted_orders = sorted(orders, key=lambda x: int(x.order_id) if x.order_id.isdigit() else 0)

    for order in sorted_orders:
        if order.status != OrderStatus.FILLED:
            continue

        if order.side == entry_side and entry_order is None:
            entry_order = order
        elif order.side == exit_side and entry_order is not None:
            # Found exit after entry
            exit_order = order
            break

    return entry_order, exit_order

def calculate_pnl(entry_price: float, exit_price: float, amount: float, side: str, leverage: int = 10) -> float:
    """
    Рассчитать P&L.
    Для LONG: (exit - entry) * amount
    Для SHORT: (entry - exit) * amount
    """
    side = side.upper()
    if side == "LONG":
        return (exit_price - entry_price) * amount
    else:  # SHORT
        return (entry_price - exit_price) * amount

def main():
    """Главная функция."""
    history_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'trade_history.json')
    history_path = os.path.abspath(history_path)

    print(f"📂 Загрузка истории из {history_path}")
    history = load_history(history_path)

    if not history:
        print("❌ История пуста")
        return

    print(f"📊 Загружено {len(history)} сделок")

    # Group by symbol
    symbols = {}
    for trade in history:
        if trade.get('status') == 'CLOSED':
            symbol = trade.get('symbol')
            if symbol:
                if symbol not in symbols:
                    symbols[symbol] = []
                symbols[symbol].append(trade)

    # Process each symbol
    for symbol, trades in symbols.items():
        print(f"\n🔄 Обработка {symbol} ({len(trades)} сделок)")

        # Get orders from exchange
        orders = get_orders_from_exchange(symbol)
        if not orders:
            print(f"  ⚠️ Нет ордеров с биржи")
            continue

        # Get FILLED orders only
        from src.exchanges.dto import OrderStatus
        filled_orders = [o for o in orders if o.status == OrderStatus.FILLED]
        print(f"  📋 Исполненных ордеров: {len(filled_orders)}")

        # For each trade, try to find matching entry/exit
        for trade in trades:
            side = trade.get('side', '')
            entry_price = trade.get('entry_price', 0)
            amount = trade.get('amount', 0)

            print(f"\n  Сделка: {trade.get('dealId')[:10]}... | {side} | entry={entry_price}")

            # Find entry and exit orders that match
            entry_order = None
            exit_order = None

            # Find orders that match our trade parameters
            for order in filled_orders:
                # Entry order should have price close to entry_price
                if side.upper() == "LONG" and order.side.value == "BUY":
                    if abs(order.average_price - entry_price) < entry_price * 0.001:  # 0.1% tolerance
                        entry_order = order
                        # Find corresponding exit
                        for exit_o in filled_orders:
                            if exit_o.side.value == "SELL" and int(exit_o.order_id) > int(order.order_id):
                                exit_order = exit_o
                                break
                        if exit_order:
                            break
                elif side.upper() == "SHORT" and order.side.value == "SELL":
                    if abs(order.average_price - entry_price) < entry_price * 0.001:  # 0.1% tolerance
                        entry_order = order
                        # Find corresponding exit
                        for exit_o in filled_orders:
                            if exit_o.side.value == "BUY" and int(exit_o.order_id) > int(order.order_id):
                                exit_order = exit_o
                                break
                        if exit_order:
                            break

            if entry_order and exit_order:
                # Calculate real P&L
                calculated_pnl = calculate_pnl(
                    entry_order.average_price,
                    exit_order.average_price,
                    amount,
                    side,
                    trade.get('leverage', 10)
                )

                # Get fees from exchange
                entry_fee = abs(entry_order.commission)
                exit_fee = abs(exit_order.commission)
                total_fees = entry_fee + exit_fee

                # Use realized_pnl from exchange (it should match calculated)
                realized_pnl = exit_order.realized_pnl

                # If exchange profit is different, use it
                if realized_pnl != 0:
                    final_pnl = realized_pnl
                else:
                    final_pnl = calculated_pnl

                net_pnl = final_pnl - total_fees

                print(f"    ✅ Найдены ордера:")
                print(f"       Entry: {entry_order.order_id} @ {entry_order.average_price}, fee={entry_fee:.4f}")
                print(f"       Exit:  {exit_order.order_id} @ {exit_order.average_price}, fee={exit_fee:.4f}")
                print(f"       💰 realized_pnl (exchange): {realized_pnl:.4f}")
                print(f"       💰 calculated_pnl: {calculated_pnl:.4f}")
                print(f"       💰 total_fees: {total_fees:.4f}")
                print(f"       💰 net_pnl: {net_pnl:.4f}")

                # Update trade
                trade['close_price'] = exit_order.average_price
                trade['realized_pnl'] = round(final_pnl, 4)
                trade['last_pnl'] = round(final_pnl, 4)
                trade['actual_close_fee'] = round(exit_fee, 4)
                trade['actual_total_fees'] = round(total_fees, 4)
                trade['net_pnl'] = round(net_pnl, 4)
                trade['close_order_id'] = exit_order.order_id

            elif entry_order:
                print(f"    ⚠️ Найден только ордер входа: {entry_order.order_id}")
            else:
                print(f"    ❌ Не найдены ордера для этой сделки")
                # Try to use any matching exit order
                for order in filled_orders:
                    if side.upper() == "LONG" and order.side.value == "SELL":
                        if order.realized_pnl != 0:
                            print(f"    📝 Используем exit ордер: {order.order_id}, profit={order.realized_pnl}")
                            trade['close_price'] = order.average_price
                            trade['realized_pnl'] = round(order.realized_pnl, 4)
                            trade['last_pnl'] = round(order.realized_pnl, 4)
                            trade['actual_close_fee'] = round(abs(order.commission), 4)
                            break
                    elif side.upper() == "SHORT" and order.side.value == "BUY":
                        if order.realized_pnl != 0:
                            print(f"    📝 Используем exit ордер: {order.order_id}, profit={order.realized_pnl}")
                            trade['close_price'] = order.average_price
                            trade['realized_pnl'] = round(order.realized_pnl, 4)
                            trade['last_pnl'] = round(order.realized_pnl, 4)
                            trade['actual_close_fee'] = round(abs(order.commission), 4)
                            break

    # Save updated history
    print(f"\n💾 Сохранение обновлённой истории...")
    save_history(history_path, history)

    # Print summary
    print("\n" + "="*60)
    print("📊 ИТОГ:")
    for trade in history:
        symbol = trade.get('symbol')
        last_pnl = trade.get('last_pnl', 0)
        net_pnl = trade.get('net_pnl', 0)
        print(f"  {symbol}: last_pnl={last_pnl:.4f}, net_pnl={net_pnl:.4f}")

if __name__ == '__main__':
    main()
