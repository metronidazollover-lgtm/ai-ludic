from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.sql import func
from core.database import Base

class Agent(Base):
    __tablename__ = "agents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    token = Column(String)
    points = Column(Integer, default=0)
    cash = Column(Float, default=100000.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AIShadowLog(Base):
    __tablename__ = "ai_shadow_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, nullable=False)
    verdict = Column(String, nullable=False)
    confidence = Column(Integer)
    reasoning = Column(Text)
    entry = Column(Float)
    exit = Column(Float)
    stop_loss = Column(Float)
    metrics_json = Column(Text)  # We can use JSON type with Postgres, but Text is more compatible for SQLite
    labels_json = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SystemConfig(Base):
    __tablename__ = "system_config"
    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class UserWallet(Base):
    __tablename__ = "user_wallet"
    id = Column(Integer, primary_key=True, autoincrement=True)
    balance_usd = Column(Float, nullable=False, default=10000.0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class BybitAssetMeta(Base):
    __tablename__ = "bybit_assets_meta"
    symbol = Column(String, primary_key=True)
    daily_turnover = Column(Float)
    whale_threshold = Column(Float)
    support_res_json = Column(Text)
    last_sync = Column(String)

class WhaleWallMemory(Base):
    __tablename__ = "whale_walls_memory"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    side = Column(String, nullable=False)
    size = Column(Float, nullable=False)
    hits = Column(Integer, default=1)
    last_seen = Column(String)
