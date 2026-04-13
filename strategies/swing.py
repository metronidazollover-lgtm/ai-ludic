"""
Swing Trading Strategy
Medium-term trend followers on 4h/1d charts.
"""
import logging
import pandas as pd
from datetime import datetime, timezone, timedelta
from ludic2.core.indicators import add_all_indicators
from ludic2.strategies.base import BaseStrategy, Signal, SignalStatus

logger = logging.getLogger("ludic2.swing")


class SwingStrategy(BaseStrategy):
    """
    Swing Trading Strategy.
    Enters on 4H pullbacks with daily trend confirmation.
    """

    @property
    def name(self) -> str:
        return "🌊 Свинг-трейдинг (H4)"

    @property
    def description(self) -> str:
        return "Среднесрочные сделки на H4. Вход на откатах основного тренда D1."

    @property
    def required_timeframes(self) -> list[str]:
        return ["4h", "1d"]

    @property
    def min_score(self) -> int:
        return 2

    async def analyze(self, dfs: dict[str, pd.DataFrame], symbol: str, data_feed=None) -> Signal | None:
        df_4h = dfs.get("4h")
        df_1d = dfs.get("1d")
        if df_4h is None or len(df_4h) < 100 or df_1d is None:
            return None

        df_4h = add_all_indicators(df_4h)
        df_1d = add_all_indicators(df_1d)
        
        price = df_4h["close"].iloc[-1]
        atr = df_4h["atr"].iloc[-1]
        
        # Trend Filter (D1)
        d1_bull = df_1d["ema_50"].iloc[-1] > df_1d["ema_200"].iloc[-1]
        
        # Pullback Filter (4H RSI)
        rsi = df_4h["rsi"].iloc[-1]
        
        direction = None
        factors = []
        
        if d1_bull and rsi < 45:
            direction = "LONG"
            factors.append(("D1 Trend", True, "Bullish Alignment"))
            factors.append(("4H Pullman", True, f"RSI: {rsi:.0f}"))
            
            take_profit = price + (atr * 4.0)
            stop_loss = price - (atr * 2.0)
        elif not d1_bull and rsi > 55:
            direction = "SHORT"
            factors.append(("D1 Trend", True, "Bearish Alignment"))
            factors.append(("4H Pullback", True, f"RSI: {rsi:.0f}"))
            
            take_profit = price - (atr * 4.0)
            stop_loss = price + (atr * 2.0)

        if not direction or len(factors) < self.min_score:
            return None

        # PHASE 16: Smart Macro Trend Filter (Checks Weekly for Swing)
        macro_result = None
        if data_feed:
            macro_result = await self.check_macro_trend(symbol, price, "4h", data_feed)
            if macro_result:
                # Reject if counter-trend
                if direction == "LONG" and macro_result.state == "bearish":
                    logger.info(f"Swing: Rejected LONG for {symbol} due to BEARISH macro trend.")
                    return None
                if direction == "SHORT" and macro_result.state == "bullish":
                    logger.info(f"Swing: Rejected SHORT for {symbol} due to BULLISH macro trend.")
                    return None

        # Estimated duration (Swing takes 3-7 days)
        target_time = self.calculate_target_time(price, take_profit, atr, 240)

        return Signal(
            symbol=symbol,
            direction=direction,
            confidence="MEDIUM",
            score=len(factors),
            max_score=2,
            entry_price=price,
            take_profit=take_profit,
            stop_loss=stop_loss,
            risk_reward=2.0,
            timeframe="H4+D1",
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
            entry_price=50000.0,
            take_profit=55000.0,
            stop_loss=48000.0,
            risk_reward=2.5,
            timeframe="H4+D1",
            strategy=self.name,
            factors=[("Macro Trend (D1)", True, "Bullish"), ("4H Alignment", True, "Bullish")],
            status=SignalStatus.OBSERVATION,
            target_time=datetime.now(timezone.utc) + timedelta(days=3)
        )
