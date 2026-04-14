"""
Market intelligence snapshots and read models for Crypto Sniper.
Focused on Bybit market data, funding rates, and AI-driven volatility analysis.
(v7: Optimized & Professional)
"""

from __future__ import annotations
import json
import os
import re
import time
import requests
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Dict, List

logger = logging.getLogger(__name__)

# --- GLOBAL CONFIG & STATE ---
_COOLDOWN_DICT: dict[str, datetime] = {} # symbol -> expiration_time

_COOLDOWN_DICT: dict[str, datetime] = {} # symbol -> expiration_time
_session = requests.Session()
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.bybit.com/"
})

# Try api.bybit.com as it often bypasses regional 403 blocks better than bytick
BYBIT_API_URL = os.getenv("BYBIT_API_URL", "https://api.bybit.com").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

# --- CONFIG GETTERS/SETTERS ---
_CONFIG_CACHE = {}
_LAST_CACHE_SYNC = 0

def _get_config(key: str, default: Any) -> Any:
    """Read config from DB with 60s caching."""
    global _LAST_CACHE_SYNC, _CONFIG_CACHE
    now = time.time()
    
    # Sync cache every 60 seconds
    if now - _LAST_CACHE_SYNC > 60:
        from database import get_db_connection
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM system_config")
            rows = cursor.fetchall()
            _CONFIG_CACHE = {row[0]: row[1] for row in rows}
            _LAST_CACHE_SYNC = now
        except: pass
        finally: conn.close()
    
    val = _CONFIG_CACHE.get(key, str(default))
    # Basic type casting
    if isinstance(default, int): return int(val)
    if isinstance(default, float): return float(val)
    return val

def get_crypto_sniper_interval() -> int:
    return _get_config("refresh_interval", 300)

def set_crypto_sniper_interval(seconds: int):
    from database import get_db_connection
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE system_config SET value=? WHERE key='refresh_interval'", (str(seconds),))
        conn.commit()
    finally: conn.close()

def get_scout_limit() -> int:
    return _get_config("scout_limit", 50)

def set_scout_limit(limit: int):
    from database import get_db_connection
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE system_config SET value=? WHERE key='scout_limit'", (str(limit),))
        conn.commit()
    finally: conn.close()

def get_audit_limit() -> int:
    return _get_config("audit_limit", 5)

def set_audit_limit(limit: int):
    from database import get_db_connection
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE system_config SET value=? WHERE key='audit_limit'", (str(limit),))
        conn.commit()
    finally: conn.close()

def get_bot_mode() -> str:
    return _get_config("trading_mode", "Conservative")

def set_bot_mode(mode: str):
    from database import get_db_connection
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE system_config SET value=? WHERE key='trading_mode'", (mode,))
        conn.commit()
    finally: conn.close()

def get_min_volatility() -> float:
    return _get_config("min_volatility_pct", 0.5)

def set_min_volatility(val: float):
    from database import get_db_connection
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE system_config SET value=? WHERE key='min_volatility_pct'", (str(val),))
        conn.commit()
    finally: conn.close()

