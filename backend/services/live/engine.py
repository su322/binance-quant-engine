import asyncio
import uuid
from typing import Dict, Any, List

from binance.spot import Spot as Client

from backend.models.order import Order
from backend.enums.types import OrderType, OrderStatus
from backend.core.config import settings
from backend.core.logger import get_logger
from backend.strategies.registry import StrategyRegistry
from backend.services.live.spot import SpotLiveBroker
from backend.services.live.future import FutureLiveBroker

logger = get_logger("TradeService")


class TradeService:
    """
    交易服务 (实盘)
    """

    def __init__(self):
        self.active_strategies: Dict[str, Any] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}

    async def start_strategy(
        self, strategy_name: str, symbol: str, params: Dict[str, Any]
    ) -> str:
        """
        启动一个策略实例
        """
        strategy_id = str(uuid.uuid4())
        logger.info(f"Starting strategy {strategy_name} ({strategy_id}) on {symbol}")

        # 1. 获取策略类
        strategy_class = StrategyRegistry.get_strategy_class(strategy_name)
        if not strategy_class:
            # 临时 hack
            if strategy_name == "GridStrategy":
                from backend.strategies.spot.grid import GridStrategy

                strategy_class = GridStrategy
            else:
                raise ValueError(f"Unknown strategy: {strategy_name}")

        # 2. 初始化策略
        config = {"symbol": symbol}
        config.update(params)
        strategy = strategy_class(strategy_name, config)

        # 3. 初始化实盘 Broker
        # 从配置中获取 API Key
        # 假设 params 中有 market_type，或者默认 SPOT
        market_type = params.get("market_type", "SPOT")
        
        # 获取 API Key
        # api_key, api_secret = settings.get_spot_test_keys()
        
        # testnet base_url
        base_url = settings.urls.spot_test_base_url
        future_base_url = settings.urls.future_test_base_url

        if market_type == "USDT_FUTURE":
            # TODO: Future keys
            # Currently using spot test keys for future as placeholder if not defined
            # future_api_key, future_secret_key = settings.get_future_test_keys()
            # For now, manually fallback to allow using spot keys for test
            future_api_key = settings.keys.future_test_api_key or settings.keys.spot_test_api_key
            future_secret_key = settings.keys.future_test_secret_key or settings.keys.spot_test_secret_key
            
            broker = FutureLiveBroker(future_api_key, future_secret_key, base_url=future_base_url)
        else:
            api_key, api_secret = settings.get_spot_test_keys()
            broker = SpotLiveBroker(api_key, api_secret, base_url=base_url)

        strategy.set_broker(broker)

        # 4. 启动策略循环 (在后台运行)
        # 注意：这里需要一个机制来持续获取行情并喂给策略
        # 简单起见，我们在这里启动一个 loop
        task = asyncio.create_task(self._strategy_loop(strategy, symbol, api_key, api_secret, base_url))

        self.active_strategies[strategy_id] = {
            "instance": strategy,
            "info": {
                "strategy_id": strategy_id,
                "strategy_name": strategy_name,
                "symbol": symbol,
                "status": "running",
                "parameters": params,
            },
        }
        self.running_tasks[strategy_id] = task

        return strategy_id

    def get_strategies(self) -> List[Dict[str, Any]]:
        """
        获取所有策略（包括运行中和已停止的）
        """
        strategies = []
        for strategy_id, info in self.active_strategies.items():
            strategies.append(info["info"])
        return strategies

    async def stop_strategy(self, strategy_id: str):
        """
        停止策略
        """
        if strategy_id in self.active_strategies:
            logger.info(f"Stopping strategy {strategy_id}")
            strategy_info = self.active_strategies[strategy_id]
            strategy = strategy_info["instance"]

            # 停止策略逻辑
            await strategy.stop()

            # 取消后台任务
            if strategy_id in self.running_tasks:
                self.running_tasks[strategy_id].cancel()
                del self.running_tasks[strategy_id]

            strategy_info["info"]["status"] = "stopped"
            # 也可以选择从 active_strategies 中删除
            # del self.active_strategies[strategy_id]
            return True
        else:
            raise ValueError(f"Strategy {strategy_id} not found")

    async def _strategy_loop(self, strategy, symbol: str, api_key: str, api_secret: str, base_url: str):
        """
        策略运行主循环 (模拟行情推送)
        实盘中应该对接 WebSocket 或 轮询 REST API
        """
        # 使用传入的 keys 初始化一个 data client
        client = Client(api_key, api_secret, base_url=base_url)

        # 启动策略
        await strategy.start()

        try:
            while True:
                # 简单轮询 K 线 (1m)
                try:
                    # 获取最近的 2 根 K 线，取倒数第二根（已完成的）或者最后一根（进行中的）
                    # 这里的逻辑取决于策略是 Close 触发还是 Tick 触发
                    # 假设我们用 1m K 线，每 2 秒轮询一次最新价格

                    # 1. 获取 ticker 价格用于实时计算 (可选)
                    # ticker = client.ticker_price(symbol)
                    # price = float(ticker['price'])

                    # 2. 获取 K 线数据
                    klines = client.klines(symbol, "1m", limit=1)
                    if klines:
                        latest = klines[-1]
                        open_time = latest[0]

                        # 构造 K 线数据结构
                        kline_data = {
                            "open_time": open_time,
                            "open": latest[1],
                            "high": latest[2],
                            "low": latest[3],
                            "close": latest[4],
                            "volume": latest[5],
                        }

                        # 每次轮询都推送最新状态给策略 (on_kline)
                        # 策略内部自己决定是否只在 K 线结束时交易，还是实时交易
                        # 对于网格策略，通常关注实时价格变化
                        await strategy.on_kline(kline_data)

                except Exception as e:
                    logger.error(f"Error fetching market data: {e}")

                await asyncio.sleep(2)  # 每 2 秒轮询一次
        except asyncio.CancelledError:
            logger.info(f"Strategy loop cancelled")
        except Exception as e:
            logger.error(f"Strategy loop failed: {e}")

    def get_strategies(self) -> List[Dict[str, Any]]:
        """
        获取所有策略状态
        """
        return [s["info"] for s in self.active_strategies.values()]


trade_service = TradeService()
