"""
Market intelligence snapshots and read models for Crypto Sniper.
Focused on Hyperliquid market data, funding rates, and AI-driven volatility analysis.
"""

from __future__ import annotations

import json
import os
from collections import Counter

from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Dict, List
import time
import re
from pathlib import Path

import requests
try:
    from openrouter import OpenRouter
except ImportError:
    OpenRouter = None

from cache import delete_pattern, get_json, set_json
from database import get_db_connection
from notifications import send_telegram_notification

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

# Global state for symbol rotation (cooldown)
_RECENT_ANALYZED_SYMBOLS: list[str] = []
_MAX_COOLDOWN_SIZE = 20

# Intervals
_DYNAMIC_INTERVALS = {
    "crypto_sniper": int(os.getenv("CRYPTO_SNIPER_REFRESH_INTERVAL", "300"))
}

def get_crypto_sniper_interval() -> int:
    return _DYNAMIC_INTERVALS["crypto_sniper"]

def set_crypto_sniper_interval(seconds: int):
    _DYNAMIC_INTERVALS["crypto_sniper"] = max(60, seconds)
    print(f"[Config] Crypto Sniper interval updated to {seconds}s")

MARKET_INTEL_OVERVIEW_CACHE_TTL_SECONDS = 300
HYPERLIQUID_API_URL = os.environ.get("HYPERLIQUID_API_URL", "https://api.hyperliquid.xyz/info").strip()

MARKET_INTEL_CACHE_PREFIX = "market_intel"


def _cache_key(*parts: object) -> str:
    return ":".join([MARKET_INTEL_CACHE_PREFIX, *[str(part) for part in parts]])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso_z() -> str:
    return _utc_now().isoformat().replace("+00:00", "Z")


def _extract_openrouter_text(response: Any) -> str:
    choices = getattr(response, "choices", None)
    if choices is None and isinstance(response, dict):
        choices = response.get("choices")
    if not choices:
        return ""

    first_choice = choices[0]
    message = getattr(first_choice, "message", None)
    if message is None and isinstance(first_choice, dict):
        message = first_choice.get("message")
    if message is None:
        return ""

    content = getattr(message, "content", None)
    if content is None and isinstance(message, dict):
        content = message.get("content")

    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and isinstance(part.get("text"), str):
                parts.append(part["text"])
        return "\n".join(part.strip() for part in parts if part and part.strip()).strip()
    return ""




def _gemini_generate_text(prompt: str, system_instruction: Optional[str] = None) -> Optional[tuple[str, str]]:
    """
    Generate text using Google Gemini with robust retries and model fallbacks.
    Returns: (generated_text, model_name) or None
    Designed to handle Free Tier instability (503, 429, timeouts).
    """
    if not GEMINI_API_KEY:
        return None
    
    # List of models to try in order of preference/stability
    # Based on user's available model list
    models = [
        "gemini-3-flash-preview",
        "gemini-3.1-pro-preview",
        "gemini-3-pro-preview",
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.0-flash", 
        "gemini-flash-latest", 
        "gemini-2.5-flash-lite",
        "gemini-1.5-flash-latest"
    ]

    # 1. Gemini Chain (Primary)
    headers = {"Content-Type": "application/json"}
    payload: dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 2048,
            "temperature": 0.1
        }
    }

    if system_instruction:
        payload["system_instruction"] = {
            "parts": [{"text": system_instruction}]
        }

    any_429 = False
    
    for model_name in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        
        try:
            # Single attempt per model to be gentle on RPM
            response = requests.post(url, headers=headers, json=payload, timeout=45)
            
            if response.status_code == 429:
                print(f"[Gemini 429] Model {model_name} is rate limited. Trying next fallback...")
                any_429 = True
                continue
                
            if response.status_code == 404:
                continue

            response.raise_for_status()
            data = response.json()
            
            candidates = data.get("candidates", [])
            if not candidates:
                continue
                
            candidate = candidates[0]
            parts = candidate.get("content", {}).get("parts", [])
            if not parts:
                continue
            
            full_text = "".join(part.get("text", "") for part in parts)
            if full_text.strip():
                return full_text.strip(), model_name

        except Exception as e:
            # For connection/timeout errors, try next fallback
            pass

    # 2. Try Groq LAST (Final Fallback - reliable Llama 3.3)
    if GROQ_API_KEY:
        print("[AI Fallback] Gemini chain exhausted. Trying Groq/Llama...")
        groq_result = _groq_generate_text(prompt, system_instruction=system_instruction)
        if groq_result:
            return groq_result

    if any_429:
        # Both Groq and Gemini are rate-limited - forced break
        print(f"[AI Cooldown] All primary and fallback models returned 429. Sleeping 300s...")
        time.sleep(300)
    else:
        print("[AI Critical] All providers failed without clear recovery path.")
        
    return None


