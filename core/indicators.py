"""
Ludic2 Technical Indicators Module
Calculates all technical indicators used by strategies.
Optimized for batch processing with pandas.
"""
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger("ludic2.indicators")


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all standard indicators to an OHLCV DataFrame.
    Input must have columns: open, high, low, close, volume
    """
    df = df.copy()
    df = add_ema(df)
    df = add_rsi(df)
    df = add_macd(df)
    df = add_atr(df)
    df = add_volume_sma(df)
    df = add_bollinger(df)
    df = add_candle_analysis(df)
    return df


def add_ema(
    df: pd.DataFrame,
    fast: int = 9,
    mid: int = 21,
    slow: int = 50,
    long: int = 100,
    macro: int = 200
) -> pd.DataFrame:
    """Add Exponential Moving Averages."""
    df[f"ema_{fast}"] = df["close"].ewm(span=fast, adjust=False).mean()
    df[f"ema_{mid}"] = df["close"].ewm(span=mid, adjust=False).mean()
    df[f"ema_{slow}"] = df["close"].ewm(span=slow, adjust=False).mean()
    
    if len(df) >= long:
        df[f"ema_{long}"] = df["close"].ewm(span=long, adjust=False).mean()
        
    if len(df) >= macro:
        df[f"ema_{macro}"] = df["close"].ewm(span=macro, adjust=False).mean()
        # Also add SMA 200 for Volatile state detection
        df[f"sma_{macro}"] = df["close"].rolling(window=macro).mean()
        
    return df


def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Add Relative Strength Index."""
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))
    return df


def add_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Add Average Directional Index (ADX).
    Used for detecting trend strength.
    """
    df = df.copy()
    high = df["high"]
    low = df["low"]
    close = df["close"]
    
    plus_dm = high.diff()
    minus_dm = low.diff()
    
    # Calculate DM+ and DM-
    df["plus_dm"] = np.where((plus_dm > -minus_dm) & (plus_dm > 0), plus_dm, 0)
    df["minus_dm"] = np.where((-minus_dm > plus_dm) & (-minus_dm > 0), -minus_dm, 0)
    
    # TR (True Range)
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    
    # Using Wilder's smoothing (alpha = 1/period)
    atr_smooth = tr.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    plus_di = 100 * (df["plus_dm"].ewm(alpha=1/period, min_periods=period, adjust=False).mean() / atr_smooth)
    minus_di = 100 * (df["minus_dm"].ewm(alpha=1/period, min_periods=period, adjust=False).mean() / atr_smooth)
    
    dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di)).replace(0, 50) # Avoid div by zero
    df["adx"] = dx.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    # Cleanup temporary columns
    return df.drop(columns=["plus_dm", "minus_dm"])


def add_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> pd.DataFrame:
    """Add MACD, Signal Line, and Histogram."""
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    df["macd"] = ema_fast - ema_slow
    df["macd_signal"] = df["macd"].ewm(span=signal, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    return df


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Add Average True Range."""
    high = df["high"]
    low = df["low"]
    close_prev = df["close"].shift(1)

    tr = pd.concat([
        high - low,
        (high - close_prev).abs(),
        (low - close_prev).abs(),
    ], axis=1).max(axis=1)

    df["atr"] = tr.rolling(window=period).mean()
    df["atr_pct"] = ((df["atr"] / df["close"]) * 100).fillna(0)  # ATR as % of price
    return df


