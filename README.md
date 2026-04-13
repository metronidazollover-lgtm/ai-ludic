# Crypto Sniper: Autonomous AI Trading Agent

Autonomous trading engine specialized in **Bybit** markets. The system scouts for high-volatility opportunities, analyzes them using AI (Gemini/Groq), and executes signals via Telegram.

## 🚀 Quick Start

1. **Configure Environment**: Copy `.env.example` to `.env` and fill in your API keys (Bybit, Gemini/Groq, Telegram).
2. **Initialize Database**: Run the server once to initialize the streamlined schema.
3. **Start the Bot**:
   ```bash
   cd service/server
   python main.py
   ```

## 🧠 Core Architecture

- **Scout Loop**: Monitors Top 50 Bybit pairs by volume and volatility.
- **AI Fallback Chain**: 
  1. Primary: Gemini Pro/Flash
  2. Fallback: Groq (Llama 3.3)
- **Execution**: Signal delivery to Telegram with interactive control panel.

## 📂 Project Structure

- `service/server/`: Backend engine and background tasks.
- `skills/`: AI system prompts and platform operational guides.
- `scratch/`: Verification and diagnostic scripts.

---
*Focus: 100% Crypto-Only. High Conviction. Agent-Native.*
