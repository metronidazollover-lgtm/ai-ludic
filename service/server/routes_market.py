from fastapi import FastAPI
from market_intel import get_market_intel_overview
from datetime import datetime, timezone

def utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def register_market_routes(app: FastAPI) -> None:
    @app.get('/health')
    async def health_check():
        return {'status': 'ok', 'timestamp': utc_now_iso_z()}

    @app.get('/api/market-intel/overview')
    async def market_intel_overview():
        """Returns simplified crypto-only status."""
        return get_market_intel_overview()

    # --- v10.0 Web UI API ---

    @app.get('/api/config')
    async def get_config():
        """Returns all system settings with descriptions."""
        from database import get_db_connection
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value, description, category FROM system_config")
            rows = cursor.fetchall()
            return [{"key": r[0], "value": r[1], "description": r[2], "category": r[3]} for r in rows]
        finally: conn.close()

    @app.post('/api/config')
    async def update_config(data: dict):
        """Updates specific system settings."""
        from database import get_db_connection
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            for key, val in data.items():
                cursor.execute("UPDATE system_config SET value=? WHERE key=?", (str(val), key))
            conn.commit()
            return {"status": "success"}
        finally: conn.close()

    @app.get('/api/wallet')
    async def get_wallet():
        """Returns current virtual balance."""
        from database import get_db_connection
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT balance_usd FROM user_wallet WHERE id=1")
            row = cursor.fetchone()
            return {"balance": row[0] if row else 10000.0}
        finally: conn.close()

    @app.post('/api/wallet')
    async def update_wallet(data: dict):
        """Sets new virtual balance."""
        from database import get_db_connection
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            balance = data.get("balance", 10000.0)
            cursor.execute("UPDATE user_wallet SET balance_usd=? WHERE id=1", (float(balance),))
            conn.commit()
            return {"status": "success", "new_balance": balance}
        finally: conn.close()

    @app.get('/api/signals')
    async def get_signals(limit: int = 50):
        """Returns history of AI verdicts (Shadow Log)."""
        from database import get_db_connection
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT symbol, verdict, confidence, reasoning, metrics_json, created_at 
                FROM ai_shadow_log ORDER BY created_at DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [{"symbol": r[0], "verdict": r[1], "confidence": r[2], "reasoning": r[3], "metrics": r[4], "time": r[5]} for r in rows]
        finally: conn.close()

    @app.post('/api/emulator/run')
    async def run_emulator(data: dict = None):
        """Triggers the backtest simulation based on shadow logs."""
        from services.emulator import run_backtest_simulation
        if data is None: data = {}
        limit = data.get("limit", 50)
        return run_backtest_simulation(limit=limit)

    # Note: Legacy social/stock routes have been removed.
    # The server now operates as a headless analysis engine.