def add_volume_sma(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Add Volume SMA and volume ratio."""
    df["vol_sma"] = df["volume"].rolling(window=period).mean()
    df["vol_ratio"] = (df["volume"] / df["vol_sma"].replace(0, np.nan)).fillna(0)
    return df


def add_bollinger(
    df: pd.DataFrame, period: int = 20, std_dev: float = 2.0
) -> pd.DataFrame:
    """Add Bollinger Bands."""
    sma = df["close"].rolling(window=period).mean()
    std = df["close"].rolling(window=period).std()
    df["bb_upper"] = sma + (std * std_dev)
    df["bb_middle"] = sma
    df["bb_lower"] = sma - (std * std_dev)
    df["bb_width"] = ((df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]) * 100
    return df


def add_candle_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze candle structure (used by Noise Filter).
    Adds body size, wick ratios, and candle type.
    """
    body = (df["close"] - df["open"]).abs()
    full_range = df["high"] - df["low"]
    full_range = full_range.replace(0, np.nan)  # Avoid division by zero

    df["body_size"] = body
    df["full_range"] = full_range
    df["body_ratio"] = body / full_range  # Body as % of full candle
    df["wick_ratio"] = 1 - df["body_ratio"]  # Total wick as % of full candle

    # Upper and lower wick sizes
    df["upper_wick"] = df["high"] - df[["open", "close"]].max(axis=1)
    df["lower_wick"] = df[["open", "close"]].min(axis=1) - df["low"]

    # Candle direction
    df["is_bullish"] = df["close"] > df["open"]
    df["is_bearish"] = df["close"] < df["open"]

    # Full-body candle (wick < 20%) — used by Impulse Integrity check
    df["is_full_body"] = df["body_ratio"] >= 0.80

    return df


def find_pivots(df: pd.DataFrame, window: int = 5) -> dict[str, list[float]]:
    """
    Find local Swing Highs and Swing Lows.
    A pivot high is a peak where it is higher than 'window' candles on each side.
    """
    highs = []
    lows = []
    
    if len(df) < window * 2 + 1:
        return {"highs": [], "lows": []}

    for i in range(window, len(df) - window):
        is_high = True
        is_low = True
        
        val_high = df["high"].iloc[i]
        val_low = df["low"].iloc[i]
        
        for j in range(i - window, i + window + 1):
            if i == j: continue
            if df["high"].iloc[j] > val_high:
                is_high = False
            if df["low"].iloc[j] < val_low:
                is_low = False
                
        if is_high:
            highs.append(float(val_high))
        if is_low:
            lows.append(float(val_low))
            
    return {"highs": highs, "lows": lows}


def get_structural_levels(df: pd.DataFrame, window: int = 5) -> dict[str, float]:
    """
    Determine the nearest support and resistance levels.
    Returns: {'support': float, 'resistance': float}
    """
    pivots = find_pivots(df, window=window)
    current_price = df["close"].iloc[-1]
    
    # Filter for nearest
    supports = [p for p in pivots["lows"] if p < current_price]
    resistances = [p for p in pivots["highs"] if p > current_price]
    
    # Fallback to current OHLC extremes if no pivots found
    support = max(supports) if supports else df["low"].tail(window*2).min()
    resistance = min(resistances) if resistances else df["high"].tail(window*2).max()
    
    return {
        "support": float(support),
        "resistance": float(resistance)
    }


def detect_ema_alignment(df: pd.DataFrame) -> str:
    """
    Check EMA alignment for trend determination.
    Returns: 'bullish', 'bearish', or 'mixed'
    """
    if len(df) < 50:
        return "mixed"

    price = df["close"].iloc[-1]
    ema9 = df["ema_9"].iloc[-1]
    ema21 = df["ema_21"].iloc[-1]
    ema50 = df["ema_50"].iloc[-1]

    if price > ema9 > ema21 > ema50:
        return "bullish"
    elif price < ema9 < ema21 < ema50:
        return "bearish"
    return "mixed"


def detect_macro_market_state(df: pd.DataFrame) -> dict:
    """
    Evaluate HTF market state to choose the best trend indicator.
    Returns logic for Phase 16 Smart Filter.
    """
    if len(df) < 200:
        return {
            'state': 'unknown',
            'indicator': 'ema_100',
            'adx': 0,
            'atr_pct': 0,
            'reason': 'Insufficient data'
        }

    # Add necessary indicators for analysis
    df = add_adx(df)
    df = add_atr(df)
    df = add_ema(df)
    
    adx = df["adx"].iloc[-1]
    atr_pct = df["atr_pct"].iloc[-1]
    
    # Logic for Smart Selection:
    if atr_pct > 1.5:
        return {
            'state': 'volatile',
            'indicator': 'sma_200',
            'adx': adx,
            'atr_pct': atr_pct,
            'reason': f'High Noise (ATR: {atr_pct:.2f}%) -> Using SMA 200'
        }
    elif adx > 25:
        return {
            'state': 'trending',
            'indicator': 'ema_100',
            'adx': adx,
            'atr_pct': atr_pct,
            'reason': f'Strong Trend (ADX: {adx:.1f}) -> Using EMA 100'
        }
    else:
        return {
            'state': 'ranging',
            'indicator': 'ema_200',
            'adx': adx,
            'atr_pct': atr_pct,
            'reason': f'Weak Trend (ADX: {adx:.1f}) -> Using EMA 200'
        }


def detect_macd_cross(df: pd.DataFrame, lookback: int = 3) -> str | None:
    """
    Detect recent MACD crossover.
    Returns: 'bullish_cross', 'bearish_cross', or None
    """
    if len(df) < lookback + 1:
        return None

    recent = df["macd_hist"].iloc[-lookback:]
    prev = df["macd_hist"].iloc[-(lookback + 1)]

    # Bullish cross: histogram went from negative to positive
    if prev < 0 and any(recent > 0):
        return "bullish_cross"
    # Bearish cross: histogram went from positive to negative
    if prev > 0 and any(recent < 0):
        return "bearish_cross"
    return None


def detect_rsi_divergence(
    df: pd.DataFrame, lookback: int = 14
) -> str | None:
    """
    Detect RSI divergence (bullish or bearish).
    Bullish: price makes lower low, RSI makes higher low
    Bearish: price makes higher high, RSI makes lower high
    """
    if len(df) < lookback * 2:
        return None

    prices = df["close"].iloc[-lookback * 2:]
    rsi_vals = df["rsi"].iloc[-lookback * 2:]

    # Find local extremes
    price_recent_low = prices.iloc[-lookback:].min()
    price_prev_low = prices.iloc[:lookback].min()
    rsi_recent_low = rsi_vals.iloc[-lookback:].min()
    rsi_prev_low = rsi_vals.iloc[:lookback].min()

    price_recent_high = prices.iloc[-lookback:].max()
    price_prev_high = prices.iloc[:lookback].max()
    rsi_recent_high = rsi_vals.iloc[-lookback:].max()
    rsi_prev_high = rsi_vals.iloc[:lookback].max()

    # Bullish divergence
    if price_recent_low < price_prev_low and rsi_recent_low > rsi_prev_low:
        return "bullish_divergence"

    # Bearish divergence
    if price_recent_high > price_prev_high and rsi_recent_high < rsi_prev_high:
        return "bearish_divergence"

    return None


def get_dynamic_precision(price: float) -> int:
    """
    Determine optimal decimal places for price display.
    """
    if price >= 100:
        return 2
    elif price >= 1:
        return 4
    elif price >= 0.01:
        return 6
    else:
        return 8
