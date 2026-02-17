from backend.strategies.base import BaseStrategy
from backend.strategies.registry import register_strategy, StrategyRegistry

# 导入所有策略文件以触发注册
# from backend.strategies.sma import SMAStrategy
# from backend.strategies.grid import GridStrategy

__all__ = ["BaseStrategy", "register_strategy", "StrategyRegistry"]