def _groq_generate_text(prompt: str, system_instruction: Optional[str] = None) -> Optional[tuple[str, str]]:
    """
    Fallback generator using Groq (OpenAI-compatible) API.
    Uses llama-3.3-70b-versatile for high quality.
    """
    if not GROQ_API_KEY:
        return None
        
    model_name = "llama-3.3-70b-versatile"
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 1024
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 429:
            print(f"[Groq 429] Groq is also rate limited.")
            return None
            
        response.raise_for_status()
        data = response.json()
        
        choices = data.get("choices", [])
        if not choices:
            return None
            
        content = choices[0].get("message", {}).get("content", "")
        if content.strip():
            return content.strip(), model_name
            
    except Exception as e:
        print(f"[Groq Error] {e}")
        
    return None







def _fetch_hyperliquid_top_pairs(limit: int = 50) -> list[str]:
    """Fetch top active pairs from Hyperliquid by 24h volume."""
    url = "https://api.hyperliquid.xyz/info"
    payload = {"type": "metaAndAssetCtxs"}
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # data[1] usually contains asset contexts with volume
        if isinstance(data, list) and len(data) >= 2:
            meta = data[0].get("universe", [])
            ctxs = data[1]
            
            # Match meta with ctxs and sort by dayVlm
            pairs = []
            for i, asset in enumerate(meta):
                if i < len(ctxs):
                    pairs.append({
                        "name": asset["name"],
                        "volume": float(ctxs[i].get("dayVlm", 0))
                    })
            
            # Sort by volume descending
            pairs.sort(key=lambda x: x["volume"], reverse=True)
            return [p["name"] for p in pairs[:limit]]
            
    except Exception as e:
        print(f"[Hyperliquid Error] Failed to fetch top pairs: {e}")
        
    # Fallback to a sensible default list
    return ["BTC", "ETH", "SOL", "AVAX", "NEAR", "ARB", "OP", "MATIC", "LINK", "DOT"]


