#!/usr/bin/env python3
"""
Удалить дубликаты сделок из trade_history.json, оставив только уникальные записи.
"""

import json
import os

def main():
    history_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'trade_history.json')
    history_path = os.path.abspath(history_path)

    print(f"📂 Загрузка истории из {history_path}")

    with open(history_path, 'r', encoding='utf-8') as f:
        history = json.load(f)

    print(f"📊 Загружено {len(history)} записей")

    # Find duplicates by dealId
    seen_ids = set()
    unique_trades = []
    duplicates = []

    for trade in history:
        deal_id = trade.get('dealId')
        if deal_id:
            if deal_id not in seen_ids:
                seen_ids.add(deal_id)
                unique_trades.append(trade)
            else:
                duplicates.append(trade)
        else:
            # Keep trades without dealId too
            unique_trades.append(trade)

    print(f"✅ Уникальных записей: {len(unique_trades)}")
    print(f"❌ Дубликатов удалено: {len(duplicates)}")

    if duplicates:
        print("\n🗑️ Удалённые дубликаты:")
        for d in duplicates:
            print(f"  - {d.get('symbol')}: {d.get('dealId')} ({d.get('reason', 'N/A')})")

    # Save unique trades
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(unique_trades, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Сохранено {len(unique_trades)} уникальных записей")

if __name__ == '__main__':
    main()
