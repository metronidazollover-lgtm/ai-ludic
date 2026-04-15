import asyncio
import json
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy import select, update, insert
from core.config import settings
from core.database import AsyncSessionLocal
from core.http import http_manager
from core.logging_config import logger
from models.trading import SystemConfig, BybitAssetMeta, WhaleWallMemory, AIShadowLog
from models.schemas import BybitTicker, Candle, AIVerdict
from services.state_service import state_service

class MarketIntelService:
    def __init__(self):
        self.base_url = settings.BYBIT_API_URL

    async def _get_config(self, key: str, default: Any) -> Any:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
            config = result.scalar_one_or_none()
            if not config: return default
            val = config.value
            try:
                if isinstance(default, int): return int(val)
                if isinstance(default, float): return float(val)
                return val
            except: return default

    # --- ADVANCED METRICS (Whales & Sentiment) ---
    async def detect_whales(self, symbol: str, orderbook: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Restore Whale detection logic
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(BybitAssetMeta.whale_threshold).where(BybitAssetMeta.symbol == symbol))
            threshold = result.scalar() or 100000.0
        
        whales = []
        now = datetime.now(timezone.utc).isoformat()
        
        async with AsyncSessionLocal() as db:
            for side in ["b", "a"]:
                for p_str, s_str in orderbook.get(side, []):
                    p, s = float(p_str), float(s_str)
                    val = p * s
                    if val >= threshold:
                        # Check memory
                        res = await db.execute(select(WhaleWallMemory).where(
                            WhaleWallMemory.symbol == symbol, 
                            WhaleWallMemory.price == p, 
                            WhaleWallMemory.side == side
                        ))
                        wall = res.scalar_one_or_none()
                        if wall:
                            wall.hits += 1
                            wall.last_seen = now
                            if wall.hits >= 2:
                                whales.append({"side": side, "price": p, "val": val, "hits": wall.hits})
                        else:
                            db.add(WhaleWallMemory(symbol=symbol, price=p, side=side, size=s, hits=1, last_seen=now))
            await db.commit()
        return whales

    async def calc_sentiment(self, symbol: str, funding: str) -> str:
        try:
            f = float(funding)
            if f > 0.0005: return "🔴 EXTREME LONGS (Bull Trap Risk)"
            if f < -0.0005: return "🟢 EXTREME SHORTS (Squeeze Risk)"
            if f > 0.0001: return "🟠 Leaning Long"
            if f < -0.0001: return "🔵 Leaning Short"
        except: pass
        return "⚪ Neutral"

    async def sync_market_metadata(self):
        """Restore Big Sweep logic."""
        tickers = await self.fetch_tickers()
        if not tickers: return
        
        whale_ratio = (await self._get_config("whale_threshold_pct", 0.1)) / 100.0
        now = datetime.now(timezone.utc).isoformat()
        
        async with AsyncSessionLocal() as db:
            for t in tickers:
                if not t.symbol.endswith("USDT"): continue
                turnover = float(t.turnover24h)
                threshold = turnover * whale_ratio
                
                # Dynamic constraints
                if t.symbol in ["BTCUSDT", "ETHUSDT"]:
                    threshold = max(threshold, 1000000)
                else:
                    threshold = max(20000, min(threshold, 500000))
                
                # Bulk update/insert would be better, but ORM update is fine for now
                await db.execute(
                    update(BybitAssetMeta)
                    .where(BybitAssetMeta.symbol == t.symbol)
                    .values(daily_turnover=turnover, whale_threshold=threshold, last_sync=now)
                )
                # If not exists, insert
                # (SQLAlchemy 2.0 has INSERT ON CONFLICT but depends on backend)
            await db.commit()
        logger.info("market_metadata_synced")

    # --- Bybit V5 Async Clients ---
    async def fetch_tickers(self) -> List[BybitTicker]:
        client = await http_manager.get_client()
        try:
            resp = await client.get(f"{self.base_url}/v5/market/tickers", params={"category": "linear"})
            data = resp.json()
            if data.get("retCode") == 0:
                return [BybitTicker(**t) for t in data["result"].get("list", [])]
        except Exception as e:
            logger.error("bybit_fetch_tickers_failed", error=str(e))
        return []

    async def fetch_candles(self, symbol: str, interval: str = "60", limit: int = 100) -> List[Candle]:
        client = await http_manager.get_client()
        params = {"category": "linear", "symbol": symbol, "interval": interval, "limit": limit}
        try:
            resp = await client.get(f"{self.base_url}/v5/market/kline", params=params)
            data = resp.json()
            if data.get("retCode") == 0:
                return [Candle(
                    close=float(c[4]), high=float(c[2]), low=float(c[3]), volume=float(c[5])
                ) for c in data["result"].get("list", [])]
        except: pass
        return []

    async def fetch_orderbook(self, symbol: str, limit: int = 25) -> Dict[str, Any]:
        client = await http_manager.get_client()
        params = {"category": "linear", "symbol": symbol, "limit": limit}
        try:
            resp = await client.get(f"{self.base_url}/v5/market/orderbook", params=params)
            data = resp.json()
            if data.get("retCode") == 0: return data["result"]
        except: pass
        return {"a": [], "b": []}

    # --- Metrics & Logic ---
    @staticmethod
    def calc_rsi(prices: List[float], period: int = 14) -> float:
        if len(prices) < period + 1: return 50.0
        deltas = [prices[i] - prices[i+1] for i in range(len(prices)-1)]
        gains = [d if d > 0 else 0 for d in deltas[:period]]
        losses = [-d if d < 0 else 0 for d in deltas[:period]]
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0: return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    async def check_symbol_candidate(self, ticker: BybitTicker) -> Optional[Dict[str, Any]]:
        symbol = ticker.symbol
        if not symbol.endswith("USDT"): return None
        if state_service.is_in_cooldown(symbol): return None

        min_vol = await self._get_config("min_volatility_pct", 0.5)
        
        candles = await self.fetch_candles(symbol, interval="1", limit=30)
        if len(candles) < 20: return None

        # Level 1: Volatility & RSI
        v1 = abs((candles[0].close / candles[1].close - 1) * 100)
        rsi = self.calc_rsi([c.close for c in candles])

        if v1 < min_vol: return None
        
        rsi_low = await self._get_config("rsi_low", 15)
        rsi_high = await self._get_config("rsi_high", 85)
        if rsi > rsi_high or rsi < rsi_low: return None

        score = v1 * 20 # Simple scoring
        return {"symbol": symbol, "score": score, "price": float(ticker.lastPrice)}

    async def scout_candidates(self) -> List[str]:
        tickers = await self.fetch_tickers()
        if not tickers: return []

        scout_limit = await self._get_config("scout_limit", 50)
        # Sort by turnover
        top_tickers = sorted(tickers, key=lambda x: float(x.turnover24h), reverse=True)[:scout_limit]
        
        # Parallel candidate check
        tasks = [self.check_symbol_candidate(t) for t in top_tickers]
        results = await asyncio.gather(*tasks)
        
        candidates = [r for r in results if r]
        candidates.sort(key=lambda x: x["score"], reverse=True)
        
        audit_limit = await self._get_config("audit_limit", 5)
        return [c["symbol"] for c in candidates[:audit_limit]]

    # --- AI Integration ---
    async def call_ai(self, prompt: str) -> Optional[AIVerdict]:
        client = await http_manager.get_client()
        
        # Try Gemini
        if settings.GEMINI_API_KEY:
            url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash-latest:generateContent?key={settings.GEMINI_API_KEY}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            try:
                resp = await client.post(url, json=payload, timeout=12)
                if resp.status_code == 200:
                    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                    return self._parse_ai_response(text)
            except Exception as e:
                logger.warning("ai_gemini_failed", error=str(e))

        # Fallback to Groq
        if settings.GROQ_API_KEY:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
            payload = {
                "model": "llama3-70b-8192",
                "messages": [
                    {"role": "system", "content": "You are a crypto trading assistant. Respond ONLY in valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            }
            try:
                resp = await client.post(url, json=payload, headers=headers, timeout=12)
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    return self._parse_ai_response(content)
            except Exception as e:
                logger.error("ai_groq_failed", error=str(e))

        return None

    def _parse_ai_response(self, text: str) -> Optional[AIVerdict]:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                return AIVerdict(**data)
            except: pass
        return None

    async def build_analysis(self, symbol: str) -> Optional[Dict[str, Any]]:
        # This mirrors build_sniper_analysis but async
        tickers = await self.fetch_tickers()
        ticker = next((t for t in tickers if t.symbol == symbol), None)
        if not ticker: return None

        ob = await self.fetch_orderbook(symbol)
        # whale detection, etc (to be simplified for now)
        
        mode = await self._get_config("trading_mode", "Conservative")
        
        prompt = f"Analyze {symbol} @ ${ticker.lastPrice}. MODE: {mode}. Respond in JSON with signal, confidence, labels, summary, entry, exit, stop_loss."
        
        verdict = await self.call_ai(prompt)
        
        # Log to Shadow AI
        if verdict:
            async with AsyncSessionLocal() as db:
                db.add(AIShadowLog(
                    symbol=symbol,
                    verdict=verdict.signal,
                    confidence=verdict.confidence,
                    reasoning=verdict.summary,
                    entry=verdict.entry,
                    exit=verdict.exit,
                    stop_loss=verdict.stop_loss,
                    labels_json=json.dumps(verdict.labels)
                ))
                await db.commit()
            
            if verdict.signal == "skip":
                state_service.set_cooldown(symbol, 30)
            
            return {"symbol": symbol, "verdict": verdict}
        return None

market_intel_service = MarketIntelService()
