from typing import List, Dict, Optional
from binance.um_futures import UMFutures
from backend.services.live.broker import LiveBroker
from backend.models.order import Order
from backend.enums.types import MarketType, OrderStatus, OrderSide, OrderType
from backend.core.logger import get_logger

logger = get_logger("LiveBroker.Future")

class FutureLiveBroker(LiveBroker):
    """
    U本位合约实盘 Broker
    """
    def __init__(self, api_key: str, secret_key: str, base_url: Optional[str] = None):
        super().__init__(api_key, secret_key, MarketType.USDT_FUTURE)
        self.client = UMFutures(api_key, secret_key, base_url=base_url)
        logger.info("FutureLiveBroker initialized")

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

            logger.info(f"Sending order to Binance Future: {params}")
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
            assets = account.get("assets", [])
            for a in assets:
                if a["asset"] == asset:
                    return float(a["walletBalance"])
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
        try:
            positions = self.client.account().get("positions", [])
            for p in positions:
                if p["symbol"] == symbol:
                    amount = float(p["positionAmt"])
                    entry_price = float(p["entryPrice"])
                    unrealized_pnl = float(p["unrealizedProfit"])
                    # TODO: leverage, margin
                    return {
                        "amount": amount,
                        "entryPrice": entry_price,
                        "unrealizedPnL": unrealized_pnl,
                        "margin": float(p["initialMargin"])
                    }
            return {"amount": 0.0, "entryPrice": 0.0}
        except Exception as e:
            logger.error(f"Failed to get position: {e}")
            return {"amount": 0.0, "entryPrice": 0.0}
