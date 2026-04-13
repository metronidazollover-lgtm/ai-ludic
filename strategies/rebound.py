"""
Rebound Strategy
Mean reversion setups on M15 charts.
"""
import logging
import pandas as pd
from datetime import datetime, timezone, timedelta
from ludic2.core.indicators import add_all_indicators, get_structural_levels
from ludic2.strategies.base import BaseStrategy, Signal, SignalStatus

logger = logging.getLogger("ludic2.rebound")


class ReboundStrategy(BaseStrategy):
    """
    Rebound Strategy.
    Enters on RSI oversold/overbought at structural support/resistance.
    """

    @property
    def name(self) -> str:
        return "🔄 Отскок от уровня (M15)"

    @property
    def description(self) -> str:
        return "Вход на разворот тренда от ключевых зон поддержки и сопротивления."

    @property
    def required_timeframes(self) -> list[str]:
        return ["15m"]

    @property
    def min_score(self) -> int:
        return 3

    async def analyze(self, dfs: dict[str, pd.DataFrame], symbol: str, data_feed=None) -> Signal | None:
        df_15m = dfs.get("15m")
        if df_15m is None or len(df_15m) < 100:
            return None

        df_15m = add_all_indicators(df_15m)
        from ludic2.core.indicators import get_dynamic_precision
        
        price = df_15m["close"].iloc[-1]
        atr = df_15m["atr"].iloc[-1]
        rsi = df_15m["rsi"].iloc[-1]
        
        # v6.5 Fix: Minimum ATR Buffer (0.1% of price) to ensure TP/SL difference
        eff_atr = max(atr if not pd.isna(atr) else 0, price * 0.001)
        prec = get_dynamic_precision(price)
        
        levels = get_structural_levels(df_15m, window=10)
        resistance = levels["resistance"]
        support = levels["support"]
        
        direction = None
        factors = []
        
        # Fix: Show ATR with higher precision for low-priced assets
        atr_prec = max(4, prec if price < 1 else 2)
        
        # Rebound Criteria: Price at level + RSI Extremes
        if price <= support * 1.005 and rsi < 35:
            direction = "LONG"
            factors.append(("Near Support", True, f"Price: {price:.{prec}f} @ Sup: {support:.{prec}f}"))
            factors.append(("RSI Oversold", True, f"RSI: {rsi:.0f}"))
            factors.append(("ATR Stability", True, f"ATR: {eff_atr:.{atr_prec}f}"))
            
            take_profit = price + (eff_atr * 3.5)
            stop_loss = price - (eff_atr * 1.5)
        elif price >= resistance * 0.995 and rsi > 65:
            direction = "SHORT"
            factors.append(("Near Resistance", True, f"Price: {price:.{prec}f} @ Res: {resistance:.{prec}f}"))
            factors.append(("RSI Overbought", True, f"RSI: {rsi:.0f}"))
            factors.append(("ATR Stability", True, f"ATR: {eff_atr:.{atr_prec}f}"))
            
            take_profit = price - (eff_atr * 3.5)
            stop_loss = price + (eff_atr * 1.5)

        if not direction or len(factors) < self.min_score:
            return None

        # PHASE 16: Smart Macro Trend Filter
        macro_result = None
        if data_feed:
            macro_result = await self.check_macro_trend(symbol, price, "15m", data_feed)
            if macro_result:
                # Reject if counter-trend
                if direction == "LONG" and macro_result.state == "bearish":
                    logger.info(f"Rebound: Rejected LONG for {symbol} due to BEARISH macro trend.")
                    return None
                if direction == "SHORT" and macro_result.state == "bullish":
                    logger.info(f"Rebound: Rejected SHORT for {symbol} due to BULLISH macro trend.")
                    return None

        # Estimated duration (Scientific: factor in vol_ratio)
        vol_ratio = df_15m["vol_ratio"].iloc[-1] if "vol_ratio" in df_15m else 1.0
        target_time = self.calculate_target_time(price, take_profit, atr, 15, vol_ratio=vol_ratio)

        return Signal(
            symbol=symbol,
            direction=direction,
            confidence="MEDIUM",
            score=len(factors),
            max_score=3,
            entry_price=price,
            take_profit=take_profit,
            stop_loss=stop_loss,
            risk_reward=2.5,
            timeframe="M15",
            strategy=self.name,
            factors=factors,
            status=SignalStatus.OBSERVATION,
            target_time=target_time,
            macro_trend=macro_result
        )

    def generate_test_signal(self, symbol: str) -> Signal:
        return Signal(
            symbol=symbol,
            direction="LONG",
            confidence="MEDIUM",
            score=3,
            max_score=3,
            entry_price=150.0,
            take_profit=165.0,
            stop_loss=144.0,
            risk_reward=2.5,
            timeframe="M15",
            strategy=self.name,
            factors=[("Near Support", True, "Confirm"), ("RSI Oversold", True, "RSI: 28")],
            status=SignalStatus.OBSERVATION,
            target_time=datetime.now(timezone.utc) + timedelta(hours=4)
        )
