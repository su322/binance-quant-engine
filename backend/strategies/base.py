from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from backend.core.logger import get_logger
from backend.core.event_bus import event_bus, Event, EventType
from backend.services.base import BaseBroker, Order, OrderSide, OrderType


class BaseStrategy(ABC):
    """
    策略基类
    所有交易策略都必须继承此类
    """

    def __init__(
        self, name: str, config: Dict[str, Any], broker: Optional[BaseBroker] = None
    ):
        self.name = name
        self.config = config
        self.broker = broker  # 交易所代理 (回测或实盘)
        self.logger = get_logger(f"Strategy.{name}")
        self.is_running = False

    def set_broker(self, broker: BaseBroker):
        """注入 Broker"""
        self.broker = broker

    async def start(self):
        """启动策略"""
        if self.is_running:
            self.logger.warning(f"Strategy {self.name} is already running.")
            return

        self.is_running = True
        self.logger.info(f"Starting strategy: {self.name}")
        await self.on_start()

        # 发布策略启动事件
        await event_bus.publish(Event(EventType.STRATEGY_STARTED, {"name": self.name}))

    async def stop(self):
        """停止策略"""
        if not self.is_running:
            self.logger.warning(f"Strategy {self.name} is not running.")
            return

        self.is_running = False
        self.logger.info(f"Stopping strategy: {self.name}")
        await self.on_stop()

        # 发布策略停止事件
        await event_bus.publish(Event(EventType.STRATEGY_STOPPED, {"name": self.name}))

    @abstractmethod
    async def on_start(self):
        """策略启动时的初始化逻辑"""
        pass

    @abstractmethod
    async def on_stop(self):
        """策略停止时的清理逻辑"""
        pass

    @abstractmethod
    async def on_tick(self, tick_data: Dict[str, Any]):
        """
        处理行情快照 (Ticker/Trade)
        - 频率：高 (每秒可能有多次推送)
        - 内容：当前最新价格、最优买卖一价、成交量等
        - 适用：高频交易、网格交易、套利策略（需要实时监控价格变化）
        """
        pass

    @abstractmethod
    async def on_kline(self, kline_data: Dict[str, Any]):
        """
        处理K线数据 (Candlestick)
        - 频率：低 (取决于时间周期，如每分钟一次)
        - 内容：开盘价(Open)、最高价(High)、最低价(Low)、收盘价(Close)、成交量(Volume)
        - 适用：趋势跟踪、均线策略、技术指标分析（MACD, RSI等）
        """
        pass
