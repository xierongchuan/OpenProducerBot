from src.prompts.strategies.base import BaseStrategy


class IntradayStrategy(BaseStrategy):

    def get_role(self) -> str:
        return "Ты — внутридневной трейдер (Intraday Trader)."

    def get_objective(self) -> str:
        return "Торговля внутри сессии, закрытие всех позиций к концу дня."

    def get_time_horizon(self) -> str:
        return "Horizon: 4-12 Hours."

    def get_strategy_section(self, ctx: dict) -> str:
        if ctx.get("is_momentum_market", False):
            return self._breakout_section()
        return self._pullback_section()

    def _breakout_section(self) -> str:
        return """## 3. СТРАТЕГИЯ: 🔥 INTRADAY BREAKOUT
*Контекст: Рынок активен, работаем по тренду дня.*

**Твоя Задача:**
Найти точку входа в продолжение дневного тренда.

**Условия:**
1.  Пробой уровня сопротивления/поддержки дня.
2.  Подтверждение объемом.
3.  Удержание сделки до конца сессии или разворота."""

    def _pullback_section(self) -> str:
        return """## 3. СТРАТЕГИЯ: ⚓ INTRADAY PULLBACK (ОТКАТ)
*Контекст: Спокойный рынок, работаем от коррекций.*

**Твоя Задача:**
Купить на низах (support/EMA) растущего тренда.

**Условия:**
1.  Касание EMA или уровня поддержки.
2.  Снижение объема на откате.
3.  RSI вернулся в нейтральную зону."""
