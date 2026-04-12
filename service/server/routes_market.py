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

    # Note: Legacy social/stock routes have been removed.
    # The server now operates as a headless analysis engine.
