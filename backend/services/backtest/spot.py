from typing import List, Dict
from backend.models.order import Order
from backend.enums.types import OrderSide, OrderStatus, MarketType
from backend.services.backtest.broker import BacktestBroker
from backend.core.logger import get_logger

logger = get_logger("BrokerService")

class SpotBacktestBroker(BacktestBroker):
    """
    现货回测 Broker
    """

    def __init__(self, initial_balance: float = 100.0):
        super().__init__(initial_balance=initial_balance, market_type=MarketType.SPOT)

    def create_order(self, order: Order) -> Order:
        if order.market_type != self.market_type:
            logger.error(
                f"Order market type {order.market_type} does not match broker {self.market_type}"
            )
            order.status = OrderStatus.REJECTED
            return order

        order.status = OrderStatus.FILLED
        price = self.current_price
        cost = order.quantity * price

        # 计算手续费
        # 统一假设手续费扣除 USDT
        commission = cost * self.commission_rate
        order.commission = commission
        order.commission_asset = "USDT"

        if order.side == OrderSide.BUY:
            # 买入
            total_cost = cost + commission
            if self.balance >= total_cost:
                self.balance -= total_cost
                self.asset += order.quantity
                self._record_trade("BUY", price, order.quantity, commission)
            else:
                order.status = OrderStatus.REJECTED
        elif order.side == OrderSide.SELL:
            # 卖出
            if self.asset >= order.quantity:
                self.asset -= order.quantity
                self.balance += cost - commission
                self._record_trade("SELL", price, order.quantity, commission)
            else:
                order.status = OrderStatus.REJECTED
        return order

    def get_account_balance(self, asset: str) -> float:
        if asset == "USDT":
            return self.balance
        if asset == "BTC":  # 简化
            return self.asset
        return 0.0

    def get_position(self, symbol: str) -> Dict[str, float]:
        return {"amount": self.asset, "entryPrice": 0.0}
