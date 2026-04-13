"""
HODL Strategy
Long-term spot-only investment signals.
"""
import logging
import pandas as pd
from datetime import datetime, timezone, timedelta
from ludic2.core.indicators import add_all_indicators
from ludic2.strategies.base import BaseStrategy, Signal, SignalStatus

logger = logging.getLogger("ludic2.hodl")


class HodlStrategy(BaseStrategy):
    """
    HODL Strategy (Spot).
    Identifies major accumulation zones on 1D.
    """

    @property
    def name(self) -> str:
        return "💎 HODL / Инвест (1D)"

    @property
    def description(self) -> str:
        return "ДЛИТЕЛЬНЫЙ СПОТ. Покупки на 1D. Выход на пиках цикла."

    @property
    def required_timeframes(self) -> list[str]:
        return ["1d"]

    @property
    def market_type(self) -> str:
        return "spot" # Safety: Investment mode

    @property
    def min_score(self) -> int:
        return 1

    async def analyze(self, dfs: dict[str, pd.DataFrame], symbol: str, data_feed=None) -> Signal | None:
        df_1d = dfs.get("1d")
        if df_1d is None or len(df_1d) < 200:
            return None

        df_1d = add_all_indicators(df_1d)
        
        price = df_1d["close"].iloc[-1]
        ema50 = df_1d["ema_50"].iloc[-1]
        ema200 = df_1d["ema_200"].iloc[-1]
        rsi = df_1d["rsi"].iloc[-1]
        
        direction = None
        factors = []

        is_golden_cross = ema50 > ema200 and df_1d["ema_50"].iloc[-2] <= df_1d["ema_200"].iloc[-2]
        
        if is_golden_cross:
            direction = "LONG (SPOT)"
            factors.append(("Golden Cross", True, "EMA 50/200 Cross"))
        elif price > ema200 and rsi < 40:
            direction = "LONG (SPOT)"
            factors.append(("Macro Value", True, "Price > EMA 200"))
            factors.append(("Low RSI", True, f"RSI: {rsi:.0f}"))

        if not direction:
            return None

        # Long-term investment horizon (3 months+)
        target_time = datetime.now(timezone.utc) + timedelta(days=90)

        return Signal(
            symbol=symbol,
            direction=direction,
            confidence="HIGH",
            score=len(factors),
            max_score=2,
            entry_price=price,
            take_profit=price * 2.0,
            stop_loss=price * 0.8,
            risk_reward=5.0,
            timeframe="1D",
            strategy=self.name,
            factors=factors,
            status=SignalStatus.CONFIRMED, # Macro investments fire once
            target_time=target_time
        )

    def generate_test_signal(self, symbol: str) -> Signal:
        return Signal(
            symbol=symbol,
            direction="LONG (SPOT)",
            confidence="HIGH",
            score=2,
            max_score=2,
            entry_price=40000.0,
            take_profit=80000.0,
            stop_loss=32000.0,
            risk_reward=5.0,
            timeframe="1D",
            strategy=self.name,
            factors=[("Golden Cross", True, "Confirmed")],
            target_time=datetime.now(timezone.utc) + timedelta(days=180),
            status=SignalStatus.CONFIRMED
        )
