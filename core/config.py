"""
Ludic2 Configuration Module
Loads settings from .env and provides typed access to all config values.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    # Try .env.example for reference
    _example = Path(__file__).parent / ".env.example"
    if _example.exists():
        load_dotenv(_example)


# === Bybit API ===
BYBIT_API_KEY: str = os.getenv("BYBIT_API_KEY", "")
BYBIT_API_SECRET: str = os.getenv("BYBIT_API_SECRET", "")
BYBIT_TESTNET: bool = os.getenv("BYBIT_TESTNET", "false").lower() == "true"
BYBIT_DEMO: bool = os.getenv("BYBIT_DEMO", "true").lower() == "true"
DEFAULT_LEVERAGE: int = int(os.getenv("DEFAULT_LEVERAGE", "10"))

# === Telegram ===
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_API_URL: str | None = os.getenv("TELEGRAM_API_URL")

# === Risk Management ===
MAX_POSITION_PCT: float = float(os.getenv("MAX_POSITION_PCT", "0.05"))
DAILY_STOP_LOSS_PCT: float = float(os.getenv("DAILY_STOP_LOSS_PCT", "0.20"))
DAILY_TAKE_PROFIT_PCT: float = float(os.getenv("DAILY_TAKE_PROFIT_PCT", "0.40"))
MAX_OPEN_POSITIONS: int = int(os.getenv("MAX_OPEN_POSITIONS", "5"))
KELLY_MULTIPLIER: float = float(os.getenv("KELLY_MULTIPLIER", "0.25"))

# === Market Scanner ===
SCAN_INTERVAL_SECONDS: int = int(os.getenv("SCAN_INTERVAL_SECONDS", "60"))
MIN_VOLUME_USDT: float = float(os.getenv("MIN_VOLUME_USDT", "1000000"))
TOP_PAIRS_COUNT: int = int(os.getenv("TOP_PAIRS_COUNT", "30"))

# === Timeframes ===
SCALPING_TIMEFRAME: str = "5m"
SWING_TIMEFRAME: str = "4h"
MACRO_TIMEFRAME: str = "1d"

# === Indicator Defaults ===
EMA_FAST: int = 9
EMA_MID: int = 21
EMA_SLOW: int = 50
EMA_MACRO: int = 200
RSI_PERIOD: int = 14
MACD_FAST: int = 12
MACD_SLOW: int = 26
MACD_SIGNAL: int = 9
ATR_PERIOD: int = 14
VOLUME_SMA_PERIOD: int = 20

# === Signal Thresholds ===
SIGNAL_MIN_SCORE: int = 3          # Minimum factors for MEDIUM signal
SIGNAL_HIGH_SCORE: int = 4         # Minimum factors for HIGH signal
RSI_OVERSOLD: int = 30
RSI_OVERBOUGHT: int = 70
OBI_THRESHOLD: float = 0.3        # Order Book Imbalance threshold
NOISE_WICK_THRESHOLD: float = 0.40 # Max avg wick ratio (from OTC-Screener v5.0)
NOISE_HOSTILE_WICK: float = 0.50   # Anti-sweep threshold (from OTC-Screener v5.0)
ATR_ANOMALY_MULTIPLIER: float = 2.5

# === Paths ===
PROJECT_ROOT: Path = Path(__file__).parent.parent  # Ludic1/
BOT_ROOT: Path = Path(__file__).parent              # Ludic1/ludic2/
DB_PATH: Path = BOT_ROOT / "storage" / "trades.db"
LOG_DIR: Path = PROJECT_ROOT / "logs"


def validate() -> list[str]:
    """Check that essential config values are set. Returns list of errors."""
    errors = []
    if not BYBIT_API_KEY or BYBIT_API_KEY == "your_api_key_here":
        errors.append("BYBIT_API_KEY not configured in .env")
    if not BYBIT_API_SECRET or BYBIT_API_SECRET == "your_api_secret_here":
        errors.append("BYBIT_API_SECRET not configured in .env")
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        errors.append("TELEGRAM_BOT_TOKEN not configured in .env")
    if not TELEGRAM_CHAT_ID or TELEGRAM_CHAT_ID == "your_chat_id_here":
        errors.append("TELEGRAM_CHAT_ID not configured in .env")
    return errors
