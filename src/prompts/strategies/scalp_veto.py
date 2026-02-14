"""
ScalpVetoStrategy — Minimal AI veto prompt for borderline SCALP signals.

Input: ~145 tokens. Output: ~25 tokens.
Fires only for borderline quality signals that the deterministic engine
couldn't confidently auto-execute.

The AI's job: APPROVE or REJECT. Nothing else.
"""

from src.prompts.strategies.base import BaseStrategy


class ScalpVetoStrategy(BaseStrategy):

    def get_role(self) -> str:
        return "Scalp risk veto filter."

    def get_objective(self) -> str:
        return "Approve or reject a borderline scalp signal."

    def get_time_horizon(self) -> str:
        return "1-15 minutes."

    def get_strategy_section(self, ctx: dict) -> str:
        signal = ctx.get("signal", "BUY")
        score = ctx.get("score", 0)
        max_score = ctx.get("max_score", 10)
        quality = ctx.get("quality", 0.0)
        regime = ctx.get("regime", "UNKNOWN")
        rsi = ctx.get("rsi", 50)
        volume_ratio = ctx.get("volume_ratio", 1.0)
        momentum_dir = ctx.get("momentum_dir", "MIXED")
        pattern = ctx.get("pattern", "generic")
        symbol = ctx.get("symbol", "?")

        return f"""SCALP VETO for {symbol}. Approve or reject.
Signal: {signal} | Score: {score}/{max_score} | Q: {quality:.2f}
Regime: {regime} | RSI: {rsi:.0f} | Vol: {volume_ratio:.1f}x | Mom: {momentum_dir}
Pattern: {pattern}

Rules:
- APPROVE if indicators align and no obvious trap
- REJECT if RSI extreme, volume dying, or regime unfavorable
- Only respond with JSON: {{"action":"buy|sell|hold","confidence":0.7,"reason":"12 words max"}}"""

    def get_position_management(self, ctx: dict) -> str:
        return ""

    def get_special_situations(self, ctx: dict) -> str:
        return ""

    def get_risk_table(self, ctx: dict) -> str:
        return ""
