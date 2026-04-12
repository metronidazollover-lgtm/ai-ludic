import sys
import os
from pathlib import Path

# Add service/server to path
sys.path.append(str(Path(__file__).parent.parent / "service" / "server"))

import market_intel
from dotenv import load_dotenv

load_dotenv()

def test_sniper():
    print("Testing Crypto Sniper Analysis with Skills context...")
    try:
        # We simulate the analysis for BTC
        # This will call Gemini with the new logic
        analysis = market_intel._build_sniper_analysis("BTC")
        print("\n--- Analysis Result ---")
        import json
        print(json.dumps(analysis, indent=2))
        
        if analysis["summary"] == "AI generation failed, using technical fallback.":
            print("\n[FAIL] AI generation still failing.")
        else:
            print("\n[SUCCESS] AI generated a detailed analysis!")
            
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sniper()
