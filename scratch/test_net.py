import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    try:
        r = requests.get('https://google.com', timeout=5)
        print(f"Google: {r.status_code} OK")
    except Exception as e:
        print(f"Google FAIL: {e}")

    try:
        r = requests.get('https://api.telegram.org', timeout=5)
        print(f"Telegram API: {r.status_code} OK")
    except Exception as e:
        print(f"Telegram API FAIL: {e}")

if __name__ == "__main__":
    test_connection()
