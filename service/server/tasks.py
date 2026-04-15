"""
Tasks Module - Async Refactored Control (v11)
"""
import asyncio
import os
import logging
from typing import Dict

from services.market_intel import market_intel_service
from services.state_service import state_service
from core.logging_config import logger as struct_logger

async def refresh_crypto_sniper_snapshots_loop():
    """Background task to refresh Crypto Sniper snapshots (Async)."""
    struct_logger.info("sniper_loop_started")

    await asyncio.sleep(15) 

    while True:
        try:
            struct_logger.info("sniper_cycle_start")
            
            # 1. Scout candidates
            candidates = await market_intel_service.scout_candidates()
            
            for symbol in candidates:
                analysis = await market_intel_service.build_analysis(symbol)
                if analysis and analysis.get("verdict"):
                    struct_logger.info("signal_generated", symbol=symbol, verdict=analysis["verdict"].signal)
                    # Note: Notification logic could be added here
            
            struct_logger.info("sniper_cycle_complete", found=len(candidates))
        except Exception as e:
            struct_logger.error("sniper_loop_error", error=str(e))

        interval = await market_intel_service._get_config("refresh_interval", 300)
        await asyncio.sleep(interval)

async def market_sync_loop():
    """Background task to sync market metadata (Async)."""
    await asyncio.sleep(30)
    
    while True:
        try:
            struct_logger.info("market_sync_trigger")
            await market_intel_service.sync_market_metadata()
        except Exception as e:
            struct_logger.error("market_sync_error", error=str(e))
            
        await asyncio.sleep(12 * 3600)

async def telegram_command_polling_loop():
    """Poll for Telegram commands (Placeholder for now)."""
    # This should be refactored to a dedicated TelegramService
    while True:
        await asyncio.sleep(60)

BACKGROUND_TASK_REGISTRY = {
    "crypto_sniper": refresh_crypto_sniper_snapshots_loop,
    "telegram_polling": telegram_command_polling_loop,
    "market_syncer": market_sync_loop,
}

DEFAULT_BACKGROUND_TASKS = "crypto_sniper,telegram_polling,market_syncer"

def start_background_tasks(logger_arg) -> Dict[str, asyncio.Task]:
    enabled_tasks_str = os.getenv("AI_TRADER_BACKGROUND_TASKS", DEFAULT_BACKGROUND_TASKS)
    enabled_tasks = [t.strip() for t in enabled_tasks_str.split(",") if t.strip()]
    
    tasks = {}
    for name, func in BACKGROUND_TASK_REGISTRY.items():
        if name in enabled_tasks:
            logger_arg.info(f"Starting background task: {name}")
            tasks[name] = asyncio.create_task(func())
            
    return tasks
