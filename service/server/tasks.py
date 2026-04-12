"""
Tasks Module

后台任务管理
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}

def _env_int(name: str, default: int, minimum: Optional[int] = None) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except Exception:
        value = default
    if minimum is not None:
        value = max(minimum, value)
    return value

async def refresh_crypto_sniper_snapshots_loop():
    """Background task to refresh Crypto Sniper snapshots."""
    from market_intel import refresh_crypto_sniper_snapshot

    await asyncio.sleep(15)

    while True:
        try:
            print("[Crypto Sniper] Scouting for opportunities...")
            result = await asyncio.to_thread(refresh_crypto_sniper_snapshot)
            if "symbol" in result:
                print(
                    "[Crypto Sniper] Found opportunity: "
                    f"symbol={result.get('symbol')} "
                    f"signal={result.get('signal')}"
                )
            else:
                print(f"[Crypto Sniper] No clear opportunity: {result.get('message')}")
        except Exception as e:
            print(f"[Crypto Sniper Error] {e}")

        from market_intel import get_crypto_sniper_interval
        current_interval = get_crypto_sniper_interval()
        print(f"[Crypto Sniper] Task complete. Sleeping {current_interval}s until next hunt...")
        await asyncio.sleep(current_interval)

async def telegram_command_polling_loop():
    """Poll for Telegram commands to control the bot dynamically."""
    from notifications import get_telegram_updates, send_telegram_notification
    from market_intel import get_crypto_sniper_interval, set_crypto_sniper_interval
    import os
    
    last_update_id = None
    target_chat_id = str(os.getenv("TELEGRAM_CHAT_ID", ""))
    
    main_menu = {
        "keyboard": [
            [{"text": "📊 Status"}, {"text": "⏱ Set Interval"}],
            [{"text": "🏓 Ping"}, {"text": "🔄 Help"}]
        ],
        "resize_keyboard": True,
        "persistent": True
    }
    
    await asyncio.sleep(10)
    print("[Telegram] Started interactive button polling loop.")
    
    awaiting_interval = False
    
    while True:
        try:
            updates = await asyncio.to_thread(get_telegram_updates, offset=last_update_id)
            
            for update in updates:
                last_update_id = update["update_id"] + 1
                
                if "callback_query" in update:
                    cb = update["callback_query"]
                    chat_id = str(cb.get("message", {}).get("chat", {}).get("id", ""))
                    data = cb.get("data", "")
                    if target_chat_id and chat_id != target_chat_id: continue
                    
                    if data.startswith("set_int_"):
                        new_seconds = int(data.split("_")[-1])
                        set_crypto_sniper_interval(new_seconds)
                        awaiting_interval = False
                        send_telegram_notification(
                            f"✅ <b>Interval Updated</b>\nFrequency: {new_seconds//60} min ({new_seconds}s)",
                            reply_markup=main_menu
                        )
                    continue

                message = update.get("message", {})
                chat_id = str(message.get("chat", {}).get("id", ""))
                text = message.get("text", "").strip()
                
                if target_chat_id and chat_id != target_chat_id:
                    continue
                
                if text.isdigit() and awaiting_interval:
                    mins = int(text)
                    if 0 < mins <= 1440: 
                        secs = mins * 60
                        set_crypto_sniper_interval(secs)
                        awaiting_interval = False
                        send_telegram_notification(
                            f"🚀 <b>Configuration Updated!</b>\nNew Sniper frequency: <b>{mins} min</b>.",
                            reply_markup=main_menu
                        )
                    else:
                        send_telegram_notification("❌ Please enter 1 to 1440 minutes.", reply_markup=main_menu)
                    continue
                
                awaiting_interval = False

                if text == "/start" or text == "🔄 Help" or text == "/help" or not text:
                    send_telegram_notification(
                        "👋 <b>Crypto Sniper Control Panel</b>\nUse the buttons below to manage your AI agent.",
                        reply_markup=main_menu
                    )
                elif text == "📊 Status" or text == "/status":
                    curr = get_crypto_sniper_interval()
                    from market_intel import GEMINI_API_KEY, GROQ_API_KEY
                    ai_status = "Active" if (GEMINI_API_KEY or GROQ_API_KEY) else "Inactive"
                    status_msg = (
                        "🤖 <b>Bot Status</b>\n"
                        f"• Sniper Interval: <b>{curr//60} min</b> ({curr}s)\n"
                        f"• AI Capability: {ai_status}\n"
                        "• Status: 🟢 Running"
                    )
                    send_telegram_notification(status_msg, reply_markup=main_menu)
                elif text == "⏱ Set Interval":
                    awaiting_interval = True
                    send_telegram_notification(
                        "⌛ <b>Awaiting Interval Input</b>\nPlease type the number of <b>minutes</b> and send it now.",
                        reply_markup=main_menu
                    )
                elif text == "🏓 Ping" or text == "/ping":
                    send_telegram_notification("🏓 Pong! Your AI is responsive.", reply_markup=main_menu)

        except Exception as e:
            print(f"[Telegram Loop Error] {e}")
            
        await asyncio.sleep(5) 

DEFAULT_BACKGROUND_TASKS = "crypto_sniper,telegram_polling"

BACKGROUND_TASK_REGISTRY = {
    "crypto_sniper": refresh_crypto_sniper_snapshots_loop,
    "telegram_polling": telegram_command_polling_loop,
    "prices": None,          # Ignored legacy task
    "profit_history": None,  # Ignored legacy task
}

def _prune_profit_history():
    """Legacy stub for pruning profit history."""
    pass

def background_tasks_enabled_for_api() -> bool:
    return _env_bool("ENABLE_API_BACKGROUND_TASKS", True)

def start_background_tasks(logger) -> Dict[str, asyncio.Task]:
    """Start enabled background tasks based on AI_TRADER_BACKGROUND_TASKS environment variable."""
    requested_raw = os.getenv("AI_TRADER_BACKGROUND_TASKS", DEFAULT_BACKGROUND_TASKS)
    requested = {t.strip().lower() for t in requested_raw.split(",") if t.strip()}
    
    tasks = {}
    for name, func in BACKGROUND_TASK_REGISTRY.items():
        if name in requested and func is not None:
            logger.info(f"Starting background task: {name}")
            tasks[name] = asyncio.create_task(func())
    return tasks
