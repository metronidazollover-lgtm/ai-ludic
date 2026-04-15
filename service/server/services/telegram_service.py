import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from notifications import get_telegram_updates, send_telegram_notification, TELEGRAM_CHAT_ID
from services.market_intel import market_intel_service
from services.state_service import state_service

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self):
        self.last_update_id = 0
        self.is_running = False

    async def polling_loop(self):
        """Poll for Telegram commands and process them (v11 Async)."""
        self.is_running = True
        logger.info("telegram_polling_started", chat_id=TELEGRAM_CHAT_ID)
        
        while self.is_running:
            try:
                # get_telegram_updates is a blocking requests call in notifications.py
                # We should eventually make it async, but for now, run in executor or just keep as is
                # since it has a timeout that prevents it from hanging too long.
                updates = get_telegram_updates(offset=self.last_update_id + 1)
                
                for update in updates:
                    self.last_update_id = update.get("update_id", self.last_update_id)
                    
                    message = update.get("message")
                    if not message:
                        continue
                        
                    chat_id = str(message.get("chat", {}).get("id"))
                    text = message.get("text", "").strip()
                    user = message.get("from", {}).get("username", "Unknown")
                    
                    # Security check: only respond to the configured chat ID
                    if TELEGRAM_CHAT_ID and chat_id != str(TELEGRAM_CHAT_ID):
                        logger.warning("unauthorized_telegram_message", chat_id=chat_id, user=user, text=text)
                        continue
                        
                    logger.info("telegram_command_received", user=user, text=text)
                    await self.handle_command(text)
                    
            except Exception as e:
                logger.error("telegram_polling_error", error=str(e))
                
            await asyncio.sleep(3) # Poll every 3 seconds

    async def handle_command(self, text: str):
        if not text.startswith("/"):
            return # Ignore non-commands
            
        parts = text.lower().split()
        command = parts[0]
        
        if command == "/start" or command == "/help":
            await self.cmd_help()
        elif command == "/ping":
            send_telegram_notification("🏓 <b>Pong!</b> System is responsive.")
        elif command == "/status":
            await self.cmd_status()
        elif command == "/scan":
            await self.cmd_scan()
        elif command == "/cooldowns":
            await self.cmd_cooldowns()
        else:
            # send_telegram_notification(f"❓ Unknown command: {command}. Try /help")
            pass

    async def cmd_help(self):
        help_text = (
            "🤖 <b>AI-Trader Bot Help (v11)</b>\n\n"
            "Available commands:\n"
            "• /status - Current system status & config\n"
            "• /scan - Trigger manual market scan\n"
            "• /cooldowns - List assets in cooldown\n"
            "• /ping - Check bot connectivity\n"
            "• /help - Show this message"
        )
        send_telegram_notification(help_text)

    async def cmd_status(self):
        # Read various configs
        mode = await market_intel_service._get_config("trading_mode", "Conservative")
        interval = await market_intel_service._get_config("refresh_interval", 300)
        scout_limit = await market_intel_service._get_config("scout_limit", 50)
        min_vol = await market_intel_service._get_config("min_volatility_pct", 0.5)
        
        status_text = (
            "📊 <b>System Status</b>\n\n"
            f"✅ <b>Mode:</b> <code>{mode}</code>\n"
            f"🕒 <b>Interval:</b> <code>{interval//60} min</code>\n"
            f"🕵️ <b>Scout Limit:</b> <code>{scout_limit}</code>\n"
            f"📈 <b>Min Vol:</b> <code>{min_vol}%</code>\n"
            f"🔗 <b>Environment:</b> <code>development</code>"
        )
        send_telegram_notification(status_text)

    async def cmd_scan(self):
        send_telegram_notification("🔍 <i>Starting manual market scan...</i>")
        try:
            candidates = await market_intel_service.scout_candidates()
            if not candidates:
                send_telegram_notification("📭 No immediate candidates passed technical filters.")
                return

            found_any = False
            for symbol in candidates:
                analysis = await market_intel_service.build_analysis(symbol)
                if analysis and analysis.get("verdict"):
                    v = analysis["verdict"]
                    if v.signal != "skip":
                        found_any = True
                        # The notification for the signal should be handled by the caller or helper
                        # For now, let's format a brief alert here if build_analysis doesn't send it.
                        self._send_signal_alert(symbol, v)
            
            if not found_any:
                send_telegram_notification(f"🗃 Scanned {len(candidates)} candidates. All were 'skip' by AI.")
        except Exception as e:
            logger.error("manual_scan_failed", error=str(e))
            send_telegram_notification(f"❌ Scan failed: {str(e)}")

    async def cmd_cooldowns(self):
        cooldowns = state_service.get("cooldowns", {})
        now = datetime.now(timezone.utc).timestamp()
        
        active = []
        for s, exp in cooldowns.items():
            if exp > now:
                rem = int((exp - now) / 60)
                active.append(f"• {s}: {rem} min left")
        
        if not active:
            send_telegram_notification("❄️ No assets currently in cooldown.")
        else:
            send_telegram_notification("❄️ <b>Active Cooldowns:</b>\n" + "\n".join(active))

    def _send_signal_alert(self, symbol: str, verdict: Any):
        # verdict is an AIVerdict object
        labels_str = " ".join([f"<code>[{l}]</code>" for l in (verdict.labels or [])])
        
        content = (
            f"🎯 <b>{symbol} SIGNAL BRIEFING</b>\n"
            f"{labels_str}\n\n"
            f"📊 <b>Confidence:</b> <code>{verdict.confidence}%</code>\n\n"
            f"<blockquote>{verdict.summary}</blockquote>\n\n"
            f"—— <b>STRATEGY</b> ——\n"
            f"⚡ <b>Action:</b> <code>{verdict.signal.upper()}</code>\n"
            f"🚀 <b>Entry:</b> <code>${verdict.entry}</code>\n"
            f"🛡️ <b>Exit/TP:</b> <code>${verdict.exit}</code>\n"
            f"🛑 <b>Stop Loss:</b> <code>${verdict.stop_loss}</code>\n\n"
            f"<i>Triggered manually via Telegram</i>"
        )
        send_telegram_notification(content)

telegram_service = TelegramService()
