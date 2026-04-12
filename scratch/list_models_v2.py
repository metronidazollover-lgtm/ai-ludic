import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

def list_models():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    try:
        resp = requests.get(url)
        data = resp.json()
        print(f"Total models: {len(data.get('models', []))}")
        for m in data.get('models', []):
            name = m.get('name')
            methods = m.get('supportedGenerationMethods', [])
            if 'generateContent' in methods:
                 print(f"- {name} (GenContent OK)")
    except Exception as e:
        print(f"Error: {e}")

list_models()
