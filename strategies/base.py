"""
Ludic2 Base Strategy Class — Sniper 5.0 Edition
Defines the interface for all trading strategies with scenario tracking.
"""
from abc import ABC, abstractmethod
import pandas as pd
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum

class SignalStatus(Enum):
    OBSERVATION = "🕵️ НАБЛЮДЕНИЕ"
    CONFIRMED = "🔥 РЕКОМЕНДОВАНО"
    CANCELLED = "⚠️ ОТМЕНА"

@dataclass
class FilterResult:
    """Result of a noise filter check."""
    passed: bool
    checks: list[tuple[str, bool, str]]

@dataclass
class MacroTrendResult:
    """Result of a smart macro trend check."""
    passed: bool
    state: str
    indicator: str
    value: float
    reason: str

@dataclass
class Signal:
    """Standardized trading signal with Sniper Scenario support."""
    symbol: str
    direction: str  # "LONG", "SHORT"
    confidence: str # "HIGH", "MEDIUM"
    score: int
    max_score: int
    entry_price: float
    take_profit: float
    stop_loss: float
    risk_reward: float
    timeframe: str
    strategy: str
    factors: list[tuple[str, bool, str]]
    status: SignalStatus = SignalStatus.OBSERVATION
    
    # Sniper Timing (Rule 4)
    target_time: datetime = None  # Estimated arrival time
    arrival_time: datetime = None # Reality check time (10-20% wait)
    
    noise_filter: FilterResult = None
    macro_trend: MacroTrendResult = None # Phase 16: Smart Macro Filter
    
    timestamp: datetime = None
    message_id: int = None # For updating TG messages
    proposed_leverage: int = 10 # Default

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        
        # Default target_time if not provided (e.g. 1 hour)
        if self.target_time is None:
            self.target_time = self.timestamp + timedelta(hours=1)
        
        # Rule 3: Wait 15% of the target duration (average of 10-20%)
        if self.arrival_time is None:
            duration = (self.target_time - self.timestamp).total_seconds()
            wait_seconds = max(120, duration * 0.15) # Min 2m per Rule 3
            wait_seconds = min(900, wait_seconds)   # Max 15m per Rule 3
            self.arrival_time = self.timestamp + timedelta(seconds=wait_seconds)
            
        # Smart Leverage calculation (Target Risk = 1/2 of SL coverage)
        if self.sl_pct > 0:
            raw_lev = 1 / (self.sl_pct / 100) / 2
            self.proposed_leverage = max(1, min(25, int(raw_lev)))

    @property
    def risk_reward_str(self) -> str:
        return f"1:{self.risk_reward:.1f}"

    @property
    def tp_pct(self) -> float:
        if self.direction == "LONG":
            return ((self.take_profit - self.entry_price) / self.entry_price) * 100
        return ((self.entry_price - self.take_profit) / self.entry_price) * 100

    @property
    def sl_pct(self) -> float:
        if self.direction == "LONG":
            return ((self.entry_price - self.stop_loss) / self.entry_price) * 100
        return ((self.stop_loss - self.entry_price) / self.entry_price) * 100


MACRO_TIMEFRAME_MAP = {
    '1m': '15m',
    '3m': '15m',
    '5m': '1h',
    '15m': '1h',
    '30m': '4h',
    '1h': '4h',
    '4h': '1d',
    '1d': '1w'
}

class BaseStrategy(ABC):
    """Abstract base class for all Ludic2 strategies."""

    @property
    @abstractmethod
    def name(self) -> str: pass

    @property
    @abstractmethod
    def description(self) -> str: pass

    @property
    @abstractmethod
    def required_timeframes(self) -> list[str]: pass

    @property
    def market_type(self) -> str:
        """Default market type ('swap' or 'spot')."""
        return "swap"

    @property
    def min_score(self) -> int:
        """Minimum score required for this strategy to trigger."""
        return 3

    @abstractmethod
    async def analyze(self, dfs: dict[str, pd.DataFrame], symbol: str, data_feed=None) -> Signal | None:
        """Analyze price data and return a Signal if entry criteria are met."""
        pass

    @abstractmethod
    def generate_test_signal(self, symbol: str) -> Signal:
        """Generate a sample signal for testing the UI."""
        pass

    async def check_macro_trend(self, symbol: str, current_price: float, current_tf: str, data_feed) -> MacroTrendResult:
        """
        Phase 16: Smart Macro Trend Filter.
        Fetches HTF data, determines market state and selects the best EMA/SMA indicator.
        """
        macro_tf = MACRO_TIMEFRAME_MAP.get(current_tf, '1h')
        
        # 1. Fetch HTF Data
        df_htf = await data_feed.fetch_ohlcv(symbol, macro_tf, limit=250)
        if df_htf.empty or len(df_htf) < 200:
            return MacroTrendResult(True, "unknown", "none", 0.0, "Insufficient HTF history")
            
        # 2. Analyze Market State (ADX/ATR logic from indicators.py)
        from ludic2.core.indicators import detect_macro_market_state
        state_info = detect_macro_market_state(df_htf)
        
        indicator_key = state_info['indicator'] # e.g. 'ema_100', 'ema_200', 'sma_200'
        indicator_val = df_htf[indicator_key].iloc[-1]
        
        # 3. Decision
        passed = False
        trend_status = "mixed"
        
        if current_price > indicator_val:
            trend_status = "bullish"
            passed = True # Signal can be LONG
        elif current_price < indicator_val:
            trend_status = "bearish"
            passed = True # Signal can be SHORT
            
        # Note: If Signal is LONG but trend is bearish, it will be rejected later in Strat.analyze.
        # We return passed=True here to indicate the trend WAS successfully determined.
        
        return MacroTrendResult(
            passed=passed,
            state=trend_status,
            indicator=indicator_key.upper(),
            value=indicator_val,
            reason=state_info['reason'] + f" ({macro_tf})"
        )

    def calculate_target_time(self, price: float, target: float, atr: float, timeframe_minutes: int, vol_ratio: float = 1.0) -> datetime:
        """Estimate arrival time at target based on ATR/Volatility and Market Intensity."""
        dist = abs(target - price)
        # Fix: Ensure dynamic_speed is never 0 to avoid ZeroDivisionError
        # (e.g. if ATR is 0 and price is 0). 
        # Floor speed at 0.01% of price per candle or absolute 0.000001
        speed_floor = max(0.000001, price * 0.0001)
        speed_per_candle = max(atr * 0.5 if not pd.isna(atr) else 0, speed_floor)
        
        intensity = max(0.5, min(3.0, vol_ratio if not pd.isna(vol_ratio) else 1.0))
        dynamic_speed = max(speed_floor, speed_per_candle * intensity)
        
        candles_needed = dist / dynamic_speed
        total_minutes = candles_needed * timeframe_minutes
        
        return datetime.now(timezone.utc) + timedelta(minutes=total_minutes)
