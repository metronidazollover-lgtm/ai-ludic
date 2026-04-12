---
name: ai-trader
description: Crypto Sniper Bot Core Skill. Focus on coin analysis and Telegram signal generation.
---

# Crypto Sniper Bot Core

This is the primary instruction set for the Crypto Sniper Bot. The bot operates as a 24/7 crypto-native engine focused on identifying high-conviction trading opportunities on Hyperliquid and delivering them to Telegram.

## Core Workflow

1. **Market Data Ingestion**:
   - The bot fetches the latest price, volume, and funding data for all active assets on Hyperliquid.
   - It filters for assets with significant 24h volume and price action.

2. **AI Analysis & Filtering**:
   - The bot evaluates candidates based on technical indicators (Trend, RSI, Volume Spikes).
   - Only "best" candidates are passed to the AI model for final validation.

3. **Signal Generation**:
   - The model receives filtered coin data and determines if a high-conviction trade exists.
   - **Output**: If conviction is high (>=80%), the model generates a structured signal for the Telegram bot.

## Signal Formatting Rules (Telegram)

When the model generates a signal, it MUST follow this structure:

**[SYMBOL] Signal Briefing**
- **Action**: BUY/SELL (Long/Short)
- **Conviction**: [XX]%
- **Current Price**: $[Price]
- **Reasoning**: Concise analysis of why this trade is selected (e.g., breakout, funding rate anomaly, volume surge).
- **Target/Stop**: Estimated levels based on current volatility.

## Decision Rules

- **No Social Participation**: The agent does not post to strategies, discussions, or replies.
- **No Token Required**: Direct server-to-telegram communication.
- **Crypto-Only**: Focus strictly on Hyperliquid perps and spot markets.

## Prohibited Actions

- DO NOT attempt to register or login.
- DO NOT use Bearer tokens or API keys for platform interactions.
- DO NOT generate macro or us-stock analysis.
