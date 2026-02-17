from typing import Dict, Any, List, Optional
from backend.strategies.base import BaseStrategy
from backend.strategies.registry import register_strategy
from backend.services.base import Order, OrderSide, OrderType


@register_strategy("GridStrategy")
class GridStrategy(BaseStrategy):
    """
    网格交易策略 (Grid Trading)

    逻辑：
    1. 动态网格：以当前持仓价格为中心，上挂卖单，下挂买单。
    2. 触发后：
       - 买单成交 -> 价格下跌 -> 以新低价为中心，下挂买单，上挂卖单（卖出刚才买入的）。
       - 卖单成交 -> 价格上涨 -> 以新高价为中心，下挂买单（买回刚才卖出的），上挂卖单。
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.symbol = config.get("symbol", "BTCUSDT")
        self.grid_size = float(
            config.get("grid_size", 0.01)
        )  # 网格大小 (百分比，如 0.01 = 1%)
        self.quantity = float(config.get("quantity", 0.001))  # 每次交易数量

        # 状态变量
        self.last_trade_price = None  # 上次成交价格 (中心价格)
        self.active_buy_order = None  # 当前挂的买单价格
        self.active_sell_order = None  # 当前挂的卖单价格

    async def on_start(self):
        """初始化"""
        self.logger.info(f"Starting Dynamic Grid Strategy for {self.symbol}")
        self.logger.info(f"Grid Size: {self.grid_size*100}%, Qty: {self.quantity}")

    async def on_stop(self):
        """停止"""
        self.logger.info("Grid strategy stopped.")

    async def on_tick(self, tick_data: Dict[str, Any]):
        pass

    async def on_kline(self, kline_data: Dict[str, Any]):
        """
        处理K线数据 (模拟撮合)
        """
        if not self.broker:
            self.logger.error("Broker not set!")
            return

        current_price = float(kline_data["close"])

        # 1. 如果是第一次运行，以当前价格建仓（或者假设已建仓）
        if self.last_trade_price is None:
            self.last_trade_price = current_price
            self.logger.info(f"Initialized Base Price: {self.last_trade_price}")
            self._update_grid_levels()
            return

        # 2. 检查买单成交 (价格跌破买入价)
        if self.active_buy_order and current_price <= self.active_buy_order:
            self.logger.info(
                f"BUY FILLED at {current_price} (Target: {self.active_buy_order})"
            )

            # 执行买入
            order = Order(self.symbol, OrderSide.BUY, OrderType.MARKET, self.quantity)
            self.broker.create_order(order)

            # 更新中心价格为触发价
            self.last_trade_price = self.active_buy_order
            self._update_grid_levels()

        # 3. 检查卖单成交 (价格涨破卖出价)
        elif self.active_sell_order and current_price >= self.active_sell_order:
            self.logger.info(
                f"SELL FILLED at {current_price} (Target: {self.active_sell_order})"
            )

            # 执行卖出
            order = Order(self.symbol, OrderSide.SELL, OrderType.MARKET, self.quantity)
            self.broker.create_order(order)

            # 更新中心价格为触发价
            self.last_trade_price = self.active_sell_order
            self._update_grid_levels()

    def _update_grid_levels(self):
        """更新网格挂单价格"""
        # 下一网格买入价 = 中心价 * (1 - 网格大小)
        self.active_buy_order = self.last_trade_price * (1 - self.grid_size)

        # 下一网格卖出价 = 中心价 * (1 + 网格大小)
        self.active_sell_order = self.last_trade_price * (1 + self.grid_size)

        self.logger.info(
            f"New Grid Levels -> Buy: {self.active_buy_order:.2f}, Sell: {self.active_sell_order:.2f} (Base: {self.last_trade_price:.2f})"
        )
