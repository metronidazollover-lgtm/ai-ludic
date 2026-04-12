import requests
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def test_gemini():
    # Trying 1.5-flash which is widely available
    model = "gemini-1.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": "Hello, are you there? Respond with 'Yes' only."}]}],
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_gemini()
