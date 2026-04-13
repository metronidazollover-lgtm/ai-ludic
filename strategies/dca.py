"""
Spot-only accumulation for long-term holders.
"""
import logging
import pandas as pd
from datetime import datetime, timezone, timedelta
from ludic2.core.indicators import add_all_indicators
from ludic2.strategies.base import BaseStrategy, Signal, SignalStatus

logger = logging.getLogger("ludic2.dca")


class DcaStrategy(BaseStrategy):
    """
    DCA Strategy (Spot).
    Systematic accumulation in discount zones.
    """

    @property
    def name(self) -> str:
        return "⏳ DCA (Усреднение)"

    @property
    def description(self) -> str:
        return "ДОЛГОСРОЧНЫЙ СПОТ. Регулярные закупки в зонах дисконта."

    @property
    def required_timeframes(self) -> list[str]:
        return ["1d"]

    @property
    def market_type(self) -> str:
        return "spot" # Safety: Rule 1 Compliance (No futures averaging)

    @property
    def min_score(self) -> int:
        return 1

    async def analyze(self, dfs: dict[str, pd.DataFrame], symbol: str, data_feed=None) -> Signal | None:
        df_1d = dfs.get("1d")
        if df_1d is None or len(df_1d) < 50:
            return None

        df_1d = add_all_indicators(df_1d)
        
        price = df_1d["close"].iloc[-1]
        ema200 = df_1d["ema_200"].iloc[-1] if "ema_200" in df_1d else df_1d["ema_50"].iloc[-1]
        rsi = df_1d["rsi"].iloc[-1]
        
        factors = []

        is_discount = price <= ema200 or rsi < 40
        
        if is_discount:
            factors.append(("Discount Zone", True, f"P <= EMA 200" if price <= ema200 else f"RSI: {rsi:.0f}"))
            
            # Long-term DCA target
            target_time = datetime.now(timezone.utc) + timedelta(days=14)

            return Signal(
                symbol=symbol,
                direction="LONG (SPOT)",
                confidence="MEDIUM",
                score=1,
                max_score=1,
                entry_price=price,
                take_profit=price * 1.5,
                stop_loss=price * 0.7,
                risk_reward=1.6,
                timeframe="1D",
                strategy=self.name,
                factors=factors,
                status=SignalStatus.CONFIRMED, # DCA enters immediately upon discount
                target_time=target_time
            )
            
        return None

    def generate_test_signal(self, symbol: str) -> Signal:
        return Signal(
            symbol=symbol,
            direction="LONG (SPOT)",
            confidence="MEDIUM",
            score=1,
            max_score=1,
            entry_price=2500.0,
            take_profit=3750.0,
            stop_loss=2000.0,
            risk_reward=1.5,
            timeframe="1D",
            strategy=self.name,
            factors=[("Discount Zone", True, "Bullish")],
            target_time=datetime.now(timezone.utc) + timedelta(days=30),
            status=SignalStatus.CONFIRMED
        )
