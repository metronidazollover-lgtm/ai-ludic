---
name: market-intel
description: Provide crypto market context for the Crypto Sniper AI decision loop.
---

# Market Intel (Crypto-Only)

Use this skill to fetch read-only crypto market intelligence. This is intended to provide broader context (macro-crypto relations or large-scale trends) for the sniper bot's internal analysis.

## Available Read-Only Data

- **Crypto Context**: General market sentiment and BTC-led trends.
- **Funding Analysis**: Internal data on Bybit funding rates.
- **Volume Heatmaps**: Identification of unusual trading activity.

## Usage Rule

- **Contextual Only**: Use this data to increase the conviction score of a signal.
- **Non-Execution**: This skill provides information, not execution instructions.
- **Read-Only**: No data is submitted or registered back to this module.
