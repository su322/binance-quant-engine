from typing import List, Dict, Optional
from binance.spot import Spot
from backend.services.live.broker import LiveBroker
from backend.models.order import Order
from backend.enums.types import MarketType, OrderStatus, OrderSide, OrderType
from backend.core.logger import get_logger

logger = get_logger("LiveBroker.Spot")

class SpotLiveBroker(LiveBroker):
    """
    现货实盘 Broker
    """
    def __init__(self, api_key: str, secret_key: str, base_url: Optional[str] = None):
        super().__init__(api_key, secret_key, MarketType.SPOT)
        self.client = Spot(api_key, secret_key, base_url=base_url)
        logger.info("SpotLiveBroker initialized")

    def create_order(self, order: Order) -> Order:
        try:
            # 转换参数
            params = {
                "symbol": order.symbol,
                "side": order.side.value,
                "type": order.order_type.value,
                "quantity": order.quantity,
            }
            if order.order_type == OrderType.LIMIT:
                params["price"] = order.price
                params["timeInForce"] = "GTC" # 默认

            logger.info(f"Sending order to Binance: {params}")
            response = self.client.new_order(**params)
            
            # 更新订单状态
            order.order_id = str(response.get("orderId"))
            order.status = OrderStatus(response.get("status", "NEW"))
            # 更多字段映射...
            
            return order
        except Exception as e:
            logger.error(f"Failed to create order: {e}")
            order.status = OrderStatus.REJECTED
            return order

    def cancel_order(self, order_id: str):
        # TODO: Need symbol to cancel order in Binance API
        pass

    def get_account_balance(self, asset: str) -> float:
        try:
            account = self.client.account()
            balances = account.get("balances", [])
            for b in balances:
                if b["asset"] == asset:
                    return float(b["free"]) + float(b["locked"])
            return 0.0
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return 0.0

    def get_open_orders(self, symbol: str) -> List[Order]:
        # TODO: Implement mapping
        return []

    def get_history_orders(self, symbol: str, limit: int = 10) -> List[Order]:
        # TODO: Implement mapping
        return []

    def get_position(self, symbol: str) -> Dict[str, float]:
        # 现货没有持仓概念，通常返回资产余额
        # 但为了接口一致性...
        base_asset = symbol.replace("USDT", "") # 简单假设
        amount = self.get_account_balance(base_asset)
        return {"amount": amount, "entryPrice": 0.0}
