"""
AI-Trader Backend Server - Crypto Sniper Mode
"""

import logging
import os
from logging.handlers import RotatingFileHandler

# Setup logging
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(
            os.path.join(LOG_DIR, "server.log"),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

from cache import get_cache_status
from database import init_database, get_database_status
from routes import create_app
from tasks import (
    background_tasks_enabled_for_api,
    start_background_tasks,
)

# Initialize database
init_database()

# Create app
app = create_app()


# ==================== Startup ====================

@app.on_event("startup")
async def startup_event():
    """Startup event - schedule background tasks."""
    db_status = get_database_status()
    logger.info("Database ready: backend=%s", db_status.get("backend"))
    
    cache_status = get_cache_status()
    logger.info("Cache status: enabled=%s", cache_status.get("enabled"))

    if not background_tasks_enabled_for_api():
        logger.info("Background tasks disabled via environment config.")
        return

    started = start_background_tasks(logger)
    logger.info("Crypto Sniper background tasks started: %s", ", ".join(started.keys()))


# ==================== Run ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
