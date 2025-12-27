# 🤖 OpenProducer Agents Architecture

OpenProducer использует **многоагентную (Multi-Agent/Multi-Process)** архитектуру, где каждый модуль выполняет роль специализированного "агента" в торговом конвейере. Каждый торговый актив (например, ETHUSDT, BTCUSDT) запускается в собственном изолированном процессе, внутри которого живут следующие агенты:

## 1. 🏗️ Launcher (Main Supervisor)
*   **Файл:** `src/main.py`
*   **Роль:** Менеджер процессов.
*   **Функции:**
    *   Проверяет конфигурацию (`bot_config.json`) и API ключи.
    *   Запускает отдельный процесс (`Worker`) для каждой торговой пары.
    *   Запускает процесс генерации графиков (`Chart Worker`).
    *   Следит за здоровьем подпроцессов и останавливает их при выходе.

## 2. 🔄 Process Worker (Coordinator)
*   **Файл:** `src/core/process_worker.py`
*   **Роль:** Дирижер оркестра для одного символа.
*   **Функции:**
    *   Работает в бесконечном цикле (Loop).
    *   Последовательно вызывает других агентов: `Collector -> Analyzer -> Predictor -> Executor -> Monitor`.
    *   Управляет частотой тиков в зависимости от `STRATEGY_STYLE` (Scalp/Intraday/Swing).
    *   Обрабатывает ошибки, чтобы падение одного этапа не крашило весь бот.

## 3. 📡 Collector Agent (Data Ingestion)
*   **Файл:** `src/core/collector.py`
*   **Роль:** Сборщик данных.
*   **Функции:**
    *   Загружает свечные данные (OHLCV) с биржи BingX.
    *   Формирует датафреймы Pandas.
    *   Проводит первичную валидацию данных (пропуски, задержки).

## 4. 🧠 Analyzer Agent (Technical Analysis)
*   **Файл:** `src/core/analyzer.py`
*   **Роль:** Технический аналитик.
*   **Функции:**
    *   Рассчитывает индикаторы: SMA, EMA, RSI, ATR, Bollinger Bands.
    *   Определяет Рыночный Контекст (Тренд, Уровни, Объемы).
    *   **Dynamic Strategy Selector:** Локально решает, какая стратегия сейчас актуальна (Momentum vs Pullback) на основе `volume_ratio`.
    *   Формирует обогащенный Промпт для ИИ.

## 5. 🔮 Predictor Agent (AI Reasoning)
*   **Файл:** `src/core/predict.py`
*   **Роль:** ИИ-Трейдер (Decision Maker).
*   **Функции:**
    *   **Smart Filter:** Решает, стоит ли вообще тратить деньги на вызов ИИ (пропускает флэт/низкий объем).
    *   Отправляет запрос в LLM (DeepSeek/Grok/Cluade) через OpenRouter/SiliconFlow.
    *   Парсит JSON-ответ от ИИ (Action, Direction, Entry, SL, TP, Confidence).
    *   Возвращает торговый сигнал.

## 6. ⚔️ Executor Agent (Execution)
*   **Файл:** `src/core/executor.py`
*   **Роль:** Исполнитель ордеров.
*   **Функции:**
    *   Валидирует сигнал ИИ через Risk/Reward фильтр.
    *   Рассчитывает размер позиции (Position Size) с учетом риска.
    *   Отправляет ордера на биржу (Market Order + OCO для SL/TP).
    *   Использует "Режим Хеджирования" (Long и Short могут существовать независимо, но бот обычно держит одну сторону).

## 7. 👀 Monitor Agent (Trade Management)
*   **Файл:** `src/core/monitor.py`
*   **Роль:** Риск-менеджер позиции.
*   **Функции:**
    *   Отслеживает открытые PnL.
    *   **Trailing Stop:** Передвигает Stop Loss в безубыток и далее за ценой ("Let winners run").
    *   Закрывает позицию при достижении сигнала "CLOSE" от ИИ или при смене тренда.

## 8. 🎨 Chart Worker (Visualizer)
*   **Файл:** `src/core/chart_worker.py`
*   **Роль:** Художник графиков.
*   **Функции:**
    *   Работает в отдельном (неблокирующем) процессе.
    *   Генерирует PNG-снимки графиков с наложенными индикаторами и сделками.
    *   Сохраняет их в `data/charts/`.

---

## 📊 Summary Table

| Agent | File | Input | Output |
| :--- | :--- | :--- | :--- |
| **Collector** | `collector.py` | API Data | DataFrame |
| **Analyzer** | `analyzer.py` | DataFrame | Prompt Context |
| **Predictor** | `predict.py` | Context | Signal (JSON) |
| **Executor** | `executor.py` | Signal | Order ID |
| **Monitor** | `monitor.py` | Position | Trailing SL Update |
