import json
import os
import time
from config import *
from utils import init_api_session, make_request, get_headers
from logger import info, error, warning, log_trade
from symbols import get_epic, get_symbol

# Файл кэша для хранения hold_minutes по dealId
POSITION_CACHE_FILE = f"{DATA_DIR}/positions_cache.json"

def load_position_cache():
    """Загружает кэш позиций из файла"""
    try:
        if os.path.exists(POSITION_CACHE_FILE):
            with open(POSITION_CACHE_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        warning(f"⚠️ Ошибка загрузки кэша позиций: {e}")
        return {}

def save_position_cache(cache):
    """Сохраняет кэш позиций в файл"""
    try:
        with open(POSITION_CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        error(f"❌ Ошибка сохранения кэша позиций: {e}")

def get_open_positions():
    """Получает открытые позиции напрямую из Capital.com API"""
    init_api_session()  # Убедимся, что сессия активна
    url = f"{API_BASE}positions"
    headers = get_headers()

    try:
        response = make_request(url, headers=headers)
        if response is None:
            return {}

        positions = {}
        cache = load_position_cache()
        current_deal_ids = set()

        for position in response.json().get("positions", []):
            market = position.get("market", {})
            epic = market.get("epic", "")

            # Преобразуем EPIC в символ через единый модуль
            symbol = get_symbol(epic)

            if symbol in SYMBOLS and position.get("position", {}).get("status") == "OPEN":
                pos = position["position"]
                deal_id = pos["dealId"]
                current_deal_ids.add(deal_id)

                positions[symbol] = {
                    "type": pos["direction"].lower(),
                    "entry": pos["openLevel"],
                    "dealId": deal_id,
                    "created": pos["createdDate"],
                    "hold_minutes": cache.get(deal_id, 60)  # По умолчанию 60 минут
                }

        # Примечание: автоочистка кэша отключена из-за несоответствия dealId и dealReference
        # В будущем нужно реализовать получение dealId через /confirms/{dealReference}
        # save_position_cache(cache) - очистка пока отключена

        return positions
    except Exception as e:
        error(f"❌ Ошибка получения позиций: {str(e)}")
        return {}

def create_order(symbol, direction, price, hold_minutes=60):
    """Создает ордер с TP/SL через Capital.com"""
    init_api_session()  # Убедимся, что сессия активна
    # Согласно Capital.com API документации, правильный endpoint - POST /positions (не /positions/otc)
    # Endpoint /positions/otc не поддерживает POST метод, что вызывает ошибку 405
    url = f"{API_BASE}positions"
    headers = get_headers()

    # Получаем EPIC код через единый модуль
    epic = get_epic(symbol)

    # Валидация цены
    try:
        price = float(price)
        if price <= 0:
            raise ValueError(f"Некорректная цена: {price}")
    except (TypeError, ValueError) as e:
        raise ValueError(f"Цена должна быть положительным числом: {str(e)}")

    # Расчет расстояния в пунктах (зависит от актива)
    # Для форекса: пункты (вторая цифра после запятой)
    if symbol in ["EUR/USD", "GBP/USD", "USD/JPY"]:
        # Конвертируем проценты в пункты (1% = 10 пунктов для EUR/USD)
        tp_distance = str(int(TAKE_PROFIT_PERCENT * 10))
        sl_distance = str(int(STOP_LOSS_PERCENT * 10))
    # Для криптовалют: абсолютное значение в USD
    elif symbol == "BTC/USD":
        tp_distance = str(int(price * TAKE_PROFIT_PERCENT / 100))
        sl_distance = str(int(price * STOP_LOSS_PERCENT / 100))
    # Для акций и товаров: также используем абсолютное значение
    else:
        tp_distance = str(int(price * TAKE_PROFIT_PERCENT / 100))
        sl_distance = str(int(price * STOP_LOSS_PERCENT / 100))

    # Проверяем разумность значений
    if int(tp_distance) < 1 or int(sl_distance) < 1:
        raise ValueError(f"Слишком маленькие TP/SL: TP={tp_distance}, SL={sl_distance}")

    payload = {
        "epic": epic,
        "direction": direction,
        "orderType": "MARKET",
        "size": POSITION_SIZE,
        "currencyCode": "USD",
        "forceOpen": True,
        "guaranteedStop": False,
        "stopLoss": {
            "distance": sl_distance,
            "type": "BID"
        },
        "takeProfit": {
            "distance": tp_distance,
            "type": "BID"
        }
    }

    try:
        response = make_request(url, method="post", json=payload, headers=headers)
        if response is None:
            raise Exception("❌ Не удалось создать ордер - пустой ответ от сервера")

        # Логируем полный ответ API для диагностики
        response_data = response.json()
        info(f"📋 Ответ API на создание позиции: {response_data}")

        # Согласно Capital.com API документации, ответ содержит dealReference (не dealId)
        deal_reference = response_data.get("dealReference")
        if not deal_reference:
            error(f"❌ API не вернул dealReference. Ответ: {response_data}")
            raise Exception(f"❌ API не вернул dealReference в ответе: {response_data}")

        # Согласно Capital.com API: нужно вызвать /confirms/{dealReference} чтобы получить dealId
        # Но для простоты используем dealReference как ключ кэша
        # hold_minutes сохраняется в кэше как {deal_reference: hold_minutes}
        cache = load_position_cache()
        cache[deal_reference] = hold_minutes
        save_position_cache(cache)

        # Логируем сделку в trades.log
        log_trade(f"📌 {symbol}: открыт ордер {direction} по {price:.5f} "
                  f"(TP={tp_distance}, SL={sl_distance}, Ref={deal_reference}, hold={hold_minutes}мин)")

        info(f"✅ {symbol}: открыт ордер {direction} по {price:.5f} (TP={tp_distance}, SL={sl_distance})")
        return deal_reference
    except Exception as e:
        # Логируем ошибку в trades.log
        log_trade(f"❌ Ошибка создания ордера {symbol}: {str(e)}", level='ERROR')

        error(f"❌ Ошибка создания ордера {symbol}: {str(e)}")
        return None

def main(predictions):
    """Основная функция исполнения ордеров"""
    info("\n🚀 Начинаем исполнение ордеров...")
    positions = get_open_positions()
    info(f"📊 Открытые позиции: {list(positions.keys())}")

    # Проверяем лимит позиций (максимум 5)
    MAX_POSITIONS = 5
    if len(positions) >= MAX_POSITIONS:
        warning(f"⚠️ Достигнут лимит открытых позиций ({MAX_POSITIONS}). Новые позиции не открываем.")
        return

    for pred in predictions:
        symbol = pred["symbol"]
        current_price = pred["current_price"]

        # Проверяем лимит перед каждой новой позицией
        current_positions = get_open_positions()
        if len(current_positions) >= MAX_POSITIONS:
            warning(f"⚠️ Достигнут лимит позиций ({MAX_POSITIONS}). Пропускаем {symbol}")
            continue

        # Открываем новые позиции
        if symbol not in positions and pred["confidence"] > MIN_CONFIDENCE_THRESHOLD:
            hold_minutes = pred.get("hold_minutes", 60)  # По умолчанию 60 минут

            if pred["action"] == "buy":
                info(f"📈 {symbol}: сигнал BUY (confidence={pred['confidence']}, причина: {pred['reason']})")
                create_order(symbol, "BUY", current_price, hold_minutes)
            elif pred["action"] == "sell":
                info(f"📉 {symbol}: сигнал SELL (confidence={pred['confidence']}, причина: {pred['reason']})")
                create_order(symbol, "SELL", current_price, hold_minutes)
            else:
                info(f"🔄 {symbol}: действие {pred['action']} не требует открытия позиции")

if __name__ == "__main__":
    import sys, json, predict, analyzer

    info("🔄 Запуск исполнения ордеров...")
    
    # Если запускается через пайплайн
    if not sys.stdin.isatty():
        predictions = json.load(sys.stdin)
    else:
        analyses = analyzer.main()
        predictions = predict.main(analyses)
    
    main(predictions)