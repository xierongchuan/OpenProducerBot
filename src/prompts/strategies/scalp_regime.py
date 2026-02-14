"""
ScalpRegimeStrategy — AI regime advisor for SCALP mode (L2 layer).

Input: ~300 tokens. Output: ~80 tokens.
Runs every 5-10 minutes in the slow loop. Classifies market regime
and adjusts scalp engine parameters.

This strategy is NOT used for trade decisions — only for parameter tuning.
"""

from src.prompts.strategies.base import BaseStrategy


class ScalpRegimeStrategy(BaseStrategy):

    def get_role(self) -> str:
        return "Market regime classifier for scalp parameter tuning."

    def get_objective(self) -> str:
        return "Classify the current market regime and recommend scalp parameters."

    def get_time_horizon(self) -> str:
        return "5-10 minute analysis window."

    def get_strategy_section(self, ctx: dict) -> str:
        symbol = ctx.get("symbol", "?")
        ema_spread = ctx.get("ema_spread", 0.0)
        rsi = ctx.get("rsi", 50)
        macd_hist = ctx.get("macd_hist", 0.0)
        bb_width = ctx.get("bb_width", 0.0)
        bb_percentile = ctx.get("bb_percentile", 50)
        atr_ratio = ctx.get("atr_ratio", 1.0)
        volume_ratio = ctx.get("volume_ratio", 1.0)
        support = ctx.get("support", 0)
        resistance = ctx.get("resistance", 0)
        up_candles = ctx.get("up_candles", 0)
        down_candles = ctx.get("down_candles", 0)
        prev_regime = ctx.get("prev_regime", "UNKNOWN")
        duration = ctx.get("duration", 0)

        return f"""Classify market regime for {symbol} scalping.
EMA5/13: {ema_spread:.2f}% | RSI: {rsi:.0f} | MACD: {macd_hist:+.6f}
BB width: {bb_width:.2f} (p{bb_percentile}) | ATR: {atr_ratio:.1f}x | Vol: {volume_ratio:.1f}x
S/R: {support:.2f}-{resistance:.2f} | Last 20: {up_candles}/{down_candles} candles
Previous: {prev_regime} for {duration} cycles

Respond JSON only:
{{"regime":"TRENDING|RANGING|VOLATILE|TRANSITIONAL","confidence":0.8,"bias":"bullish|bearish|neutral","scalp_mode":"momentum|mean_reversion|pullback|pause","params":{{"min_score":4,"size_factor":1.0,"sl_mult":1.0,"tp_mult":3.0}},"note":"10 words max"}}"""

    def get_position_management(self, ctx: dict) -> str:
        return ""

    def get_special_situations(self, ctx: dict) -> str:
        return ""

    def get_risk_table(self, ctx: dict) -> str:
        return ""
