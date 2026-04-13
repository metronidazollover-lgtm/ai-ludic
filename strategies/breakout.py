"""
Breakout Strategy
Volatility-based breakout setups on M30 charts.
"""
import logging
import pandas as pd
from datetime import datetime, timezone, timedelta
from ludic2.core.indicators import add_all_indicators, get_structural_levels
from ludic2.strategies.base import BaseStrategy, Signal, SignalStatus

logger = logging.getLogger("ludic2.breakout")


class BreakoutStrategy(BaseStrategy):
    """
    Breakout Strategy.
    Enters when price breaks structural S/R on M30 with high volume.
    """

    @property
    def name(self) -> str:
        return "💥 Пробой уровня (M30)"

    @property
    def description(self) -> str:
        return "Вход на пробое ключевых уровней поддержки/сопротивления с подтверждением объема."

    @property
    def required_timeframes(self) -> list[str]:
        return ["30m", "1h"]

    @property
    def min_score(self) -> int:
        return 2

    async def analyze(self, dfs: dict[str, pd.DataFrame], symbol: str, data_feed=None) -> Signal | None:
        df_30m = dfs.get("30m")
        df_1h = dfs.get("1h")
        if df_30m is None or len(df_30m) < 100 or df_1h is None:
            return None

        df_30m = add_all_indicators(df_30m)
        from ludic2.core.indicators import get_dynamic_precision
        
        price = df_30m["close"].iloc[-1]
        atr = df_30m["atr"].iloc[-1]
        vol_pulse = df_30m["vol_ratio"].iloc[-1] > 1.3
        
        # v6.5 Fix: Minimum ATR Buffer (0.1% of price)
        eff_atr = max(atr if not pd.isna(atr) else 0, price * 0.001)
        prec = get_dynamic_precision(price)
        
        levels = get_structural_levels(df_30m, window=10)
        resistance = levels["resistance"]
        support = levels["support"]
        
        direction = None
        factors = []
        
        # Breakout criteria: Price crosses level + High Volume
        if price > resistance and vol_pulse:
            direction = "LONG"
            factors.append(("Resistance Breakout", True, f"Price: {price:.{prec}f} > Res: {resistance:.{prec}f}"))
            factors.append(("Volume Surge", True, f"1.3x Pulse"))
            
            take_profit = price + (eff_atr * 4.0)
            stop_loss = resistance - (eff_atr * 0.5)
        elif price < support and vol_pulse:
            direction = "SHORT"
            factors.append(("Support Breakout", True, f"Price: {price:.{prec}f} < Sup: {support:.{prec}f}"))
            factors.append(("Volume Surge", True, f"1.3x Pulse"))
            
            take_profit = price - (eff_atr * 4.0)
            stop_loss = support + (eff_atr * 0.5)

        if not direction or len(factors) < self.min_score:
            return None

        # PHASE 16: Smart Macro Trend Filter
        macro_result = None
        if data_feed:
            macro_result = await self.check_macro_trend(symbol, price, "30m", data_feed)
            if macro_result:
                # Reject if counter-trend
                if direction == "LONG" and macro_result.state == "bearish":
                    logger.info(f"Breakout: Rejected LONG for {symbol} due to BEARISH macro trend.")
                    return None
                if direction == "SHORT" and macro_result.state == "bullish":
                    logger.info(f"Breakout: Rejected SHORT for {symbol} due to BULLISH macro trend.")
                    return None

        # Double Check: Ensure TP/SL are meaningful
        if abs(take_profit - price) < (price * 0.0001):
            return None

        # Estimated duration (Breakouts take 1-4 hours)
        target_time = self.calculate_target_time(price, take_profit, atr, 30)

        return Signal(
            symbol=symbol,
            direction=direction,
            confidence="MEDIUM",
            score=len(factors),
            max_score=2,
            entry_price=price,
            take_profit=take_profit,
            stop_loss=stop_loss,
            risk_reward=2.5,
            timeframe="M30",
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
            score=2,
            max_score=2,
            entry_price=10.0,
            take_profit=11.5,
            stop_loss=9.4,
            risk_reward=2.5,
            timeframe="M30",
            strategy=self.name,
            factors=[("Resistance Break", True, "Confirm"), ("Volume Surge", True, "2.0x")],
            status=SignalStatus.OBSERVATION,
            target_time=datetime.now(timezone.utc) + timedelta(hours=3)
        )