def _fetch_hyperliquid_candles(symbol: str, interval: str = "1h", limit: int = 100) -> list[dict[str, Any]]:
    """Fetch candles from Hyperliquid Info API."""
    end_time = int(time.time() * 1000)
    # Approx duration to get enough candles
    multiplier = {"1m": 60, "5m": 300, "1h": 3600, "1d": 86400}
    start_time = end_time - (limit * multiplier.get(interval, 86400) * 1000)
    
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": symbol,
            "interval": interval,
            "startTime": start_time,
            "endTime": end_time
        }
    }
    try:
        response = requests.post(HYPERLIQUID_API_URL, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            return []
        
        # Hyperliquid returns [ {t: ms, o: str, h: str, l: str, c: str, v: str}, ... ]
        # We normalize to {date: iso, close: float}
        rows = []
        for c in data:
            try:
                dt = datetime.fromtimestamp(c["t"] / 1000, tz=timezone.utc).isoformat()
                rows.append({
                    "date": dt,
                    "close": float(c["c"]),
                    "high": float(c["h"]),
                    "low": float(c["l"]),
                    "volume": float(c["v"])
                })
            except (KeyError, ValueError, TypeError):
                continue
        
        rows.sort(key=lambda x: x["date"], reverse=True)
        return rows
    except Exception as e:
        print(f"[Hyperliquid] Error fetching {symbol} {interval}: {e}")
        return []


def _calc_return_pct(series: list[dict[str, Any]], lookback_days: int) -> Optional[float]:
    if len(series) <= lookback_days:
        return None
    latest = float(series[0]["close"])
    previous = float(series[lookback_days]["close"])
    if previous == 0:
        return None
    return ((latest / previous) - 1.0) * 100.0


def _calc_average_volume(series: list[dict[str, Any]], start_index: int, count: int) -> Optional[float]:
    window = [float(row.get("volume") or 0) for row in series[start_index:start_index + count] if float(row.get("volume") or 0) > 0]
    if not window:
        return None
    return sum(window) / len(window)


def _calc_simple_moving_average(series: list[dict[str, Any]], window: int) -> Optional[float]:
    closes = [float(row["close"]) for row in series[:window]]
    if len(closes) < window:
        return None
    return sum(closes) / window








def get_market_intel_overview() -> dict[str, Any]:
    """Simplified overview focusing strictly on crypto sniper status."""
    return {
        "status": "active",
        "focus": "crypto",
        "last_refresh": _utc_now_iso_z()
    }



def _load_skill_context(skill_names: list[str]) -> str:
    """Load skill definitions from the skills directory to provide context to the AI."""
    root = Path(__file__).parent.parent.parent
    context_parts = []
    
    for name in skill_names:
        skill_path = root / "skills" / name / "SKILL.md"
        if not skill_path.exists():
            skill_path = root / "skills" / name / "skill.md"
            
        if skill_path.exists():
            try:
                content = skill_path.read_text(encoding="utf-8")
                # Remove frontmatter if present
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        content = parts[2].strip()
                context_parts.append(f"### Skill: {name}\n{content}")
            except Exception as e:
                print(f"[Skill Load Error] {name}: {e}")
                
    if not context_parts:
        return ""
        
    return "The following are the relevant platform skills and API documentation you must follow:\n\n" + "\n\n".join(context_parts)


def _scout_top_crypto_opportunity() -> Optional[str]:
    """Identify the best crypto trading setup from Top 50 active coins with rotation."""
    global _RECENT_ANALYZED_SYMBOLS
    
    # 1. Fetch Top 50 by volume
    candidates = _fetch_hyperliquid_top_pairs(limit=50)
    
    # 2. Filter out recently analyzed symbols (Rotation)
    available_candidates = [s for s in candidates if s not in _RECENT_ANALYZED_SYMBOLS]
    
    # If we ran out of new coins, clear half of the history
    if not available_candidates:
        _RECENT_ANALYZED_SYMBOLS = _RECENT_ANALYZED_SYMBOLS[len(_RECENT_ANALYZED_SYMBOLS)//2:]
        available_candidates = [s for s in candidates if s not in _RECENT_ANALYZED_SYMBOLS]

    best_symbol = None
    best_score = -1.0
    
    # We check top 20 available for speed in the background loop
    check_limit = 20
    for symbol in available_candidates[:check_limit]:
        try:
            candles = _fetch_hyperliquid_candles(symbol, interval="1h", limit=5)
            if not candles or len(candles) < 2:
                continue
            
            latest = candles[0]["close"]
            prev = candles[1]["close"]
            change = ((latest / prev) - 1) * 100
            
            # Scouting score: Absolute change (Volatility)
            score = abs(change)
            if score > best_score:
                best_score = score
                best_symbol = symbol
        except Exception:
            continue
            
    # Add to rotation history if picking a new one
    if best_symbol:
        _RECENT_ANALYZED_SYMBOLS.append(best_symbol)
        if len(_RECENT_ANALYZED_SYMBOLS) > _MAX_COOLDOWN_SIZE:
            _RECENT_ANALYZED_SYMBOLS.pop(0)

    return best_symbol


def _build_sniper_analysis(symbol: str) -> dict[str, Any]:
    """In-depth analysis for the sniper opportunity."""
    daily_candles = _fetch_hyperliquid_candles(symbol, interval="1d", limit=30)
    hourly_candles = _fetch_hyperliquid_candles(symbol, interval="1h", limit=24)
    
    if not daily_candles or not hourly_candles:
        raise RuntimeError(f"Insufficient candle data for sniper analysis of {symbol}")
        
    current_price = daily_candles[0]["close"]
    
    # Simple technicals
    ma20_d = _calc_simple_moving_average(daily_candles, 20)
    ma5_h = _calc_simple_moving_average(hourly_candles, 5)
    
    # Trend detection
    if current_price > ma5_h:
        verdict = "bullish"
    else:
        verdict = "bearish"
    
    # Load relevant skills for context
    skills_context = _load_skill_context(["market-intel", "tradesync"])
    
    system_prompt = (
        "You are an elite 'Sniper' trading agent on the AI-Trader platform.\n"
        "Your goal is to identify high-conviction trades (80%+ confidence).\n"
        f"{skills_context}\n\n"
        "Instructions:\n"
        "- Respond ONLY with a valid JSON object.\n"
        "- Do not include any conversational text before or after the JSON.\n"
        "- Use the metrics provided to justify your signal.\n"
        "- ALWAYS include a 'stop_loss' price based on recent support/resistance."
    )

    prompt = f"""
    Analyze the technical data for {symbol} (Crypto):
    - Current Price: ${current_price}
    - 24h Change: {((current_price / daily_candles[1]['close']) - 1)*100:.2f}%
    - 1h Change: {((current_price / hourly_candles[1]['close']) - 1)*100:.2f}%
    - 20-Day MA: {ma20_d}
    - 5-Hour MA: {ma5_h}

    Task:
    1. Decide signal: 'buy' (Long) or 'sell' (Short).
    2. Suggest LEVERAGE (between 2x and 100x).
    3. Provide a short conviction summary (max 2 sentences).
    4. MUST have at least 80% confidence or do not recommend.
    5. Calculate protective Stop Loss.

    Respond in this JSON format:
    {{
      "signal": "buy" | "sell",
      "leverage": "20x",
      "confidence": 85,
      "summary": "Reasoning...",
      "entry": 123.45,
      "exit": 130.00,
      "stop_loss": 118.50
    }}
    """
    
    result = _gemini_generate_text(prompt, system_instruction=system_prompt)
    if not result:
        return None
        
    ai_raw, model_id = result
    
    # Robust JSON extraction and safety checks
    ai_data = None
    if ai_raw:
        try:
            json_match = re.search(r"\{.*\}", ai_raw, re.DOTALL)
            if json_match:
                ai_data = json.loads(json_match.group(0))
            else:
                ai_data = json.loads(ai_raw)
        except Exception as e:
            print(f"[AI Parse Error] {e} | Raw: {ai_raw}")

    # STRICT AI POLICY: If no signal was generated, skip this cycle
    if not isinstance(ai_data, dict) or not ai_data.get("signal"):
        print(f"[Crypto Sniper] AI analysis failed for {symbol}. Skipping signal as per strict policy.")
        return None
    
    # Store model name in metadata
    ai_data["meta_model"] = model_id
    
    # Ensure other keys are present with safe defaults
    confidence = ai_data.get("confidence", ai_data.get("signal_score", 70))
    leverage = ai_data.get("leverage", "5x")
    summary = ai_data.get("summary", "AI provided signal without detailed summary.")
    
    analysis = {
        "symbol": symbol,
        "market": "crypto",
        "current_price": current_price,
        "currency": "USD",
        "signal": ai_data["signal"],
        "signal_score": confidence,
        "trend_status": verdict,
        "support_levels": [current_price * 0.95],
        "resistance_levels": [current_price * 1.05],
        "bullish_factors": ["High volatility opportunity", f"Leverage: {leverage}"],
        "risk_factors": ["High risk setup", "Futures market"],
        "summary": summary,
        "analysis": ai_data
    }
    # Final Safety Check: Enforce 80% confidence threshold strictly in code
    if confidence < 80:
        print(f"[Crypto Sniper] AI signal for {symbol} rejected due to low confidence: {confidence}% (Required: 80%)")
        return None

    return analysis


def refresh_crypto_sniper_snapshot() -> dict[str, Any]:
    """Run the sniper loop: Scout -> Analyze -> Snapshot."""
    symbol = _scout_top_crypto_opportunity()
    if not symbol:
        return {"status": "error", "message": "No opportunity found"}
        
    analysis = _build_sniper_analysis(symbol)
    if not analysis:
        return {"status": "error", "message": "AI analysis unavailable"}
        
    created_at = _utc_now_iso_z()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Insert Snapshot
        cursor.execute("""
            INSERT INTO stock_analysis_snapshots (
                symbol, market, analysis_id, current_price, currency, signal,
                signal_score, trend_status, support_levels_json, resistance_levels_json,
                bullish_factors_json, risk_factors_json, summary_text, analysis_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            symbol, "crypto", f"sniper:{symbol}:{created_at}", analysis["current_price"], "USD",
            analysis["signal"], analysis["signal_score"], analysis["trend_status"],
            json.dumps(analysis["support_levels"]), json.dumps(analysis["resistance_levels"]),
            json.dumps(analysis["bullish_factors"]), json.dumps(analysis["risk_factors"]),
            analysis["summary"], json.dumps(analysis), created_at
        ))
        
        # 2. Get Signal ID from sequence
        cursor.execute("INSERT INTO signal_sequence (created_at) VALUES (?)", (created_at,))
        signal_id = cursor.lastrowid
        
        # 3. Post as Marketplace Signal (Agent 4 = CryptoOracle)
        # Re-map signal to marketplace style
        ai_data = analysis["analysis"]
        model_name = ai_data.get("meta_model", "Unknown Gemini")
        recommendation = "Long" if analysis["signal"] == "buy" else "Short"
        import html
        content = (
            f"🧠 <b>AI Model:</b> {model_name}\n"
            f"📊 <b>Confidence:</b> {analysis['signal_score']}%\n\n"
            f"{html.escape(analysis['summary'])}\n\n"
            f"Recommendation: <b>{recommendation}</b>\n"
            f"🎯 Recommended Leverage: {ai_data.get('leverage', '5x')}\n"
            f"🚀 Entry: ${ai_data.get('entry')}\n"
            f"🛑 Target/Exit: ${ai_data.get('exit')}\n"
            f"🛡️ Stop Loss: ${ai_data.get('stop_loss', 'N/A')}"
        )
        
        cursor.execute("""
            INSERT INTO signals (
                signal_id, agent_id, message_type, market, signal_type, symbol, 
                side, entry_price, exit_price, title, content, timestamp, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            signal_id, 4, "strategy", "crypto", "position", symbol,
            analysis["signal"], ai_data.get("entry"), ai_data.get("exit"),
            f"🎯 Sniper Opportunity: {symbol} ({ai_data.get('leverage', '10x')})",
            content, int(time.time()), created_at
        ))
        
        conn.commit()

        # 4. Send Telegram Notification
        try:
            telegram_title = f"<b>🎯 Sniper Opportunity: {symbol} ({ai_data.get('leverage', '10x')})</b>"
            telegram_msg = f"{telegram_title}\n\n{content}"
            if send_telegram_notification(telegram_msg):
                print(f"[Telegram] Signal for {symbol} sent successfully!")
            else:
                print(f"[Telegram] Failed to send signal for {symbol}")
        except Exception as te:
            print(f"[Telegram Notification Error] {te}")
            
    finally:
        conn.close()
        
    return {"symbol": symbol, "signal": analysis["signal"], "created_at": created_at}



