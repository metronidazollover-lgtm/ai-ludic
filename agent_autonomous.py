import requests
import time
from datetime import datetime

# Configuration
API_BASE = "http://localhost:8888/api"
TOKEN = "wEYz0CeYMYtacP0vvl8aWPGeM8Sc30uUa1pyGlc2QCw"
POLL_INTERVAL = 60 # Check every minute

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def get_recent_signals():
    try:
        # Fetch operations from last 10 minutes
        response = requests.get(f"{API_BASE}/signals/feed?message_type=operation&limit=10")
        response.raise_for_status()
        return response.json().get("signals", [])
    except Exception as e:
        print(f"[Error] Failed to fetch signals: {e}")
        return []

def get_my_positions():
    try:
        response = requests.get(f"{API_BASE}/claw/agents/me/positions", headers=HEADERS)
        response.raise_for_status()
        return response.json().get("positions", [])
    except Exception as e:
        print(f"[Error] Failed to fetch my positions: {e}")
        return []

def execute_trade(signal):
    # Prepare trade data
    trade_data = {
        "market": signal["market"],
        "action": signal["side"], # buy/sell/short/cover
        "symbol": signal["symbol"],
        "price": signal["entry_price"],
        "quantity": signal["quantity"],
        "content": f"Auto-followed signal {signal['signal_id']} from {signal['agent_name']}",
        "executed_at": "now"
    }
    
    try:
        print(f"[Trade] Attempting to {trade_data['action']} {trade_data['symbol']}...")
        response = requests.post(f"{API_BASE}/signals/realtime", headers=HEADERS, json=trade_data)
        if response.status_code == 200:
            print(f"[Success] Trade executed: {response.json()}")
        else:
            print(f"[Failed] Trade error: {response.text}")
    except Exception as e:
        print(f"[Error] Trade execution failed: {e}")

def run_agent():
    print("--- Autonomous Trading Agent Started ---")
    print(f"Target: {API_BASE}")
    
    seen_signals = set()
    
    while True:
        signals = get_recent_signals()
        my_positions = get_my_positions()
        
        # Simple Logic: If a new signal appears and we don't have this position, follow it.
        # Avoid self-loops (don't follow signals from trader123)
        for sig in signals:
            sig_id = sig["signal_id"]
            if sig_id in seen_signals:
                continue
            
            seen_signals.add(sig_id)
            
            if sig["agent_name"] == "trader123":
                continue
                
            print(f"[Signal] New signal detected: {sig['agent_name']} wants to {sig['side']} {sig['symbol']}")
            
            # Check if we already have this symbol to avoid over-trading (naive check)
            has_position = any(p["symbol"] == sig["symbol"] for p in my_positions)
            
            if sig["side"] == "buy" and not has_position:
                execute_trade(sig)
            elif sig["side"] == "sell" and has_position:
                execute_trade(sig)
        
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    run_agent()
