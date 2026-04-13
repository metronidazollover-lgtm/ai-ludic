"""
Crypto Price Fetcher - Bybit V5 Native
"""

import os
import requests
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# Bybit public endpoint (using mirror bytick for stability)
BYBIT_API_URL = os.environ.get("BYBIT_API_URL", "https://api.bytick.com").strip()

_session = requests.Session()
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
})

PRICE_FETCH_TIMEOUT = 15
PRICE_FETCH_MAX_RETRIES = 2
UTC = timezone.utc

def _normalize_symbol(symbol: str) -> str:
    """Ensure symbol is in Bybit format: BTCUSDT."""
    raw = symbol.strip().upper()
    s = raw.replace("-", "").replace("/", "")
    if s.endswith("PERP"): s = s.replace("PERP", "")
    if not s.endswith("USDT"): s += "USDT"
    return s

def _fetch_bybit_now(symbol: str) -> Optional[float]:
    """Get current price using Tickers endpoint."""
    url = f"{BYBIT_API_URL}/v5/market/tickers"
    params = {"category": "linear", "symbol": symbol}
    try:
        res = _session.get(url, params=params, timeout=PRICE_FETCH_TIMEOUT)
        data = res.json()
        if data.get("retCode") == 0:
            return float(data["result"]["list"][0].get("lastPrice", 0))
    except: pass
    return None

def _fetch_bybit_historical(symbol: str, executed_at: str) -> Optional[float]:
    """Get price at specific time using Kline endpoint."""
    try:
        dt = datetime.fromisoformat(executed_at.replace("Z", "+00:00")).astimezone(UTC)
        ts_ms = int(dt.timestamp() * 1000)
    except: return None

    url = f"{BYBIT_API_URL}/v5/market/kline"
    # Fetch 1m candle near that timestamp
    params = {"category": "linear", "symbol": symbol, "interval": "1", "start": ts_ms - 60000, "limit": 3}
    try:
        res = _session.get(url, params=params, timeout=PRICE_FETCH_TIMEOUT)
        data = res.json()
        if data.get("retCode") == 0:
            candles = data["result"].get("list", [])
            if candles:
                return float(candles[0][4]) 
    except: pass
    return None

def get_price_from_market(symbol: str, executed_at: str, market: str, **kwargs) -> Optional[float]:
    """Unified price entry point."""
    if market != "crypto": return None
    
    clean_symbol = _normalize_symbol(symbol)
    
    # Retry logic
    for attempt in range(PRICE_FETCH_MAX_RETRIES + 1):
        try:
            if executed_at.lower() == "now":
                price = _fetch_bybit_now(clean_symbol)
            else:
                price = _fetch_bybit_historical(clean_symbol, executed_at)
            
            if price and price > 0:
                return price
        except: pass
        if attempt < PRICE_FETCH_MAX_RETRIES:
            time.sleep(0.5 * (2 ** attempt)) 
            
    return None
