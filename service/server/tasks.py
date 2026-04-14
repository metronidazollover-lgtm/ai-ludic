"""
Tasks Module - Advanced Sniper Control (v7)
"""

import asyncio
import os
import logging
from typing import Dict

logger = logging.getLogger(__name__)

async def refresh_crypto_sniper_snapshots_loop():
    """Background task to refresh Crypto Sniper snapshots."""
    logger.info("[Debug] refresh_crypto_sniper_snapshots_loop started.")
    from market_intel import refresh_crypto_sniper_snapshot, get_crypto_sniper_interval

    await asyncio.sleep(15) # Initial stability delay

    while True:
        try:
            logger.info("[Crypto Sniper] Starting new hunt cycle...")
            result = await asyncio.to_thread(refresh_crypto_sniper_snapshot)
            if result and result.get("symbol"):
                logger.info(f"[Crypto Sniper] Cycle complete. Last found: {result.get('symbol')}")
        except Exception as e:
            logger.error(f"[Crypto Sniper Error] {e}")
            logger.error(f"Sniper loop error: {e}")

        current_interval = get_crypto_sniper_interval()
        await asyncio.sleep(current_interval)

async def market_sync_loop():
    """Background task to sync market metadata (v8.0)."""
    from market_intel import sync_market_metadata
    
    await asyncio.sleep(30) # Wait for initial stability
    
    while True:
        try:
            logger.info("[Syncer] Triggering market metadata update...")
            await asyncio.to_thread(sync_market_metadata)
        except Exception as e:
            logger.error(f"[Syncer Task Error] {e}")
            
        # Sync every 12 hours
        await asyncio.sleep(12 * 3600)

