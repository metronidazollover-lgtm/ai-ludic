import sys
import os

# Add service/server to path
sys.path.append(os.path.join(os.getcwd(), "service", "server"))

from notifications import send_telegram_notification

print("Sending test signal to Telegram...")
test_msg = "Test message from Crypto Sniper bot. No formatting."

success = send_telegram_notification(test_msg)
if success:
    print("[SUCCESS] Test message sent!")
else:
    print("[FAILED] Check logs/credentials.")
