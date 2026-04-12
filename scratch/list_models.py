import requests
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def list_models():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    try:
        response = requests.get(url, timeout=20)
        print(f"Status Code: {response.status_code}")
        data = response.json()
        for m in data.get('models', []):
            print(f"- {m['name']} (supported methods: {m['supportedGenerationMethods']})")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_models()
