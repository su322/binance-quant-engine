from typing import Dict, Any, List, Optional
from backend.strategies.base import BaseStrategy
from backend.strategies.registry import register_strategy
from backend.models.order import Order
from backend.enums.types import OrderSide, OrderType


@register_strategy("GridStrategy")
class GridStrategy(BaseStrategy):
    """
    网格交易策略 (Grid Trading)

    逻辑：
    1. 动态网格：以当前持仓价格为中心，上挂卖单，下挂买单。
    2. 触发后：
       - 买单成交 -> 价格下跌 -> 以新低价为中心，下挂买单，上挂卖单（卖出刚才买入的）。
       - 卖单成交 -> 价格上涨 -> 以新高价为中心，下挂买单（买回刚才卖出的），上挂卖单。
    
    配置参数:
    - grid_size: 网格大小 (如 0.01 代表 1%)
    - investment_per_grid: 每网格投入金额 (USDT)，优先使用
    - quantity: 每网格交易数量 (BTC)，兼容旧配置
    - initial_investment: 初始建仓金额 (USDT)，如果设置且需要建仓，则使用此金额买入
    - force_initial_buy: 是否强制初始建仓。
        - True: 启动时立即按 initial_investment 买入。
        - False (默认): 优先检查历史订单，如果有历史成交，则恢复上次价格；如果没有历史，则按 initial_investment 建仓。
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.symbol = config.get("symbol", "BTCUSDT")
        self.grid_size = float(
            config.get("grid_size", 0.01)
        )  # 网格大小 (百分比，如 0.01 = 1%)
        
        # 投资金额配置
        # 如果设置了 investment_per_grid，则优先按固定金额计算数量 (Quote Currency)
        # 否则按 quantity 固定数量交易 (Base Currency)
        self.investment_per_grid = float(config.get("investment_per_grid", 0.0)) 
        self.quantity = float(config.get("quantity", 0.001))  # 每次交易数量

        # 初始建仓配置
        self.initial_investment = float(config.get("initial_investment", 0.0))
        # 默认 False，即“如果不建仓(False)，就先看前面有没有买卖”
        self.force_initial_buy = config.get("force_initial_buy", False)

        # 状态变量
        self.last_trade_price = None  # 上次成交价格 (中心价格)
        self.active_buy_order = None  # 当前挂的买单价格
        self.active_sell_order = None  # 当前挂的卖单价格

    async def on_start(self):
        """初始化"""
        self.logger.info(f"Starting Dynamic Grid Strategy for {self.symbol}")
        mode = "Fixed USDT" if self.investment_per_grid > 0 else "Fixed Qty"
        val = self.investment_per_grid if self.investment_per_grid > 0 else self.quantity
        self.logger.info(f"Grid Size: {self.grid_size*100}%, Mode: {mode}, Val: {val}")

    async def on_stop(self):
        """停止"""
        self.logger.info("Grid strategy stopped.")

    async def on_tick(self, tick_data: Dict[str, Any]):
        pass

    def _get_trade_quantity(self, price: float) -> float:
        """根据价格计算交易数量"""
        if self.investment_per_grid > 0:
            # 固定金额模式: Qty = Amount / Price
            return self.investment_per_grid / price
        return self.quantity

    async def on_kline(self, kline_data: Dict[str, Any]):
        """
        处理K线数据 (模拟撮合)
        """
        if not self.broker:
            self.logger.error("Broker not set!")
            return

        current_price = float(kline_data["close"])

        # 1. 如果是第一次运行
        if self.last_trade_price is None:
            
            # 尝试从 Broker 获取历史订单来恢复状态
            # 只有当 force_initial_buy 为 False 时才尝试恢复
            history_recovered = False
            if not self.force_initial_buy:
                history_orders = self.broker.get_history_orders(self.symbol, limit=1)
                if history_orders and len(history_orders) > 0:
                    last_order = history_orders[0]
                    # 假设历史订单的成交价作为基准价
                    # 注意：实盘中可能需要更复杂的逻辑来确定“上一网”的价格，这里简化为最近一次成交价
                    price = last_order.price if last_order.price else current_price # 防止 None
                    self.last_trade_price = price
                    self.logger.info(f"Resumed from history: Base Price = {self.last_trade_price}")
                    history_recovered = True

            # 如果没有恢复成功（强制建仓，或者没有历史），则执行初始建仓
            if not history_recovered:
                # 决定初始买入金额：优先用 initial_investment，没有则用 investment_per_grid
                init_invest = self.initial_investment if self.initial_investment > 0 else self.investment_per_grid
                
                if init_invest > 0:
                    self.logger.info(f"Performing Initial Buy: {init_invest} USDT")
                    qty = init_invest / current_price
                    order = Order(self.symbol, OrderSide.BUY, OrderType.MARKET, qty)
                    self.broker.create_order(order)
                    # 成交后，基准价即为当前价 (或者成交均价，这里简化)
                    self.last_trade_price = current_price
                else:
                    # 如果没有配置初始金额，直接以当前价格为基准，不操作
                    self.last_trade_price = current_price
                    self.logger.info(f"Initialized Base Price (No Buy): {self.last_trade_price}")

            self._update_grid_levels()
            return

        # 2. 检查买单成交 (价格跌破买入价)
        if self.active_buy_order and current_price <= self.active_buy_order:
            self.logger.info(
                f"BUY FILLED at {current_price} (Target: {self.active_buy_order})"
            )

            # 执行买入
            # 按触发价计算数量
            qty = self._get_trade_quantity(self.active_buy_order)
            order = Order(self.symbol, OrderSide.BUY, OrderType.MARKET, qty)
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
            # 按触发价计算数量
            qty = self._get_trade_quantity(self.active_sell_order)
            order = Order(self.symbol, OrderSide.SELL, OrderType.MARKET, qty)
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