async def telegram_command_polling_loop():
    """Poll for Telegram commands to control the bot dynamically."""
    from notifications import get_telegram_updates, send_telegram_notification
    from market_intel import (
        get_crypto_sniper_interval, set_crypto_sniper_interval,
        get_scout_limit, set_scout_limit,
        get_audit_limit, set_audit_limit,
        get_min_volatility, set_min_volatility,
        get_bot_mode, set_bot_mode
    )
    
    last_update_id = None
    target_chat_id = str(os.getenv("TELEGRAM_CHAT_ID", ""))
    
    main_menu = {
        "keyboard": [
            [{"text": "📊 Status"}, {"text": "🛡️ Mode"}, {"text": "⏱ Interval"}],
            [{"text": "🔍 Scout Lim"}, {"text": "🧠 Audit Lim"}, {"text": "📉 Min Vol"}],
            [{"text": "🏓 Ping"}, {"text": "🔄 Help"}]
        ],
        "resize_keyboard": True,
        "persistent": True
    }
    
    await asyncio.sleep(10)
    logger.info("[Telegram] Started interactive button polling loop (v7).")
    
    awaiting_input = None # States: "interval", "scout", "audit", "vol"
    
    while True:
        try:
            updates = await asyncio.to_thread(get_telegram_updates, offset=last_update_id)
            
            for update in updates:
                last_update_id = update["update_id"] + 1
                message = update.get("message", {})
                chat_id = str(message.get("chat", {}).get("id", ""))
                text = message.get("text", "").strip()
                
                if target_chat_id and chat_id != target_chat_id: continue
                
                # Handle Numeric Inputs
                if text.replace('.','',1).isdigit() and awaiting_input:
                    try:
                        val = float(text)
                        if awaiting_input == "interval":
                            set_crypto_sniper_interval(int(val) * 60)
                            msg = f"✅ <b>Interval:</b> {int(val)} min"
                        elif awaiting_input == "scout":
                            set_scout_limit(int(val))
                            msg = f"✅ <b>Scout Limit:</b> Top {int(val)}"
                        elif awaiting_input == "audit":
                            set_audit_limit(int(val))
                            msg = f"✅ <b>AI Audit Limit:</b> {int(val)} coins"
                        elif awaiting_input == "vol":
                            set_min_volatility(val)
                            msg = f"✅ <b>Min Vol:</b> {val}%"
                        
                        awaiting_input = None
                        send_telegram_notification(msg, reply_markup=main_menu)
                    except Exception as e:
                        send_telegram_notification(f"❌ Error: {e}", reply_markup=main_menu)
                    continue

                # Handle Commands
                awaiting_input = None
                if text in ["/start", "🔄 Help", "/help"]:
                    send_telegram_notification("👋 <b>Sniper V7 Panel</b>\nUse buttons to control the hunt.", reply_markup=main_menu)
                
                elif text == "📊 Status":
                    status_text = (
                        "🤖 <b>Bybit Sniper Status</b>\n"
                        f"• Mode: <b>{get_bot_mode()}</b>\n"
                        f"• Interval: <b>{get_crypto_sniper_interval()//60} min</b>\n"
                        f"• Scout: <b>Top {get_scout_limit()}</b>\n"
                        f"• Audit: <b>{get_audit_limit()} symbols</b>\n"
                        f"• Min Vol: <b>{get_min_volatility()}%</b>\n"
                        "• Status: 🔘 Active"
                    )
                    send_telegram_notification(status_text, reply_markup=main_menu)
                
                elif text == "🛡️ Mode":
                    new_mode = "Aggressive" if get_bot_mode() == "Conservative" else "Conservative"
                    set_bot_mode(new_mode)
                    send_telegram_notification(f"🔄 <b>Mode Switched:</b> {new_mode}", reply_markup=main_menu)
                
                elif text == "⏱ Interval":
                    awaiting_input = "interval"
                    send_telegram_notification("⌛ <b>Enter Interval (min):</b>", reply_markup=main_menu)
                
                elif text == "🔍 Scout Lim":
                    awaiting_input = "scout"
                    send_telegram_notification("⌛ <b>Enter Scout Depth (10-100):</b>", reply_markup=main_menu)
                
                elif text == "🧠 Audit Lim":
                    awaiting_input = "audit"
                    send_telegram_notification("⌛ <b>Enter AI Audit Max (1-10):</b>", reply_markup=main_menu)
                
                elif text == "📉 Min Vol":
                    awaiting_input = "vol"
                    send_telegram_notification("⌛ <b>Enter Min Vol %:</b>", reply_markup=main_menu)
                
                elif text == "🏓 Ping":
                    send_telegram_notification("🏓 Pong (v7)!", reply_markup=main_menu)

        except Exception as e:
            logger.error(f"[Telegram Error] {e}")
            
        await asyncio.sleep(5) 

BACKGROUND_TASK_REGISTRY = {
    "crypto_sniper": refresh_crypto_sniper_snapshots_loop,
    "telegram_polling": telegram_command_polling_loop,
    "market_syncer": market_sync_loop,
}

DEFAULT_BACKGROUND_TASKS = "crypto_sniper,telegram_polling,market_syncer"

def background_tasks_enabled_for_api() -> bool:
    """Helper to check if background loops should run."""
    return os.getenv("ENABLE_BACKGROUND_TASKS", "true").lower() == "true"

def start_background_tasks(logger_arg) -> Dict[str, asyncio.Task]:
    """Start background tasks, filtered by AI_TRADER_BACKGROUND_TASKS env var."""
    enabled_tasks_str = os.getenv("AI_TRADER_BACKGROUND_TASKS", DEFAULT_BACKGROUND_TASKS)
    enabled_tasks = [t.strip() for t in enabled_tasks_str.split(",") if t.strip()]
    
    tasks = {}
    for name, func in BACKGROUND_TASK_REGISTRY.items():
        if name in enabled_tasks:
            logger_arg.info(f"Starting background task: {name}")
            tasks[name] = asyncio.create_task(func())
        else:
            logger_arg.debug(f"Skipping background task: {name} (not in enabled list)")
            
    return tasks