# --- MATH UTILS ---
def _calc_rsi(prices: list[float], period: int = 14) -> float:
    if len(prices) < period + 1: return 50.0
    deltas = [prices[i] - prices[i+1] for i in range(len(prices)-1)]
    gains = [d if d > 0 else 0 for d in deltas[:period]]
    losses = [-d if d < 0 else 0 for d in deltas[:period]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0: return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

def _calc_slippage(orderbook: dict, usd_amount: float = 50000) -> float:
    asks = orderbook.get("a", [])
    if not asks: return 0.0
    total_val = 0.0
    start_price = float(asks[0][0])
    last_price = start_price
    for p_str, q_str in asks:
        p, q = float(p_str), float(q_str)
        chunk_val = p * q
        if total_val + chunk_val >= usd_amount:
            last_price = p
            total_val = usd_amount
            break
        total_val += chunk_val
        last_price = p
    if total_val < usd_amount: return 9.99 
    return abs(last_price / start_price - 1) * 100

def _utc_now(): return datetime.now(timezone.utc)
def _utc_now_iso_z(): return _utc_now().isoformat().replace("+00:00", "Z")

def sync_market_metadata():
    """Big Sweep: Fetch all tickers, calculate whale thresholds, and update DB."""
    from database import get_db_connection
    print("[Syncer] Starting Big Sweep (v10.0)...", flush=True)
    tickers = _fetch_all_bybit_tickers()
    if not tickers: return
    
    now = _utc_now_iso_z()
    # Dynamic Whale % from Config
    whale_ratio = float(_get_config("whale_threshold_pct", 0.1)) / 100.0
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        for s, d in tickers.items():
            if not s.endswith("USDT"): continue
            
            turnover = d.get("turnover", 0)
            threshold = turnover * whale_ratio
            
            # Constraints based on symbol
            if s in ["BTCUSDT", "ETHUSDT"]:
                threshold = max(threshold, 1000000)
            else:
                threshold = max(20000, min(threshold, 500000))
            
            cursor.execute("""
                INSERT OR REPLACE INTO bybit_assets_meta 
                (symbol, daily_turnover, whale_threshold, last_sync)
                VALUES (?, ?, ?, ?)
            """, (s, turnover, threshold, now))
        conn.commit()
    except Exception as e: print(f"[Syncer Error] {e}")
    finally: conn.close()

def _get_whale_threshold(symbol: str) -> float:
    """Read the threshold from DB (Macro Context)."""
    from database import get_db_connection
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT whale_threshold FROM bybit_assets_meta WHERE symbol=?", (symbol,))
        row = cursor.fetchone()
        if row: return float(row[0])
    except: pass
    finally: conn.close()
    return 100000.0 # Default fallback $100k

def _detect_whale_accumulation(symbol: str, orderbook: dict) -> list[dict]:
    """Detect persistent large orders (Whales) in the orderbook."""
    from database import get_db_connection
    threshold = _get_whale_threshold(symbol)
    now = _utc_now_iso_z()
    whales = []
    
    # Process both Bids and Asks
    for side in ["b", "a"]:
        for price_str, size_str in orderbook.get(side, []):
            price = float(price_str)
            size = float(size_str)
            val = price * size
            
            if val >= threshold:
                # Potential Whale. Check memory.
                conn = get_db_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT id, hits FROM whale_walls_memory 
                        WHERE symbol=? AND price=? AND side=?
                    """, (symbol, price, side))
                    row = cursor.fetchone()
                    
                    if row:
                        wall_id, hits = row[0], row[1]
                        new_hits = hits + 1
                        cursor.execute("""
                            UPDATE whale_walls_memory SET hits=?, last_seen=? WHERE id=?
                        """, (new_hits, now, wall_id))
                        if new_hits >= 2:
                            whales.append({"side": side, "price": price, "val": val, "hits": new_hits})
                    else:
                        cursor.execute("""
                            INSERT INTO whale_walls_memory (symbol, price, side, size, hits, last_seen)
                            VALUES (?, ?, ?, ?, 1, ?)
                        """, (symbol, price, side, size, now))
                    conn.commit()
                except: pass
                finally: conn.close()
                
    # Cleanup old walls (not seen in last hour)
    # (Simplified for now, could be a separate task)
    return whales

def _calc_crowd_sentiment(symbol: str, current_funding: str) -> str:
    """Analyze funding rate to detect extreme crowd positioning."""
    try:
        f = float(current_funding)
        if f > 0.0005: return "🔴 EXTREME LONGS (Bull Trap Risk)"
        if f < -0.0005: return "🟢 EXTREME SHORTS (Squeeze Risk)"
        if f > 0.0001: return "🟠 Leaning Long"
        if f < -0.0001: return "🔵 Leaning Short"
    except: pass
    return "⚪ Neutral"

def _log_ai_shadow(symbol: str, verdict: dict, metrics: dict):
    """Log everything for future analysis (Black Box)."""
    from database import get_db_connection
    import json
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ai_shadow_log (symbol, verdict, confidence, reasoning, entry, exit, stop_loss, metrics_json, labels_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            symbol, 
            verdict.get("signal", "skip"),
            verdict.get("confidence", 0),
            verdict.get("summary", ""),
            verdict.get("entry", 0.0),
            verdict.get("exit", 0.0),
            verdict.get("stop_loss", 0.0),
            json.dumps(metrics),
            json.dumps(verdict.get("labels", []))
        ))
        conn.commit()
    except Exception as e: print(f"[Shadow Log Error] {e}")
    finally: conn.close()

# --- BYBIT V5 API (OPTIMIZED) ---
def _fetch_all_bybit_tickers() -> dict[str, dict]:
    """Optimization: Fetch price, turnover, funding, and OI for ALL coins in 1 request."""
    url = f"{BYBIT_API_URL}/v5/market/tickers"
    try:
        res = _session.get(url, params={"category": "linear"}, timeout=15)
        if res.status_code != 200:
            print(f"[Bybit Error] Global Ticker status: {res.status_code}", flush=True)
            return {}
        data = res.json()
        if data.get("retCode") == 0:
            return {t["symbol"]: {
                "price": float(t.get("lastPrice", 0)),
                "high24h": float(t.get("highPrice24h", 0)),
                "low24h": float(t.get("lowPrice24h", 0)),
                "turnover": float(t.get("turnover24h", 0)),
                "funding": t.get("fundingRate", "0"),
                "oi": t.get("openInterest", "0")
            } for t in data["result"].get("list", [])}
        else:
            print(f"[Bybit Error] Global Ticker retCode: {data.get('retCode')} {data.get('retMsg')}", flush=True)
    except Exception as e:
        print(f"[Bybit Connection Error] {e}", flush=True)
    return {}

def _fetch_bybit_candles(symbol: str, interval: str = "60", limit: int = 100):
    url = f"{BYBIT_API_URL}/v5/market/kline"
    params = {"category": "linear", "symbol": symbol, "interval": interval, "limit": limit}
    try:
        res = _session.get(url, params=params, timeout=15)
        if res.status_code != 200: return []
        data = res.json()
        if data.get("retCode") == 0:
            return [{"close": float(c[4]), "high": float(c[2]), "low": float(c[3]), "volume": float(c[5])} 
                    for c in data["result"].get("list", [])]
    except: pass
    return []

def _fetch_bybit_orderbook(symbol: str, limit: int = 25):
    url = f"{BYBIT_API_URL}/v5/market/orderbook"
    params = {"category": "linear", "symbol": symbol, "limit": limit}
    try:
        res = _session.get(url, params=params, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data.get("retCode") == 0: return data["result"]
    except: pass
    return {"a": [], "b": []}

# --- SCANNER LOGIC (TIER 1 & 2) ---
def _scout_top_crypto_candidates() -> list[str]:
    """Algorithmically filter the top coins into AI candidates."""
    global_data = _fetch_all_bybit_tickers()
    if not global_data: return []
    
    scout_limit = get_scout_limit()
    min_vol = get_min_volatility()
    audit_limit = get_audit_limit()
    now = _utc_now()
    
    # Sort by turnover and filter out USDT pairs in cooldown
    available = [s for s, d in sorted(global_data.items(), key=lambda x: x[1]["turnover"], reverse=True) 
                 if s.endswith("USDT") and (_COOLDOWN_DICT.get(s, now) <= now)]
    
    # (Snapshot display removed in favor of direct metric passing)
    
    # 2. Level 2.A (Momentum & Exhaustion Check)
    results = []
    candidates_to_check = available[:scout_limit]
    logger.info(f"[Scan] Tier 2.A: Analyzing {len(candidates_to_check)} candidates (Limit: {scout_limit})...")
    
    rsi_low = _get_config("rsi_low", 15)
    rsi_high = _get_config("rsi_high", 85)
    slippage_cap = _get_config("slippage_cap_pct", 1.5)
    liq_test_usd = _get_config("liquidity_test_usd", 50000)
    
    for i, s in enumerate(candidates_to_check):
        try:
            if i % 10 == 0: logger.info(f"[Scan] Progress: {i}/{len(candidates_to_check)}")
            
            candles = _fetch_bybit_candles(s, interval="1", limit=30)
            if len(candles) < 20: 
                logger.info(f"  [X] {s}: Insufficient candle data")
                continue
            
            v1 = abs((candles[0]["close"] / candles[1]["close"] - 1) * 100)
            rsi = _calc_rsi([c["close"] for c in candles])
            
            if v1 < min_vol: 
                logger.info(f"  [X] {s}: Volatility too low ({v1:.2f}% < {min_vol}%)")
                continue
            if rsi > rsi_high or rsi < rsi_low: 
                logger.info(f"  [X] {s}: RSI Exhaustion ({rsi:.1f})")
                continue
            
            # Level 2.B (Liquidity & Orderbook)
            ob = _fetch_bybit_orderbook(s, limit=50)
            slippage = _calc_slippage(ob, liq_test_usd)
            if slippage > slippage_cap: 
                logger.info(f"  [X] {s}: Slippage too high ({slippage:.2f}% @ ${liq_test_usd})")
                continue
            
            score = v1 * 20 + (100 - slippage * 30)
            logger.info(f"  [+] {s} PASSED technical filter (Score: {score:.2f})")
            results.append((s, score))
            time.sleep(0.01)
        except Exception as e:
            logger.error(f"  [!] Error checking {s}: {e}")
    
    final_picks = sorted(results, key=lambda x: x[1], reverse=True)
    logger.info(f"[Scan] Found {len(final_picks)} qualified candidates for AI Audit.")
    return [p[0] for p in final_picks[:audit_limit]]

# --- AI AUDIT (TIER 3) ---
def _build_sniper_analysis(symbol: str) -> Optional[dict]:
    """Contextual audit with RRR enforcement and Market Snapshot."""
    global_data = _fetch_all_bybit_tickers()
    if symbol not in global_data: return None
    
    ticker = global_data[symbol]
    candles_h4 = _fetch_bybit_candles(symbol, interval="240", limit=2)
    h4_high = candles_h4[0]["high"] if candles_h4 else ticker["high24h"]
    
    ob = _fetch_bybit_orderbook(symbol)
    bid_vol = sum(float(b[1]) for b in ob.get("b", []))
    ask_vol = sum(float(a[1]) for a in ob.get("a", []))
    imbalance = bid_vol / ask_vol if ask_vol > 0 else 1.0
    
    # Level 3 Analysis (Whale & Sentiment)
    whales = _detect_whale_accumulation(symbol, ob)
    sentiment = _calc_crowd_sentiment(symbol, ticker["funding"])
    
    whale_info = "None"
    if whales:
        whale_info = ", ".join([f"{w['hits']}x wall at ${w['price']}" for w in whales])
    
    mode = get_bot_mode()
    target_rrr = _get_config("target_rrr", 2.0)
    rsi_low = _get_config("rsi_low", 15)
    rsi_high = _get_config("rsi_high", 85)
    
    prompt = f"""
    Analyze {symbol} (Bybit) @ ${ticker['price']}
    MODE: {mode} | MARKET SENTIMENT: {sentiment}
    WHALE ACTIVITY: {whale_info}
    
    METRICS:
    - 24h High/Low: ${ticker['high24h']} / ${ticker['low24h']}
    - H4 Local High: ${h4_high}
    - Funding: {ticker['funding']} | OI: {ticker['oi']}
    - L2 Imbalance: {imbalance:.2f}x
    
    STRICT RULES:
    1. Reward-to-Risk Ratio (RRR) MUST be 1:{target_rrr} or better.
    2. Respect RSI boundaries: {rsi_low} - {rsi_high}.
    3. Place Stop Loss behind logical H1/H4 levels.
    4. If Whale activity opposes the trend, be cautious.
    
    Respond ONLY in JSON (schema: signal, confidence, labels, summary, entry, exit, stop_loss, time_to_tp_hours).
    """
    
    # AI Cascade
    metrics = {
        "price": ticker["price"],
        "funding": ticker["funding"],
        "oi": ticker["oi"],
        "imbalance": imbalance,
        "sentiment": sentiment,
        "whale_tags": whale_info,
        "rrr_target": target_rrr
    }
    
    try:
        res = _call_ai_logic(prompt)
        # Shadow Log all verdicts
        _log_ai_shadow(symbol, res, metrics)
        
        if res and res.get("signal") != "skip":
            return {"symbol": symbol, "data": res, "model": "Gemini-Pro", "whales": whales, "sentiment": sentiment}
        elif res and res.get("signal") == "skip":
            _COOLDOWN_DICT[symbol] = _utc_now() + timedelta(minutes=30)
    except: pass
    return None

def _call_ai_logic(prompt: str) -> dict:
    """Cascade: Gemini -> Groq -> Skip"""
    # 1. Primary: Gemini (using 'gemini-1.5-flash-latest' for stability)
    url_gemini = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash-latest:generateContent"
    headers_gemini = {"Content-Type": "application/json"}
    payload_gemini = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        r = requests.post(f"{url_gemini}?key={GEMINI_API_KEY}", json=payload_gemini, headers=headers_gemini, timeout=12)
        if r.status_code == 200:
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            logger.info(f"Gemini Response: {text}")
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match: return json.loads(match.group())
        logger.warning(f"  [AI Warning] Gemini failed (Status: {r.status_code}, Msg: {r.text[:100]}). Switching to Groq...")
    except Exception as e:
        logger.warning(f"  [AI Warning] Gemini Error: {e}. Switching to Groq...")

    # 2. Fallback: Groq (Llama-3 70B)
    if GROQ_API_KEY:
        url_groq = "https://api.groq.com/openai/v1/chat/completions"
        headers_groq = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload_groq = {
            "model": "llama3-70b-8192",
            "messages": [
                {"role": "system", "content": "You are a crypto trading assistant. You must respond ONLY in valid JSON format."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        try:
            r = requests.post(url_groq, json=payload_groq, headers=headers_groq, timeout=12)
            if r.status_code == 200:
                content = r.json()["choices"][0]["message"]["content"]
                logger.info(f"Groq Response: {content}")
                return json.loads(content)
            logger.warning(f"  [AI Warning] Groq failed (Status: {r.status_code}, Msg: {r.text[:100]}).")
        except Exception as e:
            logger.error(f"  [AI Warning] Groq Error: {e}")

    return {"signal": "skip"}

def refresh_crypto_sniper_snapshot() -> dict[str, Any]:
    from notifications import send_telegram_notification
    candidates = _scout_top_crypto_candidates()
    approved_signals = []
    
    for s in candidates:
        analysis = _build_sniper_analysis(s) # Note: _build_sniper_analysis already calls _log_ai_shadow
        if analysis:
            approved_signals.append(analysis)
    
    if not approved_signals:
        return {"status": "done", "symbol": None}

    # Sort by confidence score (descending) and pick the best one
    approved_signals.sort(key=lambda x: x["data"].get("confidence", 0), reverse=True)
    best = approved_signals[0]
    
    s = best["symbol"]
    d = best["data"]
    w_list = best.get("whales", [])
    sentiment = best.get("sentiment", "⚪ Neutral")
    
    # Formatting Whale block
    whale_html = ""
    if w_list:
        whale_html = "\n\n🐳 <b>WHALE ACTIVITY DETECTED</b>\n"
        for w in w_list:
            whale_html += f"• {w['hits']}x Wall at <b>${w['price']}</b> ({'Buy' if w['side']=='b' else 'Sell'})\n"
    
    labels_str = " ".join([f"<code>[{l}]</code>" for l in d.get("labels", [])])
    
    content = (
        f"🎯 <b>{s} SIGNAL BRIEFING</b>\n"
        f"{labels_str}\n\n"
        f"📈 <b>Sentiment:</b> {sentiment}\n"
        f"📊 <b>Confidence:</b> <code>{d['confidence']}%</code>\n\n"
        f"<blockquote>{d.get('summary', '')}</blockquote>"
        f"{whale_html}\n"
        f"—— <b>STRATEGY</b> ——\n"
        f"⚡ <b>Action:</b> <code>{d['signal'].upper()}</code>\n"
        f"🚀 <b>Entry:</b> <code>${d.get('entry')}</code>\n"
        f"🛑 <b>Target:</b> <code>${d.get('exit')}</code>\n"
        f"🛡️ <b>Stop Loss:</b> <code>${d.get('stop_loss')}</code>\n\n"
        f"<i>Powered by Crypto Sniper v8.0</i>"
    )
    send_telegram_notification(content)
    return {"status": "done", "symbol": s}

def get_market_intel_overview():
    return {
        "status": "active",
        "mode": get_bot_mode(),
        "scout_limit": get_scout_limit(),
        "audit_limit": get_audit_limit(),
        "interval_min": get_crypto_sniper_interval() // 60,
        "min_vol": get_min_volatility(),
        "connection": "optimized",
        "last_scan": _utc_now_iso_z()
    }
