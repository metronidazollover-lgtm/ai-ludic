from pydantic import BaseModel, Field
from typing import List, Optional

class BybitTicker(BaseModel):
    symbol: str
    lastPrice: str
    highPrice24h: str
    lowPrice24h: str
    turnover24h: str
    fundingRate: str
    openInterest: str

class Candle(BaseModel):
    close: float
    high: float
    low: float
    volume: float

class OrderbookEntry(BaseModel):
    price: float
    size: float

class AIVerdict(BaseModel):
    signal: str = Field(description="buy, sell, or skip")
    confidence: int = Field(ge=0, le=100)
    labels: List[str]
    summary: str
    entry: Optional[float] = None
    exit: Optional[float] = None
    stop_loss: Optional[float] = None
    time_to_tp_hours: Optional[int] = None
