import requests
import html
from typing import Optional
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def send_telegram_notification(text: str, reply_markup: Optional[dict] = None):
    """
    Send a message to a Telegram chat using the bot API.
    Supports HTML and optional reply_markup (keyboards).
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] Skip: Missing Bot Token or Chat ID")
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # Try sending with HTML formatting first
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML" 
    }
    
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        
        # If HTML fails (e.g. bad tags), try plain text as fallback
        if response.status_code == 400 and "can't parse entities" in response.text:
            print("[Telegram] HTML parsing failed, sending as plain text...")
            # Simple escape: strip <b> tags and hope for the best, or just send plain
            plain_text = text.replace("<b>", "").replace("</b>", "")
            payload["text"] = plain_text
            payload.pop("parse_mode", None)
            response = requests.post(url, json=payload, timeout=10)
            
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"[Telegram Error] {e}")
        return False

def get_telegram_updates(offset=None):
    """
    Poll for new messages from the Telegram bot.
    """
    if not TELEGRAM_BOT_TOKEN:
        return []
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {"timeout": 10, "offset": offset}
    
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json().get("result", [])
    except Exception as e:
        print(f"[Telegram Polling Error] {e}")
        return []
