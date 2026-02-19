from abc import ABC, abstractmethod
from typing import Dict, List
from backend.enums.types import MarketType
from backend.models.order import Order


class BaseBroker(ABC):
    """
    交易所代理基类 (Broker Interface)
    定义了策略与交易所交互的标准接口
    """

    def __init__(self, market_type: MarketType = MarketType.SPOT):
        self.market_type = market_type

    @abstractmethod
    def create_order(self, order: Order) -> Order:
        """创建订单"""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str):
        """取消订单"""
        pass

    @abstractmethod
    def get_account_balance(self, asset: str) -> float:
        """获取账户余额"""
        pass

    @abstractmethod
    def get_open_orders(self, symbol: str) -> List[Order]:
        """获取当前挂单 (用于程序重启后恢复状态)"""
        pass

    @abstractmethod
    def get_history_orders(self, symbol: str, limit: int = 10) -> List[Order]:
        """获取历史订单 (用于程序重启后恢复状态或策略计算)"""
        pass

    @abstractmethod
    def get_position(self, symbol: str) -> Dict[str, float]:
        """获取持仓信息 (合约专用)"""
        pass


class BaseExchangeClient(ABC):
    """
    交易所客户端基类 (Exchange Client Interface)
    封装具体的 API 调用 (如 REST, WebSocket)
    """
    pass
