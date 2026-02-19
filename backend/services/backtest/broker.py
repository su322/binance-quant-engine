from typing import List, Dict, Optional
from backend.exchange.base import BaseBroker
from backend.models.order import Order
from backend.enums.types import OrderStatus, MarketType
from backend.core.logger import get_logger
from abc import abstractmethod

logger = get_logger("BrokerService")

class BacktestBroker(BaseBroker):
    """
    简易回测 Broker (内存版)
    """

    def __init__(
        self,
        initial_balance: float = 100.0,
        market_type: MarketType = MarketType.SPOT,
    ):
        super().__init__(market_type)
        self.balance = initial_balance
        self.asset = 0.0
        self.trades = []
        self.current_price = 0.0
        # 费率配置 (Maker/Taker 简化为统一费率，取较高者以保守估计)
        # 现货: 0.1%
        # U本位合约: Taker 0.05%
        if market_type == MarketType.SPOT:
            self.commission_rate = 0.001
        elif market_type == MarketType.USDT_FUTURE:
            self.commission_rate = 0.0005
        else:
            raise ValueError(f"Unsupported market type: {market_type}")

    def create_order(self, order: Order) -> Order:
        """
        创建订单 (由子类实现具体逻辑)
        """
        raise NotImplementedError("Subclasses must implement create_order")

    def _record_trade(self, side, price, qty, commission):
        self.trades.append(
            {
                "side": side,
                "price": price,
                "quantity": qty,
                "cost": price * qty,
                "commission": commission,
            }
        )

    def cancel_order(self, order_id: str):
        pass

    def get_account_balance(self, asset: str) -> float:
        """
        获取账户余额 (由子类实现具体逻辑)
        """
        raise NotImplementedError("Subclasses must implement get_account_balance")


    def get_open_orders(self, symbol: str) -> List[Order]:
        return []

    @abstractmethod
    def get_position(self, symbol: str) -> Dict[str, float]:
        """获取持仓 (由子类实现具体逻辑)"""
        raise NotImplementedError("Subclasses must implement get_position")

    def get_history_orders(self, symbol: str, limit: int = 10) -> List[Order]:
        """
        获取历史订单 (模拟)
        """
        # 简单返回最近的 N 个 trades 转换成的 Order
        history_orders = []
        # 注意：这里 self.trades 存的是 dict，需要转换
        # 而且 self.trades 只存了成交的，没存 CANCELED 等
        # 回测中通常策略自己记录了，这里仅做接口兼容
        return history_orders
