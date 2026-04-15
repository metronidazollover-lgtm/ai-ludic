"""
AI-Trader Backend Server - Modern Refactored Mode
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.config import settings
from core.database import engine, init_db
from core.http import http_manager
from core.logging_config import setup_logging, logger
from services.state_service import state_service
# from routes import register_routes # Assume we refactor routes to a simpler registration

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger.info("server_starting", env=settings.ENVIRONMENT)
    
    # Initialize DB (if needed, though Alembic handles it)
    # await init_db()
    
    # Start background tasks via task manager (to be implemented)
    from tasks import start_background_tasks
    bg_tasks = start_background_tasks(logger)
    
    yield
    
    # Shutdown
    logger.info("server_shutting_down")
    await http_manager.close_client()
    state_service.save_state()
    # Cancel background tasks
    for task in bg_tasks.values():
        task.cancel()

def create_app() -> FastAPI:
    app = FastAPI(
        title="Crypto Sniper API",
        version="11.0.0",
        lifespan=lifespan
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Routes
    from routes_market import register_market_routes
    register_market_routes(app)
    # register_routes(app)

    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
