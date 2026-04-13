"""
Ludic2 Strategy Factory
Dynamic instantiation of trading strategies.
"""
from typing import Type
from ludic2.strategies.base import BaseStrategy
from ludic2.strategies.scalping_futures import ScalpingFuturesStrategy
from ludic2.strategies.swing import SwingStrategy
from ludic2.strategies.trend import TrendFollowingStrategy
from ludic2.strategies.daytrading import DaytradingStrategy
from ludic2.strategies.hodl import HodlStrategy
from ludic2.strategies.dca import DcaStrategy
from ludic2.strategies.breakout import BreakoutStrategy
from ludic2.strategies.rebound import ReboundStrategy
from ludic2.strategies.arbitrage import ArbitrageStrategy
from ludic2.strategies.hedging import HedgingStrategy

# Placeholder for future expansion
class PlaceholderStrategy(BaseStrategy):
    @property
    def name(self): return "🔒 В разработке"
    @property
    def description(self): return "Данная стратегия находится в разработке."
    @property
    def required_timeframes(self): return ["1h"]
    async def analyze(self, dfs, symbol): return None
    def generate_test_signal(self, symbol):
        from ludic2.strategies.base import Signal
        return Signal(
            symbol=symbol,
            direction="TEST",
            confidence="MEDIUM",
            score=0,
            max_score=0,
            entry_price=0,
            take_profit=0,
            stop_loss=0,
            risk_reward=0,
            timeframe="1h",
            strategy=self.name,
            factors=[]
        )


class StrategyFactory:
    """Factory to create and switch between strategies."""
    
    STRATEGIES: dict[str, Type[BaseStrategy]] = {
        "scalping": ScalpingFuturesStrategy,
        "swing": SwingStrategy,
        "trend": TrendFollowingStrategy,
        "daytrading": DaytradingStrategy,
        "hodl": HodlStrategy,
        "dca": DcaStrategy,
        "breakout": BreakoutStrategy,
        "rebound": ReboundStrategy,
        "arbitrage": ArbitrageStrategy,
        "hedging": HedgingStrategy,
    }

    @classmethod
    def get_strategy(cls, name: str) -> BaseStrategy:
        """Create a new instance of a strategy by code name."""
        strategy_cls = cls.STRATEGIES.get(name.lower(), PlaceholderStrategy)
        return strategy_cls()

    @classmethod
    def get_list(cls) -> list[dict]:
        """Get a list of all strategies with their metadata."""
        items = []
        for code, strategy_cls in cls.STRATEGIES.items():
            # Instantiate once to get metadata
            s = strategy_cls()
            items.append({
                "code": code,
                "name": s.name,
                "description": s.description
            })
        return items
