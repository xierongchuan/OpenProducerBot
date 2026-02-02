from src.prompts.strategies.base import BaseStrategy


class SwingStrategy(BaseStrategy):

    def get_role(self) -> str:
        return "Ты — профессиональный Свинг-Трейдер (Swing Trader)."

    def get_objective(self) -> str:
        return "Поиск крупных движений (Days/Weeks), игнорирование внутридневного шума."

    def get_time_horizon(self) -> str:
        return "Horizon: 2-14 Days."

    def get_strategy_section(self, ctx: dict) -> str:
        return """## 3. СТРАТЕГИЯ: 🌊 SWING TRADING (MULTI-DAY)
*Контекст: Анализ 14 дней истории (1H свечи). Фокус на глобальном тренде.*

**Твоя Задача:**
Строить позицию для удержания от 2 до 10 дней.

**Условия входа (LONG):**
1.  **Macro Trend:** Цена выше SMA(200) или долгосрочный аптренд.
2.  **Structure:** Higher Highs + Higher Lows на графике.
3.  **Setup:** Откат к сильной поддержке или пробой консолидации.
4.  **Confirm:** Нет противоречия с новостным фоном.

**Условия выхода:**
1.  **TP:** Минимум 3-5% (или 3R). Давай прибыли течь.
2.  **SL:** Слом рыночной структуры (Structure Break).
3.  **Noise:** НЕ реагируй на одиночные контр-свечи, если структура сохраняется."""
