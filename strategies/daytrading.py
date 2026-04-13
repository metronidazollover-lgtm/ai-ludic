"""
Full-day setups on M15 charts.
"""
import logging
import pandas as pd
from datetime import datetime, timezone, timedelta
from ludic2.core.indicators import add_all_indicators
from ludic2.strategies.base import BaseStrategy, Signal, SignalStatus

logger = logging.getLogger("ludic2.daytrading")


class DaytradingStrategy(BaseStrategy):
    """
    Daytrading Strategy.
    Enters on M15 breakouts with H1 trend confirmation.
    """

    @property
    def name(self) -> str:
        return "☀️ Дейтрейдинг (M15)"

    @property
    def description(self) -> str:
        return "Внутридневные сделки на M15. Фиксация в течение дня."

    @property
    def required_timeframes(self) -> list[str]:
        return ["15m", "1h"]

    @property
    def min_score(self) -> int:
        return 3

    async def analyze(self, dfs: dict[str, pd.DataFrame], symbol: str, data_feed=None) -> Signal | None:
        df_15m = dfs.get("15m")
        df_1h = dfs.get("1h")
        if df_15m is None or len(df_15m) < 100 or df_1h is None:
            return None

        df_15m = add_all_indicators(df_15m)
        df_1h = add_all_indicators(df_1h)
        
        price = df_15m["close"].iloc[-1]
        atr = df_15m["atr"].iloc[-1]
        
        # Trend Filter (H1)
        h1_ema50 = df_1h["ema_50"].iloc[-1]
        h1_ema200 = df_1h["ema_200"].iloc[-1]
        h1_bull = h1_ema50 > h1_ema200
        
        # M15 Momentum
        rsi = df_15m["rsi"].iloc[-1]
        m15_ema9 = df_15m["ema_9"].iloc[-1]
        m15_ema21 = df_15m["ema_21"].iloc[-1]
        m15_bull = m15_ema9 > m15_ema21
        
        direction = None
        factors = []
        
        if h1_bull and m15_bull and rsi < 60:
            direction = "LONG"
            factors.append(("H1 Trend", True, "Bullish Alignment"))
            factors.append(("M15 Momentum", True, "Bullish Alignment"))
            factors.append(("RSI Level", True, f"RSI: {rsi:.0f}"))
            
            take_profit = price + (atr * 3.0)
            stop_loss = price - (atr * 1.5)
        elif not h1_bull and not m15_bull and rsi > 40:
            direction = "SHORT"
            factors.append(("H1 Trend", True, f"H1 Bearish: {h1_ema50:.2f} < {h1_ema200:.2f}"))
            factors.append(("M15 Momentum", True, "Bearish Alignment"))
            factors.append(("RSI Level", True, f"RSI: {rsi:.0f}"))
            
            take_profit = price - (atr * 3.0)
            stop_loss = price + (atr * 1.5)

        if not direction or len(factors) < self.min_score:
            return None

        # PHASE 16: Smart Macro Trend Filter
        macro_result = None
        if data_feed:
            macro_result = await self.check_macro_trend(symbol, price, "15m", data_feed)
            if macro_result:
                # Reject if counter-trend
                if direction == "LONG" and macro_result.state == "bearish":
                    logger.info(f"Daytrading: Rejected LONG for {symbol} due to BEARISH macro trend.")
                    return None
                if direction == "SHORT" and macro_result.state == "bullish":
                    logger.info(f"Daytrading: Rejected SHORT for {symbol} due to BULLISH macro trend.")
                    return None

        # Estimated duration (Daytrading takes 4-12 hours)
        target_time = self.calculate_target_time(price, take_profit, atr, 15)

        return Signal(
            symbol=symbol,
            direction=direction,
            confidence="MEDIUM",
            score=len(factors),
            max_score=3,
            entry_price=price,
            take_profit=take_profit,
            stop_loss=stop_loss,
            risk_reward=2.0,
            timeframe="M15+H1",
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
            entry_price=100.0,
            take_profit=103.0,
            stop_loss=98.5,
            risk_reward=2.0,
            timeframe="M15+H1",
            strategy=self.name,
            factors=[("H1 Trend", True, "Bullish Alignment"), ("M15 Momentum", True, "Bullish Alignment")],
            status=SignalStatus.OBSERVATION,
            target_time=datetime.now(timezone.utc) + timedelta(hours=6)
        )
