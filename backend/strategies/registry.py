from typing import Dict, Type
from backend.strategies.base import BaseStrategy
from backend.core.logger import get_logger

logger = get_logger("StrategyRegistry")


class StrategyRegistry:
    """
    策略注册表
    负责管理所有可用的策略类
    """

    _strategies: Dict[str, Type[BaseStrategy]] = {}

    @classmethod
    def register(cls, name: str, strategy_cls: Type[BaseStrategy]):
        """注册一个策略类"""
        if name in cls._strategies:
            logger.warning(f"Strategy {name} is already registered. Overwriting.")
        cls._strategies[name] = strategy_cls
        logger.info(f"Registered strategy: {name}")

    @classmethod
    def get_strategy_class(cls, name: str) -> Type[BaseStrategy]:
        """获取策略类"""
        if name not in cls._strategies:
            raise ValueError(f"Strategy {name} not found.")
        return cls._strategies[name]

    @classmethod
    def list_strategies(cls):
        """列出所有已注册的策略"""
        return list(cls._strategies.keys())


# 装饰器：用于自动注册策略
def register_strategy(name: str):
    def decorator(cls):
        StrategyRegistry.register(name, cls)
        return cls

    return decorator
