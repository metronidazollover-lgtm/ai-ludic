from fastapi import FastAPI, Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timezone
from typing import List

from core.database import get_db
from models.trading import SystemConfig, UserWallet, AIShadowLog
from services.market_intel import market_intel_service

router = APIRouter(prefix="/api")

def utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

@router.get('/health')
async def health_check():
    return {'status': 'ok', 'timestamp': utc_now_iso_z()}

@router.get('/market-intel/overview')
async def market_intel_overview():
    """Returns simplified crypto-only status."""
    return {
        "status": "active",
        "mode": await market_intel_service._get_config("trading_mode", "Conservative"),
        "scout_limit": await market_intel_service._get_config("scout_limit", 50),
        "audit_limit": await market_intel_service._get_config("audit_limit", 5),
        "interval_min": (await market_intel_service._get_config("refresh_interval", 300)) // 60,
        "min_vol": await market_intel_service._get_config("min_volatility_pct", 0.5),
        "connection": "optimized",
        "last_scan": utc_now_iso_z()
    }

@router.get('/config')
async def get_config(db: AsyncSession = Depends(get_db)):
    """Returns all system settings with descriptions."""
    result = await db.execute(select(SystemConfig))
    configs = result.scalars().all()
    return [
        {
            "key": c.key, 
            "value": c.value, 
            "description": c.description, 
            "category": c.category
        } for c in configs
    ]

@router.post('/config')
async def update_config(data: dict, db: AsyncSession = Depends(get_db)):
    """Updates specific system settings."""
    for key, val in data.items():
        await db.execute(
            update(SystemConfig)
            .where(SystemConfig.key == key)
            .values(value=str(val))
        )
    await db.commit()
    return {"status": "success"}

@router.get('/wallet')
async def get_wallet(db: AsyncSession = Depends(get_db)):
    """Returns current virtual balance."""
    result = await db.execute(select(UserWallet).where(UserWallet.id == 1))
    wallet = result.scalar_one_or_none()
    return {"balance": wallet.balance_usd if wallet else 10000.0}

@router.post('/wallet')
async def update_wallet(data: dict, db: AsyncSession = Depends(get_db)):
    """Sets new virtual balance."""
    balance = data.get("balance", 10000.0)
    await db.execute(
        update(UserWallet)
        .where(UserWallet.id == 1)
        .values(balance_usd=float(balance))
    )
    await db.commit()
    return {"status": "success", "new_balance": balance}

@router.get('/signals')
async def get_signals(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Returns history of AI verdicts (Shadow Log)."""
    result = await db.execute(
        select(AIShadowLog)
        .order_by(AIShadowLog.created_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    return [
        {
            "symbol": l.symbol, 
            "verdict": l.verdict, 
            "confidence": l.confidence, 
            "reasoning": l.reasoning, 
            "metrics": l.metrics_json, 
            "time": l.created_at
        } for l in logs
    ]

@router.post('/emulator/run')
async def run_emulator(data: dict = None):
    """Triggers the backtest simulation based on shadow logs."""
    from services.emulator import run_backtest_simulation
    if data is None: data = {}
    limit = data.get("limit", 50)
    # Note: run_backtest_simulation should be updated to be async
    return await run_backtest_simulation(limit=limit)

def register_market_routes(app: FastAPI) -> None:
    app.include_router(router)
