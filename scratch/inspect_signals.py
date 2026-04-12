import sqlite3
import json
import os

db_path = r'c:\Users\favis\Desktop\trade\ai-trader\ai_trader_data\clawtrader.db'

def inspect_signals():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check if signals table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='signals'")
    if not cursor.fetchone():
        print("Table 'signals' does not exist")
        return

    # Get latest signals
    cursor.execute("SELECT * FROM signals ORDER BY timestamp DESC LIMIT 5")
    rows = cursor.fetchall()
    
    signals = []
    for row in rows:
        signals.append(dict(row))
    
    with open('signals_report.json', 'w', encoding='utf-8') as f:
        json.dump(signals, f, ensure_ascii=False, indent=2)
    
    print(f"Successfully exported {len(signals)} signals to signals_report.json")
    conn.close()

if __name__ == "__main__":
    inspect_signals()
