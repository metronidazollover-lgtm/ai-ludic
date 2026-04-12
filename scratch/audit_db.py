import sqlite3
import json
import os
import sys

# Set console to UTF-8
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

# Updated to use the correct volume mapping directory from docker-compose
db_path = "c:\\Users\\favis\\Desktop\\trade\\ai-trader\\ai_trader_data\\clawtrader.db"

def audit():
    if not os.path.exists(db_path):
        print(u"Error: DB not found at " + db_path)
        return

    print(u"Auditing database at: " + db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print(u"\n--- LAST 5 CRYPTO SNIPER SNAPSHOTS ---")
    cursor.execute("SELECT symbol, signal, created_at, analysis_json FROM stock_analysis_snapshots ORDER BY created_at DESC LIMIT 5")
    rows = cursor.fetchall()
    for row in rows:
        analysis = json.loads(row['analysis_json'] or '{}')
        model = analysis.get('meta_model', 'N/A')
        print(u"[{0}] {1} - {2} | Model: {3}".format(row['created_at'], row['symbol'], row['signal'], model))

    print(u"\n--- LAST 5 MARKETPLACE SIGNALS (AGENT 4) ---")
    cursor.execute("SELECT title, content, created_at FROM signals WHERE agent_id = 4 ORDER BY created_at DESC LIMIT 5")
    rows = cursor.fetchall()
    for row in rows:
        print(u"[{0}] {1}".format(row['created_at'], row['title']))
        content = row['content']
        has_model = u"AI Model:" in content
        print(u"  Content Meta: {0}".format(u"[MODEL FOUND]" if has_model else u"[NO MODEL BRANDING]"))
        preview = content[:100].replace('\n', ' ')
        # Use repr to avoid encoding issues with weird chars in terminal
        print(u"  Snippet: " + preview + "...")

    conn.close()

if __name__ == "__main__":
    audit()
