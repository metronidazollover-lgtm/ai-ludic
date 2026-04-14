import time
from datetime import datetime, timedelta
import json
from database import get_db_connection
# We reuse fetching logic from market_intel
from market_intel import _fetch_bybit_candles, _get_config

def run_backtest_simulation(limit: int = 50):
    """
    Core Backtest Engine.
    Iterates through ai_shadow_log and simulates trade outcomes.
    """
    signals = []
    
    # 1. Fetch historical signals
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, symbol, verdict, entry, exit, stop_loss, created_at, metrics_json 
            FROM ai_shadow_log 
            WHERE verdict IN ('buy', 'sell')
            ORDER BY created_at DESC LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        for r in rows:
            signals.append({
                "id": r[0], "symbol": r[1], "side": r[2],
                "entry": r[3], "tp": r[4], "sl": r[5],
                "time": r[6], "metrics": json.loads(r[7])
            })
    finally: conn.close()
    
    if not signals: return {"status": "error", "message": "No signals found for simulation."}
    
    results = []
    total_pnl = 0.0
    wins = 0
    losses = 0
    
    # Simulation settings from DB
    priority = _get_config("emulator_conflict_priority", "SL-First")
    fallback_limit = int(_get_config("emulator_fallback_time_limit", 24))
    precision = _get_config("emulator_scan_precision", "M1")
    
    # Map precision to Bybit intervals
    interval_map = {"M1": "1", "M5": "5", "M15": "15"}
    bybit_interval = interval_map.get(precision, "1")

    print(f"[Emulator] Simulating {len(signals)} signals...")

    for s in signals:
        # 2. Fetch candles starting from signal time
        candles = _fetch_bybit_candles(s["symbol"], interval=bybit_interval, limit=200) # Check next standard set
        if not candles: continue
        
        outcome = "IDLE"
        pnl = 0.0
        
        entry = float(s["entry"])
        tp = float(s["tp"])
        sl = float(s["sl"])
        
        for c in candles:
            low = c["low"]
            high = c["high"]
            
            # Simple simulation logic
            if s["side"] == "buy":
                # Check for SL first if conservative
                if priority == "SL-First":
                    if low <= sl: outcome, pnl = "LOSS", -abs((entry/sl - 1)*100); break
                    if high >= tp: outcome, pnl = "WIN", abs((tp/entry - 1)*100); break
                else:
                    if high >= tp: outcome, pnl = "WIN", abs((tp/entry - 1)*100); break
                    if low <= sl: outcome, pnl = "LOSS", -abs((entry/sl - 1)*100); break
            else: # sell
                if priority == "SL-First":
                    if high >= sl: outcome, pnl = "LOSS", -abs((sl/entry - 1)*100); break
                    if low <= tp: outcome, pnl = "WIN", abs((entry/tp - 1)*100); break
                else:
                    if low <= tp: outcome, pnl = "WIN", abs((entry/tp - 1)*100); break
                    if high >= sl: outcome, pnl = "LOSS", -abs((sl/entry - 1)*100); break
        
        if outcome == "WIN": wins += 1
        if outcome == "LOSS": losses += 1
        total_pnl += pnl
        
        results.append({
            "symbol": s["symbol"],
            "side": s["side"],
            "outcome": outcome,
            "pnl": pnl,
            "time": s["time"]
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
