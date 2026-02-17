from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class OrderStatus(Enum):
    NEW = "NEW"  # 新订单，已挂单但未成交
    PARTIALLY_FILLED = "PARTIALLY_FILLED"  # 部分成交
    FILLED = "FILLED"  # 全部成交
    CANCELED = "CANCELED"  # 已撤销
    REJECTED = "REJECTED"  # 被拒绝（资金不足、参数错误等）


class MarketType(Enum):
    SPOT = "SPOT"  # 现货
    USDT_FUTURE = "USDT_FUTURE"  # U本位合约


class Order:
    def __init__(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        market_type: MarketType = MarketType.SPOT,  # 默认为现货
    ):
        self.symbol = symbol
        self.side = side
        self.order_type = order_type
        self.quantity = quantity
        self.price = price
        self.market_type = market_type
        self.status = OrderStatus.NEW
        self.order_id = None
        self.filled_price = None
        self.filled_quantity = 0
        self.commission = 0.0  # 手续费
        self.commission_asset = None  # 手续费资产 (e.g. BNB, USDT)


class BaseBroker(ABC):
    """
    交易所代理基类
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
    def get_position(self, symbol: str) -> Dict[str, float]:
        """获取持仓信息 (合约专用)"""
        pass

    @abstractmethod
    def get_history_orders(self, symbol: str, limit: int = 10) -> List[Order]:
        """获取历史订单 (用于程序重启后恢复状态或策略计算)"""
        pass
