---
name: ai-trader
description: Crypto Sniper Bot Core Skill. Focus on coin analysis and Telegram signal generation.
---

# Crypto Sniper Bot Core

This is the primary instruction set for the Crypto Sniper Bot. The bot operates as a 24/7 crypto-native engine focused on identifying high-conviction trading opportunities on Bybit and delivering them to Telegram.

## Core Workflow

1. **Market Data Ingestion**:
   - The bot fetches the latest price, volume, and funding data for all active assets on Bybit.
   - It filters for assets with significant 24h volume and price action.

2. **AI Analysis & Filtering**:
   - The bot evaluates candidates based on technical indicators (Trend, RSI, Volume Spikes).
   - Only "best" candidates are passed to the AI model for final validation.

3. **Signal Generation**:
   - The model receives filtered coin data and determines if a high-conviction trade exists.
   - **Output**: If conviction is high (>=80%), the model generates a structured signal for the Telegram bot.

## Signal Formatting Rules (Telegram)

When the model generates a signal, it MUST follow this JSON structure in its response:
- **labels**: Array of tags like `[BREAKOUT]`, `[RIDING_THE_WAVE]`, `[WHALE_MOVE]`, `[QUICK_SCALP]`.
- **confidence**: High conviction >= 80% only.
- **RRR Discipline**: Target Profit MUST be at least 2.0x the distance of Stop Loss.

## Decision Rules: Risk Management

1. **RRR 1:2+**: Never propose a trade where the risk (entry to stop) is greater than half the reward (entry to target).
2. **Stop Placement**: Always place stops behind the most recent H1/H4 structure (lows for longs, highs for shorts).
3. **Condition Audit**: 
    - Use RSI to avoid entries on extreme exhaustion (RSI > 85 or < 15).
    - Use Market Snapshot to adjust conviction (Solo runners vs Sector wave).

## Prohibited Actions
...

- DO NOT attempt to register or login.
- DO NOT use Bearer tokens or API keys for platform interactions.
- DO NOT generate macro or us-stock analysis.
