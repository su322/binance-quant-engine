from binance.spot import Spot as Client
from binance.um_futures import UMFutures as FutureClient
from typing import Optional, List, Dict

from backend.services.base import (
    BaseBroker,
    Order,
    OrderSide,
    OrderType,
    OrderStatus,
    MarketType,
)
from backend.core.config_loader import get_config
from backend.core.logger import get_logger

logger = get_logger("BrokerService")


class BacktestBroker(BaseBroker):
    """
    简易回测 Broker (内存版)
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        market_type: MarketType = MarketType.SPOT,
    ):
        super().__init__(market_type)
        self.balance = initial_balance
        self.asset = 0.0
        self.trades = []
        self.current_price = 0.0
        # 简单费率模拟
        self.commission_rate = 0.001 if market_type == MarketType.SPOT else 0.0004

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
        commission = cost * self.commission_rate
        order.commission = commission
        order.commission_asset = "USDT"  # 简化假设

        if order.side == OrderSide.BUY:
            total_cost = cost + commission
            if self.balance >= total_cost:
                self.balance -= total_cost
                self.asset += order.quantity
                self._record_trade("BUY", price, order.quantity, commission)
            else:
                order.status = OrderStatus.REJECTED
        elif order.side == OrderSide.SELL:
            if self.asset >= order.quantity:
                self.asset -= order.quantity
                self.balance += cost - commission
                self._record_trade("SELL", price, order.quantity, commission)
            else:
                order.status = OrderStatus.REJECTED
        return order

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
        if asset == "USDT":
            return self.balance
        if asset == "BTC":  # 简化
            return self.asset
        return 0.0

    def get_open_orders(self, symbol: str) -> List[Order]:
        return []

    def get_position(self, symbol: str) -> Dict[str, float]:
        return {"amount": self.asset, "entryPrice": 0.0}

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


class LiveBroker(BaseBroker):
    """
    实盘 Broker (对接 Binance API)
    """

    def __init__(self, symbol: str, market_type: MarketType = MarketType.SPOT):
        super().__init__(market_type)
        self.symbol = symbol

        # Load API keys
        section = "keys"
        # 根据不同市场类型加载不同配置或客户端
        if self.market_type == MarketType.SPOT:
            api_key, api_secret = get_config(
                "spot_test_api_key", "spot_test_secret_key", section=section
            )
            base_url = get_config("spot_base_url", section="urls")
            # testnet base_url
            self.client = Client(api_key, api_secret, base_url=base_url)
        elif self.market_type == MarketType.USDT_FUTURE:
            api_key, api_secret = get_config(
                "future_test_api_key", "future_test_secret_key", section=section
            )
            base_url = get_config("future_base_url", section="urls")
            self.client = FutureClient(
                key=api_key, secret=api_secret, base_url=base_url
            )

        # 解决 requests SSL 问题 (仅测试网需要)
        # self.client.session.verify = False # 某些版本可能不支持直接这样改，视具体库版本而定
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def create_order(self, order: Order) -> Order:
        """
        下单
        """
        try:
            params = {
                "symbol": order.symbol,
                "side": order.side.name,
                "type": order.order_type.name,
                "quantity": order.quantity,
            }
            if order.order_type == OrderType.LIMIT:
                params["price"] = order.price
                params["timeInForce"] = "GTC"

            # 发送下单请求
            response = self.client.new_order(**params)

            # 更新订单状态
            order.order_id = str(response["orderId"])
            order.status = OrderStatus.NEW  # 初始状态为 NEW

            status = response.get("status")
            if status == "FILLED":
                order.status = OrderStatus.FILLED
                # 尝试获取手续费信息 (通常在 fills 字段中，或者是成交后的回报)
                # 实盘中可能需要查询 myTrades 才能拿到准确的手续费
            elif status == "PARTIALLY_FILLED":
                order.status = OrderStatus.PARTIALLY_FILLED

            logger.info(f"Order created: {order.order_id} - {response}")
            return order
        except Exception as e:
            logger.error(f"Create order failed: {e}")
            order.status = OrderStatus.REJECTED
            return order

    def cancel_order(self, order_id: str):
        try:
            self.client.cancel_order(symbol=self.symbol, orderId=order_id)
            logger.info(f"Order cancelled: {order_id}")
        except Exception as e:
            logger.error(f"Cancel order failed: {e}")

    def get_account_balance(self, asset: str) -> float:
        try:
            if self.market_type == MarketType.SPOT:
                account = self.client.account()
                for balance in account["balances"]:
                    if balance["asset"] == asset:
                        return float(balance["free"])
            elif self.market_type == MarketType.USDT_FUTURE:
                # 合约账户查询
                account = self.client.balance()
                for balance in account:
                    if balance["asset"] == asset:
                        return float(balance["balance"])  # 或者 availableBalance
            return 0.0
        except Exception as e:
            logger.error(f"Get balance failed: {e}")
            return 0.0

    def get_open_orders(self, symbol: str) -> List[Order]:
        """获取挂单"""
        try:
            orders_data = self.client.get_open_orders(symbol=symbol)
            orders = []
            for o_data in orders_data:
                # 转换回 Order 对象
                # 注意：这里需要根据 API 返回字段仔细映射
                side = OrderSide[o_data["side"]]
                o_type = OrderType[o_data["type"]]
                price = float(o_data["price"])
                qty = float(o_data["origQty"])

                order = Order(symbol, side, o_type, qty, price, self.market_type)
                order.order_id = str(o_data["orderId"])
                order.status = (
                    OrderStatus.NEW
                )  # 既然是 open orders，肯定是 NEW 或 PARTIALLY_FILLED
                if o_data["status"] == "PARTIALLY_FILLED":
                    order.status = OrderStatus.PARTIALLY_FILLED
                orders.append(order)
            return orders
        except Exception as e:
            logger.error(f"Get open orders failed: {e}")
            return []

    def get_position(self, symbol: str) -> Dict[str, float]:
        """获取合约持仓"""
        if self.market_type != MarketType.USDT_FUTURE:
            return {}
        try:
            # 只有合约有 position
            # Binance API: GET /fapi/v2/positionRisk
            positions = self.client.get_position_risk(symbol=symbol)
            # positions 是一个列表（因为可能有双向持仓），这里简化处理单向
            for pos in positions:
                if pos["symbol"] == symbol:
                    amt = float(pos["positionAmt"])
                    entry_price = float(pos["entryPrice"])
                    return {"amount": amt, "entryPrice": entry_price}
            return {}
        except Exception as e:
            logger.error(f"Get position failed: {e}")
            return {}

    def get_history_orders(self, symbol: str, limit: int = 10) -> List[Order]:
        """
        重启后同步或策略使用：
        获取最近的历史订单
        """
        # 实盘实现：调用 myTrades 或 allOrders
        try:
            orders = []
            if self.market_type == MarketType.SPOT:
                # 现货查询历史订单 (allOrders) 或成交记录 (myTrades)
                # 这里使用 allOrders 可以查到挂单和成交单
                history_orders = self.client.get_orders(symbol=symbol, limit=limit)
            elif self.market_type == MarketType.USDT_FUTURE:
                # 合约查询
                history_orders = self.client.get_all_orders(symbol=symbol, limit=limit)

            for o_data in history_orders:
                side = OrderSide[o_data["side"]]
                o_type = OrderType[o_data["type"]]
                price = float(o_data["price"])
                qty = float(o_data["origQty"])

                order = Order(symbol, side, o_type, qty, price, self.market_type)
                order.order_id = str(o_data["orderId"])

                status = o_data["status"]
                if status == "NEW":
                    order.status = OrderStatus.NEW
                elif status == "FILLED":
                    order.status = OrderStatus.FILLED
                elif status == "PARTIALLY_FILLED":
                    order.status = OrderStatus.PARTIALLY_FILLED
                elif status == "CANCELED":
                    order.status = OrderStatus.CANCELED
                elif status == "REJECTED":
                    order.status = OrderStatus.REJECTED

                orders.append(order)
            return orders
        except Exception as e:
            logger.error(f"Get history orders failed: {e}")
            return []
