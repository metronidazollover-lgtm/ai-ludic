"""
Telegram Notification Service
"""

import os
import requests
import json
from typing import Optional, List, Dict, Any

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

def send_telegram_notification(message: str, reply_markup: Optional[Dict[str, Any]] = None) -> bool:
    """Send a notification to the configured Telegram chat."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] Missing token or chat ID. Skipping notification.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"[Telegram Error] Failed to send message: {e}")
        return False

def get_telegram_updates(offset: Optional[int] = None) -> List[Dict[str, Any]]:
    """Poll for new updates from Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        return []

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset

    try:
        response = requests.get(url, params=params, timeout=35)
        response.raise_for_status()
        data = response.json()
        return data.get("result", [])
    except Exception as e:
        print(f"[Telegram Error] Failed to get updates: {e}")
        return []
