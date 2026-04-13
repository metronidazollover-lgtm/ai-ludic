"""
Trend Following Strategy
Capturing momentum on 1H/4H timeframes.
"""
import logging
import pandas as pd
from datetime import datetime, timezone, timedelta
from ludic2.core.indicators import add_all_indicators
from ludic2.strategies.base import BaseStrategy, Signal, SignalStatus

logger = logging.getLogger("ludic2.trend")


class TrendFollowingStrategy(BaseStrategy):
    """
    Trend Following Strategy.
    Enters when H1 EMA/MACD momentum aligns with H4 trend.
    """

    @property
    def name(self) -> str:
        return "📈 Трендовая торговля (H1)"

    @property
    def description(self) -> str:
        return "Работа по импульсу на H1. Подтверждение тренда на H4. Высокое мат. ожидание."

    @property
    def required_timeframes(self) -> list[str]:
        return ["1h", "4h"]

    @property
    def min_score(self) -> int:
        return 3

    async def analyze(self, dfs: dict[str, pd.DataFrame], symbol: str, data_feed=None) -> Signal | None:
        df_1h = dfs.get("1h")
        df_4h = dfs.get("4h")
        if df_1h is None or len(df_1h) < 100 or df_4h is None:
            return None

        df_1h = add_all_indicators(df_1h)
        df_4h = add_all_indicators(df_4h)
        
        price = df_1h["close"].iloc[-1]
        atr = df_1h["atr"].iloc[-1]
        
        # H4 Trend
        h4_ema50 = df_4h["ema_50"].iloc[-1]
        h4_ema200 = df_4h["ema_200"].iloc[-1]
        h4_bull = h4_ema50 > h4_ema200
        
        # H1 Momentum
        h1_ema9 = df_1h["ema_9"].iloc[-1]
        h1_ema21 = df_1h["ema_21"].iloc[-1]
        h1_bull = h1_ema9 > h1_ema21
        
        # MACD alignment
        h1_macd = df_1h["macd_hist"].iloc[-1] > 0 # Using hist as proxy for cross
        
        direction = None
        factors = []
        
        if h4_bull and h1_bull:
            direction = "LONG"
            factors.append(("H4 Trend", True, "Bullish Alignment"))
            factors.append(("H1 Momentum", True, "Bullish Alignment"))
            if h1_macd:
                factors.append(("MACD Pulse", True, "Bullish"))
            
            take_profit = price + (atr * 4.0)
            stop_loss = price - (atr * 2.0)
        elif not h4_bull and not h1_bull:
            direction = "SHORT"
            factors.append(("H4 Trend", True, "Bearish Alignment"))
            factors.append(("H1 Momentum", True, "Bearish Alignment"))
            if not h1_macd:
                factors.append(("MACD Pulse", True, "Bearish"))
            
            take_profit = price - (atr * 4.0)
            stop_loss = price + (atr * 2.0)

        if not direction or len(factors) < self.min_score:
            return None

        # PHASE 16: Smart Macro Trend Filter
        macro_result = None
        if data_feed:
            macro_result = await self.check_macro_trend(symbol, price, "1h", data_feed)
            if macro_result:
                # Reject if counter-trend
                if direction == "LONG" and macro_result.state == "bearish":
                    logger.info(f"Trend: Rejected LONG for {symbol} due to BEARISH macro trend.")
                    return None
                if direction == "SHORT" and macro_result.state == "bullish":
                    logger.info(f"Trend: Rejected SHORT for {symbol} due to BULLISH macro trend.")
                    return None

        # Estimated duration (Trend takes 1-3 days)
        target_time = self.calculate_target_time(price, take_profit, atr, 60)

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
            timeframe="H1+H4",
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
            entry_price=3000.0,
            take_profit=3200.0,
            stop_loss=2900.0,
            risk_reward=2.0,
            timeframe="H1+H4",
            strategy=self.name,
            factors=[("H4 Trend", True, "Bullish Alignment"), ("H1 Momentum", True, "Bullish Alignment")],
            status=SignalStatus.OBSERVATION,
            target_time=datetime.now(timezone.utc) + timedelta(days=1)
        )
