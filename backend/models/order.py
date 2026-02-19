from typing import Optional
from backend.enums.types import OrderSide, OrderType, OrderStatus, MarketType

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
