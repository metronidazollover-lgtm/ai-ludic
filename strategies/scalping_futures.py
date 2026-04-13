"""
Scalping Futures Strategy
Multi-factor scoring system for crypto futures scalping with scenario tracking.
"""
import logging
import pandas as pd
from ludic2 import config
from ludic2.core.indicators import (
    add_all_indicators,
    detect_ema_alignment,
    detect_macd_cross,
    get_structural_levels,
)
from ludic2.risk.noise_filter import CryptoNoiseFilter
from ludic2.strategies.base import BaseStrategy, Signal, FilterResult, SignalStatus

logger = logging.getLogger("ludic2.scalping")


class ScalpingFuturesStrategy(BaseStrategy):
    """
    Multi-factor scalping strategy for crypto futures.
    Compliant with Sniper Reality Checks (Rule 3 and 4).
    """

    @property
    def name(self) -> str:
        return "⚡ Скальпинг (M5)"

    @property
    def description(self) -> str:
        return "Быстрые сделки на M5 с подтверждением тренда и фазой наблюдения."

    @property
    def required_timeframes(self) -> list[str]:
        return ["5m", "1h", "4h"]

    @property
    def min_score(self) -> int:
        return 3 # Medium strictness for scalping

    def __init__(self):
        self.noise_filter = CryptoNoiseFilter()

    async def analyze(self, dfs: dict[str, pd.DataFrame], symbol: str, data_feed=None) -> Signal | None:
        """Analyze a pair across multiple timeframes."""
        df = dfs.get("5m")
        df_1h = dfs.get("1h")
        df_4h = dfs.get("4h")

        if df is None or df_1h is None or df_4h is None:
            return None

        # Add indicators (Indicators module adds ATR, EMA, RSI, etc)
        df = add_all_indicators(df)
        df_1h = add_all_indicators(df_1h)
        df_4h = add_all_indicators(df_4h)

        # 1. Determine direction on 5m
        trend_5m = detect_ema_alignment(df)
        if trend_5m == "mixed":
            return None
        
        direction = "LONG" if trend_5m == "bullish" else "SHORT"
        entry_price = df["close"].iloc[-1]
        atr = df["atr"].iloc[-1]

        # PHASE 16: Smart Macro Trend Filter
        macro_result = None
        if data_feed:
            macro_result = await self.check_macro_trend(symbol, entry_price, "5m", data_feed)
            if macro_result:
                # Reject if counter-trend
                if direction == "LONG" and macro_result.state == "bearish":
                    logger.info(f"Scalping: Rejected LONG for {symbol} due to BEARISH macro trend.")
                    return None
                if direction == "SHORT" and macro_result.state == "bullish":
                    logger.info(f"Scalping: Rejected SHORT for {symbol} due to BULLISH macro trend.")
                    return None

        # 2. Tech Confluence Scorer (Sniper v5.0)
        factors = [("Trend M5", True, f"5m {trend_5m}")]
        
        # MACD Cross
        m_cross = detect_macd_cross(df, lookback=3)
        macd_ok = (direction == "LONG" and m_cross == "bullish_cross") or \
                  (direction == "SHORT" and m_cross == "bearish_cross")
        factors.append(("MACD Pulse", macd_ok, "Confirmed" if macd_ok else "No pulse"))

        # RSI Range
        rsi = df["rsi"].iloc[-1]
        rsi_ok = (direction == "LONG" and rsi < 55) or (direction == "SHORT" and rsi > 45)
        factors.append(("RSI Level", rsi_ok, f"RSI: {rsi:.0f}"))

        # Volume Integrity
        vol_pulse = df["vol_ratio"].iloc[-1] > 1.2
        factors.append(("Volume", vol_pulse, f"Ratio: {df['vol_ratio'].iloc[-1]:.1f}"))

        # HTF Confirmation
        trend_1h = detect_ema_alignment(df_1h)
        htf_ok = (direction == "LONG" and trend_1h == "bullish") or \
                 (direction == "SHORT" and trend_1h == "bearish")
        factors.append(("Trend H1", htf_ok, f"H1 {trend_1h}"))

        score = sum(1 for _, ok, _ in factors if ok)
        
        if score < self.min_score:
            return None

        # 3. Dynamic Levels (Target & Stop)
        levels_5m = get_structural_levels(df, window=5)
        levels_1h = get_structural_levels(df_1h, window=8)
        
        if direction == "LONG":
            resistance = min(levels_1h["resistance"], df["high"].rolling(20).max().iloc[-1])
            support = levels_5m["support"]
            # Ensure price isn't too close to resistance
            if (resistance - entry_price) < (atr * 0.5): resistance = entry_price + (atr * 3)
            
            take_profit = resistance
            stop_loss = support - (atr * 0.2)
        else:
            support = max(levels_1h["support"], df["low"].rolling(20).min().iloc[-1])
            resistance = levels_5m["resistance"]
            if (entry_price - support) < (atr * 0.5): support = entry_price - (atr * 3)
            
            take_profit = support
            stop_loss = resistance + (atr * 0.2)

        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        rr = reward / risk if risk > 0 else 0
        
        if rr < 1.0: return None

        # 4. Scenario Expiry (Rule 4)
        target_time = self.calculate_target_time(entry_price, take_profit, atr, 5)

        # 5. Noise Filter
        filter_res_old = self.noise_filter.check(df, direction)
        filter_res = FilterResult(passed=filter_res_old.passed, checks=filter_res_old.checks)
        if not filter_res.passed: return None

        return Signal(
            symbol=symbol,
            direction=direction,
            confidence="HIGH" if score >= 4 else "MEDIUM",
            score=score,
            max_score=len(factors),
            entry_price=entry_price,
            take_profit=take_profit,
            stop_loss=stop_loss,
            risk_reward=rr,
            timeframe="M5+HTF",
            strategy=self.name,
            factors=factors,
            noise_filter=filter_res,
            macro_trend=macro_result,
            status=SignalStatus.OBSERVATION,
            target_time=target_time
        )

    def generate_test_signal(self, symbol: str) -> Signal:
        return Signal(
            symbol=symbol,
            direction="LONG",
            confidence="HIGH",
            score=4,
            max_score=5,
            entry_price=100.0,
            take_profit=105.0,
            stop_loss=98.0,
            risk_reward=2.5,
            timeframe="M5+MTF",
            strategy=self.name,
            factors=[("Trend M5", True, "Bullish"), ("MACD Pulse", True, "Confirmed"), ("Volume", True, "1.5x")],
            status=SignalStatus.OBSERVATION,
            target_time=datetime.now(timezone.utc) + pd.Timedelta(minutes=45)
        )
