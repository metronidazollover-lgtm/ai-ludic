from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Database
    DATABASE_URL: str = ""
    DB_PATH: str = "service/server/data/clawtrader.db"

    # AI Keys
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""

    # Exchange
    BYBIT_API_URL: str = "https://api.bybit.com"

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # App Settings
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    ENABLE_BACKGROUND_TASKS: bool = True
    AI_TRADER_BACKGROUND_TASKS: str = "crypto_sniper,telegram_polling,market_syncer"

    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL:
            # Handle Postgres async if needed
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        
        # Default to aiosqlite
        # Resolve path relative to PROJECT ROOT (which is parent of service/)
        # Current file is in service/server/core/config.py
        current_dir = os.path.dirname(os.path.abspath(__file__)) # service/server/core
        server_dir = os.path.dirname(current_dir) # service/server
        db_path = os.path.join(server_dir, "data", "clawtrader.db")
        
        return f"sqlite+aiosqlite:///{db_path}"

settings = Settings()
