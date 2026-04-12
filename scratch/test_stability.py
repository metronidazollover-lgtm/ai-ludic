import requests
import json
import time
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

def test_model(model_name):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": "Say 'OK' if you can read this."}]}]
    }
    try:
        start = time.time()
        resp = requests.post(url, json=payload, timeout=10)
        end = time.time()
        print(f"Model: {model_name} | Status: {resp.status_code} | Time: {end-start:.2f}s")
        if resp.status_code != 200:
            print(f"  Error: {resp.text}")
        return resp.status_code == 200
    except Exception as e:
        print(f"Model: {model_name} | Error: {e}")
        return False

models_to_test = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-flash-latest",
    "gemini-2.0-flash-exp",
    "gemini-pro"
]

print(f"Testing models with API Key: {API_KEY[:5]}...{API_KEY[-5:]}")
for m in models_to_test:
    test_model(m)
    time.sleep(1)
