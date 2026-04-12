---
name: ai-trader
description: Crypto Sniper Bot bootstrap. This file points the model to the correct core workflow.
---

# AI-Trader Bootstrap

The legacy platform features (Registration, Social, Stock Market) have been decommissioned for this bot.

### NEW WORKFLOW:
For all trading analysis and signal generation tasks, please refer EXCLUSIVELY to:
[CRYPTO_SNIPER_CORE.md](file:///c:/Users/favis/Desktop/trade/ai-trader/skills/CRYPTO_SNIPER_CORE.md)

### Decision Logic:
1. **Fetch Data** from Internal Hyperliquid source.
2. **Filter & Analyze** coins based on internal algorithms.
3. **Generate Signal** using the instructions in the core sniper skill.
4. **Send to Telegram** via the background task loop.

No other skills or platform interactions are required.
