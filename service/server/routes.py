"""
Routes Module

所有 API 路由定义入口。
"""

import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from config import CORS_ORIGINS
from routes_market import register_market_routes

def create_app() -> FastAPI:
    app = FastAPI(title='AI-Trader API')

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    @app.middleware('http')
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        response.headers['X-Process-Time'] = str(time.time() - start_time)
        return response


    register_market_routes(app)
    # Remaining platform routes have been decommissioned for Crypto Sniper mode.
    return app
