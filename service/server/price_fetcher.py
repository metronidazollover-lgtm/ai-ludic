"""
Crypto Price Fetcher for Server
Exclusively using Hyperliquid public info endpoints.
"""

import os
import random
import requests
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Tuple, Any
import re
import time
import json

# Hyperliquid public info endpoint
HYPERLIQUID_API_URL = os.environ.get("HYPERLIQUID_API_URL", "https://api.hyperliquid.xyz/info").strip()

PRICE_FETCH_TIMEOUT_SECONDS = float(os.environ.get("PRICE_FETCH_TIMEOUT_SECONDS", "10"))
PRICE_FETCH_MAX_RETRIES = max(0, int(os.environ.get("PRICE_FETCH_MAX_RETRIES", "2")))
PRICE_FETCH_BACKOFF_BASE_SECONDS = max(0.0, float(os.environ.get("PRICE_FETCH_BACKOFF_BASE_SECONDS", "0.35")))
PRICE_FETCH_ERROR_COOLDOWN_SECONDS = max(0.0, float(os.environ.get("PRICE_FETCH_ERROR_COOLDOWN_SECONDS", "20")))

UTC = timezone.utc
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_provider_cooldowns: Dict[str, float] = {}

def _provider_cooldown_remaining(provider: str) -> float:
    return max(0.0, _provider_cooldowns.get(provider, 0.0) - time.time())

def _activate_provider_cooldown(provider: str, duration_s: float, reason: str) -> None:
    if duration_s <= 0: return
    until = time.time() + duration_s
    _provider_cooldowns[provider] = max(_provider_cooldowns.get(provider, 0.0), until)
    print(f"[Price API] {provider} cooldown initialized ({reason})")

def _retry_delay(attempt: int) -> float:
    base = PRICE_FETCH_BACKOFF_BASE_SECONDS * (2 ** attempt)
    return base + random.uniform(0.0, base * 0.25)

def _request_json_with_retry(provider: str, method: str, url: str, **kwargs) -> Any:
    remaining = _provider_cooldown_remaining(provider)
    if remaining > 0:
        raise RuntimeError(f"{provider} cooldown active")
    
    attempts = PRICE_FETCH_MAX_RETRIES + 1
    for attempt in range(attempts):
        try:
            resp = requests.request(method, url, timeout=PRICE_FETCH_TIMEOUT_SECONDS, **kwargs)
            if resp.status_code in _RETRYABLE_STATUS_CODES and attempt < attempts - 1:
                time.sleep(_retry_delay(attempt))
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt < attempts - 1:
                time.sleep(_retry_delay(attempt))
                continue
            _activate_provider_cooldown(provider, PRICE_FETCH_ERROR_COOLDOWN_SECONDS, str(e))
            raise

def _normalize_hyperliquid_symbol(symbol: str) -> str:
    raw = symbol.strip().upper()
    if ":" in raw: return raw
    s = raw
    for suffix in ("-PERP", "PERP", "-USD", "/USD"):
        if s.endswith(suffix):
            s = s[: -len(suffix)]
            break
    return s.strip()

def _hyperliquid_post(payload: dict) -> Any:
    return _request_json_with_retry("hyperliquid", "POST", HYPERLIQUID_API_URL, json=payload)

def _parse_executed_at_to_utc(executed_at: str) -> Optional[datetime]:
    try:
        cleaned = executed_at.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        return dt.astimezone(UTC)
    except:
        return None

def _get_hyperliquid_mid_price(symbol: str) -> Optional[float]:
    coin = _normalize_hyperliquid_symbol(symbol)
    try:
        data = _hyperliquid_post({"type": "l2Book", "coin": coin})
        if isinstance(data, dict) and "levels" in data:
            levels = data["levels"]
            if len(levels) >= 2:
                bids, asks = levels[0], levels[1]
                if bids and asks:
                    mid = (float(bids[0]["px"]) + float(asks[0]["px"])) / 2
                    return float(f"{mid:.6f}")
    except: pass
    return None

def _get_hyperliquid_candle_close(symbol: str, executed_at: str) -> Optional[float]:
    dt = _parse_executed_at_to_utc(executed_at)
    if not dt: return None
    target_ms = int(dt.timestamp() * 1000)
    coin = _normalize_hyperliquid_symbol(symbol)
    try:
        data = _hyperliquid_post({
            "type": "candleSnapshot",
            "req": {"coin": coin, "interval": "1m", "startTime": target_ms - 600000, "endTime": target_ms + 600000}
        })
        if isinstance(data, list):
            closest = None
            closest_diff = float('inf')
            for c in data:
                diff = abs(int(c["t"]) - target_ms)
                if diff < closest_diff:
                    closest_diff = diff
                    closest = float(c["c"])
            return closest
    except: pass
    return None

def get_price_from_market(symbol: str, executed_at: str, market: str, **kwargs) -> Optional[float]:
    if market != "crypto": return None
    if executed_at.lower() == "now":
        return _get_hyperliquid_mid_price(symbol)
    return _get_hyperliquid_candle_close(symbol, executed_at)

def describe_polymarket_contract(*args, **kwargs): return None # Legacy shim
