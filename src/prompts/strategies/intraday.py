from src.prompts.strategies.base import BaseStrategy


class IntradayStrategy(BaseStrategy):

    def get_role(self) -> str:
        return "Ты — Intraday Trader (внутридневной трейдер на 5m TF)."

    def get_objective(self) -> str:
        return "Ловить дневные движения. Держать позицию 4-12 часов. Шире стопы чем в скальпинге."

    def get_time_horizon(self) -> str:
        return "Horizon: 4-12 часов. Закрыть к концу торговой сессии."

    def get_strategy_section(self, ctx: dict) -> str:
        current_price = ctx.get("current_price", 0)
        atr = ctx.get("atr", 0)
        rsi = ctx.get("rsi", 50)
        volume_ratio = ctx.get("volume_ratio", 1.0)
        volume_status = ctx.get("volume_status", "Норма")

        global_trend = ctx.get("global_trend", "N/A")
        local_trend = ctx.get("local_trend", "N/A")
        last_5_direction = ctx.get("last_5_direction", "MIXED")

        support = ctx.get("support", 0)
        resistance = ctx.get("resistance", 0)
        support_dist_pct = ctx.get("support_dist_pct", 0)
        resistance_dist_pct = ctx.get("resistance_dist_pct", 0)

        seb_upper = ctx.get("seb_upper", 0)
        seb_lower = ctx.get("seb_lower", 0)
        seb_status = ctx.get("seb_status", "INSIDE")
        trend_quality_desc = ctx.get("trend_quality_desc", "Low")

        long_sl = ctx.get("long_sl", 0)
        long_tp = ctx.get("long_tp", 0)
        short_sl = ctx.get("short_sl", 0)
        short_tp = ctx.get("short_tp", 0)

        if current_price > 0:
            long_potential_pct = (long_tp - current_price) / current_price * 100
            short_potential_pct = (current_price - short_tp) / current_price * 100
            long_risk_pct = (current_price - long_sl) / current_price * 100
            short_risk_pct = (short_sl - current_price) / current_price * 100
        else:
            long_potential_pct = short_potential_pct = long_risk_pct = short_risk_pct = 0

        warnings = []
        if volume_ratio < 0.3:
            warnings.append("DEAD MARKET: Объём слишком низкий.")
        if "MIXED" in last_5_direction and trend_quality_desc == "Low":
            warnings.append("CHOPPY: Нет направления — рассмотри HOLD.")

        warnings_block = ""
        if warnings:
            warnings_block = "\n**ТЕКУЩИЕ РИСКИ:**\n" + "\n".join(f"- {w}" for w in warnings)

        return f"""## 3. СТРАТЕГИЯ: INTRADAY MOMENTUM (5m TF)
*Контекст: Дневные движения. Шире стопы чем скальп, дольше держим позицию.*

---

### МЕНТАЛИТЕТ INTRADAY

**Отличия от скальпа:**
- Шире SL (2.0 ATR) — даём цене "дышать"
- Больше TP (3.0 ATR) — ловим дневной move
- Держим позицию часами, не минутами
- Меньше сделок, но крупнее движения

**Реальность:**
- НЕ каждый день будет тренд — иногда рынок чопит
- Твоя задача: найти направление дня и следовать ему
- "Укусить побольше" — не выходи слишком рано
{warnings_block}

---

### СЕТАПЫ ДЛЯ ВХОДА

**1. TREND CONTINUATION (Продолжение тренда)**

Условия для LONG:
- Global Trend = UP (цена выше SMA)
- Local Trend = BULLISH (EMA9 > EMA21)
- Volume Ratio >= 0.7x (сейчас: {volume_ratio:.2f}x — {volume_status})
- RSI 40-70 (не перекуплен, сейчас: {rsi:.1f})
- Last 5 Direction: UP или STRONG UP (сейчас: {last_5_direction})

Условия для SHORT:
- Global Trend = DOWN
- Local Trend = BEARISH
- Volume Ratio >= 0.7x
- RSI 30-60
- Last 5 Direction: DOWN или STRONG DOWN

---

**2. PULLBACK ENTRY (Вход на откате)**

Условия для LONG:
- Global Trend = UP (тренд не сломан)
- Цена откатила к support ({support:.2f}) или EMA
- RSI опустился к 40-50 (сейчас: {rsi:.1f})
- Объём падает на откате

Условия для SHORT:
- Global Trend = DOWN
- Цена отскочила к resistance ({resistance:.2f})
- RSI поднялся к 50-60

**Вход:** На развороте от уровня. НЕ ловить падающий нож.

---

**3. BREAKOUT (Пробой уровня)**

Условия:
- Цена пробивает resistance ({resistance:.2f}) или support ({support:.2f})
- Volume spike >= 1.2x на пробойной свече
- Закрепление за уровнем (подтверждение)

**Вход:** После закрытия свечи за уровнем, не на самом пробое.
**SL:** За пробитый уровень.

---

### УПРАВЛЕНИЕ ПОЗИЦИЕЙ (ATR-BASED)

**Для LONG:**
| Параметр | Уровень | % от цены |
|----------|---------|-----------|
| Entry | ~{current_price:.2f} | — |
| Stop Loss | {long_sl:.2f} | -{long_risk_pct:.2f}% |
| Take Profit | {long_tp:.2f} | +{long_potential_pct:.2f}% |

**Для SHORT:**
| Параметр | Уровень | % от цены |
|----------|---------|-----------|
| Entry | ~{current_price:.2f} | — |
| Stop Loss | {short_sl:.2f} | +{short_risk_pct:.2f}% |
| Take Profit | {short_tp:.2f} | -{short_potential_pct:.2f}% |

**Правила INTRADAY:**
1. SL = 2.0 ATR (шире чем скальп)
2. TP = 3.0 ATR (R:R = 1:1.5)
3. НЕ двигай SL против себя
4. Можно подтянуть SL в безубыток после +1% движения

---

### АДАПТАЦИЯ К РЫНКУ

**Текущее состояние:**
- Тренд: Global={global_trend}, Local={local_trend}
- Импульс: {last_5_direction} ({volume_status})
- Качество тренда: {trend_quality_desc}
- SEB: {seb_status}

| Состояние | Volume | Действие |
|-----------|--------|----------|
| Trending | >= 0.7x | Trend Continuation |
| Trending + Pullback | >= 0.5x | Pullback Entry |
| Breakout | >= 1.2x | Breakout Trade |
| Ranging (INSIDE) | Any | HOLD или Range play |
| Dead Market | < 0.3x | HOLD |

---

### КОГДА НЕ ВХОДИТЬ (HOLD)

**Жёсткие фильтры:**
1. Volume Ratio < 0.3x (рынок мёртв)
2. MIXED direction + Low quality + RSI 45-55 (полный хаос)

**Мягкие фильтры:**
- Цена в середине range (далеко от уровней)
- Conflicting trends (Global UP, Local BEARISH)

**ВАЖНО:** Не пропускай сделку из-за "неидеальности".
Если есть направление + объём — рассмотри вход."""

    def get_position_management(self, ctx: dict) -> str:
        return """### УПРАВЛЕНИЕ ПОЗИЦИЕЙ (INTRADAY MODE)

**ПРАВИЛО:** Дай прибыли расти, но не жадничай.

1. **Маленький плюс (+0.5% - +1.5%):**
   - Подтяни SL в безубыток
   - HOLD — это еще не TP

2. **Хороший плюс (+1.5% - +3%):**
   - Рассмотри частичное закрытие (50%)
   - Трейлинг стоп на остаток

3. **Маленький минус (до -1%):**
   - HOLD если структура цела
   - CLOSE если пробит ключевой уровень

4. **Около SL:**
   - НЕ двигай SL дальше
   - Прими убыток, двигайся дальше

5. **Позиция "зависла":**
   - Нет движения > 2 часов = рассмотри выход"""

    def get_special_situations(self, ctx: dict) -> str:
        return """### СПЕЦИАЛЬНЫЕ СИТУАЦИИ (INTRADAY)

**1. STRONG TREND DAY:**
- Цена идет в одном направлении весь день
- НЕ контртренди — только по тренду
- Можно добавить к позиции на откатах

**2. FAKEOUT / ЛОЖНЫЙ ПРОБОЙ:**
- Пробой + возврат = вход ПРОТИВ пробоя
- SL за экстремум фейкаута

**3. REVERSAL (Разворот дня):**
- После сильного утреннего move цена разворачивается
- Жди подтверждения (пробой key level в обратную сторону)
- Осторожно — часто бывают ложные развороты"""
