import asyncio
import json
from datetime import datetime
from sqlalchemy import select
from core.database import AsyncSessionLocal
from models.trading import AIShadowLog, SystemConfig
from market_intel import _fetch_bybit_candles # Still using old fetcher for now, but should refactor to async too

async def get_config_val(key: str, default: str) -> str:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
        config = result.scalar_one_or_none()
        return config.value if config else default

async def run_backtest_simulation(limit: int = 50):
    """
    Core Backtest Engine (Async Refactored).
    Iterates through ai_shadow_log and simulates trade outcomes.
    """
    signals = []
    
    # 1. Fetch historical signals
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AIShadowLog)
            .where(AIShadowLog.verdict.in_(['buy', 'sell']))
            .order_by(AIShadowLog.created_at.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        for r in rows:
            signals.append({
                "id": r.id, "symbol": r.symbol, "side": r.verdict,
                "entry": r.entry, "tp": r.exit, "sl": r.stop_loss,
                "time": r.created_at, "metrics": json.loads(r.metrics_json) if r.metrics_json else {}
            })
    
    if not signals: 
        return {"status": "error", "message": "No signals found for simulation."}
    
    results = []
    total_pnl = 0.0
    wins = 0
    losses = 0
    
    # Simulation settings from DB
    priority = await get_config_val("emulator_conflict_priority", "SL-First")
    precision = await get_config_val("emulator_scan_precision", "M1")
    
    interval_map = {"M1": "1", "M5": "5", "M15": "15"}
    bybit_interval = interval_map.get(precision, "1")

    print(f"[Emulator] Simulating {len(signals)} signals...")

    for s in signals:
        # Note: _fetch_bybit_candles is still blocking, we should ideally wrap it or make it async
        # For now, let's at least process signals. 
        # IMPROVEMENT: Should use httpx async client here.
        candles = await asyncio.to_thread(_fetch_bybit_candles, s["symbol"], interval=bybit_interval, limit=200)
        if not candles: continue
        
        outcome = "IDLE"
        pnl = 0.0
        
        entry = float(s["entry"])
        tp = float(s["tp"])
        sl = float(s["sl"])
        
        # Quick validation
        if entry <= 0: continue

        for c in candles:
            low = c["low"]
            high = c["high"]
            
            if s["side"] == "buy":
                if priority == "SL-First":
                    if low <= sl: 
                        outcome, pnl = "LOSS", ((sl / entry) - 1) * 100
                        break
                    if high >= tp: 
                        outcome, pnl = "WIN", ((tp / entry) - 1) * 100
                        break
                else:
                    if high >= tp: 
                        outcome, pnl = "WIN", ((tp / entry) - 1) * 100
                        break
                    if low <= sl: 
                        outcome, pnl = "LOSS", ((sl / entry) - 1) * 100
                        break
            else: # sell
                if priority == "SL-First":
                    if high >= sl: 
                        outcome, pnl = "LOSS", ((entry / sl) - 1) * 100
                        break
                    if low <= tp: 
                        outcome, pnl = "WIN", ((entry / tp) - 1) * 100
                        break
                else:
                    if low <= tp: 
                        outcome, pnl = "WIN", ((entry / tp) - 1) * 100
                        break
                    if high >= sl: 
                        outcome, pnl = "LOSS", ((entry / sl) - 1) * 100
                        break
        
        if outcome == "WIN": wins += 1
        if outcome == "LOSS": losses += 1
        total_pnl += pnl
        
        results.append({
            "symbol": s["symbol"],
            "side": s["side"],
            "outcome": outcome,
            "pnl": pnl,
            "time": str(s["time"])
        })
        
    return {
        "status": "success",
        "stats": {
            "winrate": (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0,
            "total_pnl": total_pnl,
            "samples": len(results)
        },
        "trades": results
    }
