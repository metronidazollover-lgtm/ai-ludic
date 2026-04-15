
import os
import requests
import dotenv

dotenv.load_dotenv("c:/Users/favis/Desktop/trade/ai-trader/.env")

token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

print(f"Token: {token[:10]}...")
print(f"Chat ID: {chat_id}")

def test_connection():
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        res = requests.get(url, timeout=10)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_connection()
