"""
Database Module

数据库初始化、连接和管理
"""

from __future__ import annotations

import os
import re
import sqlite3
import time
from typing import Any, Iterable, Optional, Sequence

from config import DATABASE_URL

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None
    dict_row = None

_BASE_DIR = os.path.dirname(__file__)
_DEFAULT_SQLITE_DB_PATH = os.path.join(_BASE_DIR, "data", "clawtrader.db")
_SQLITE_DB_PATH = os.getenv("DB_PATH", _DEFAULT_SQLITE_DB_PATH)

def using_postgres() -> bool:
    return bool(DATABASE_URL)

def get_database_backend_name() -> str:
    return "postgresql" if using_postgres() else "sqlite"

def get_db_connection():
    if using_postgres():
        if psycopg is None:
            raise RuntimeError("PostgreSQL support requires psycopg.")
        conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        return DatabaseConnection(conn, "postgres")

    db_path = _SQLITE_DB_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return DatabaseConnection(conn, "sqlite")

class DatabaseCursor:
    def __init__(self, cursor: Any, backend: str):
        self._cursor = cursor
        self._backend = backend
        self.lastrowid: Optional[int] = None

    def execute(self, sql: str, params: Optional[Sequence[Any]] = None):
        self.lastrowid = None
        if params is None:
            self._cursor.execute(sql)
        else:
            self._cursor.execute(sql, tuple(params))
        self.lastrowid = getattr(self._cursor, "lastrowid", None)
        return self

    def executemany(self, sql: str, seq_of_params: Iterable[Sequence[Any]]):
        self._cursor.executemany(sql, [tuple(params) for params in seq_of_params])
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def __getattr__(self, name: str):
        return getattr(self._cursor, name)

class DatabaseConnection:
    def __init__(self, connection: Any, backend: str):
        self._connection = connection
        self._backend = backend

    def cursor(self):
        return DatabaseCursor(self._connection.cursor(), self._backend)

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        self._connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc is not None:
            self.rollback()
        else:
            self.commit()
        self.close()

def init_database():
    """Initialize streamlined database schema for Crypto Sniper."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Minimal Agents table for the bot
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            token TEXT,
            points INTEGER DEFAULT 0,
            cash REAL DEFAULT 100000.0,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Crypto Sniper Snapshots (Opportunities & AI Context)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_analysis_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            market TEXT NOT NULL,
            analysis_id TEXT UNIQUE NOT NULL,
            current_price REAL,
            currency TEXT,
            signal TEXT,
            signal_score INTEGER,
            trend_status TEXT,
            support_levels_json TEXT,
            resistance_levels_json TEXT,
            bullish_factors_json TEXT,
            risk_factors_json TEXT,
            summary_text TEXT,
            analysis_json TEXT,
            created_at TEXT NOT NULL
        )
    """)

    # ID Sequence for signals
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signal_sequence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL
        )
    """)

    # High-conviction signals log (for marketplace and tracking)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER,
            agent_id INTEGER,
            message_type TEXT,
            market TEXT,
            signal_type TEXT,
            symbol TEXT NOT NULL,
            side TEXT,
            entry_price REAL,
            exit_price REAL,
            title TEXT,
            content TEXT,
            timestamp INTEGER,
            created_at TEXT NOT NULL
        )
    """)

    if not using_postgres():
        conn.commit()
    conn.close()
    print("[INFO] Streamlined Database initialized")

def get_database_status() -> dict[str, Any]:
    return {"backend": get_database_backend_name()}
