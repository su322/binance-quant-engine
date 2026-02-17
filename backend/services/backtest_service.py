import os
import sys
from typing import Dict, Any

import pandas as pd

from backend.services.base import BaseBroker, Order, OrderSide, OrderType, OrderStatus
from backend.core.logger import get_logger
from backend.strategies.registry import StrategyRegistry
from backend.services.execution_service import BacktestBroker

# 临时 hack，确保能导入策略
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

logger = get_logger("BacktestService")


class BacktestService:
    """
    回测服务
    """

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            # Default to backend/data/backtest
            self.data_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data",
                "backtest",
            )
        else:
            self.data_dir = os.path.abspath(data_dir)

        # 存储回测结果
        self.backtest_results = {}

    async def run_backtest(
        self,
        strategy_name: str,
        symbol: str,
        interval: str,
        initial_balance: float,
        params: Dict[str, Any],
    ):
        """
        运行回测
        """
        logger.info(f"Starting backtest for {strategy_name} on {symbol}")

        # 1. 加载数据
        file_path = os.path.join(self.data_dir, f"{symbol}-{interval}.csv")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Data file not found: {file_path}")

        df = pd.read_csv(file_path)
        logger.info(f"Loaded {len(df)} candles")

        # 2. 初始化 Broker 和 Strategy
        broker = BacktestBroker(initial_balance)

        # 构造策略配置
        config = {"symbol": symbol}
        config.update(params)

        # 从注册表获取策略类
        strategy_class = StrategyRegistry.get_strategy_class(strategy_name)
        if not strategy_class:
            # 尝试根据名称推断 (临时处理，未来应该完善注册机制)
            if strategy_name == "GridStrategy":
                from backend.strategies.grid import GridStrategy

                strategy_class = GridStrategy
            else:
                raise ValueError(f"Unknown strategy: {strategy_name}")

        strategy = strategy_class(strategy_name, config)
        strategy.set_broker(broker)

        await strategy.start()

        # 3. 循环回测
        for index, row in df.iterrows():
            kline_data = {
                "open_time": row.get("open_time"),
                "open": row.get("open"),
                "high": row.get("high"),
                "low": row.get("low"),
                "close": row.get("close"),
                "volume": row.get("volume"),
            }

            # 更新 Broker 价格
            broker.current_price = float(row["close"])

            # 触发策略
            await strategy.on_kline(kline_data)

        await strategy.stop()

        # 4. 计算结果
        final_balance = broker.balance + (broker.asset * broker.current_price)
        profit = final_balance - initial_balance
        profit_percent = (profit / initial_balance) * 100

        result = {
            "strategy_name": strategy_name,
            "symbol": symbol,
            "initial_balance": initial_balance,
            "final_balance": final_balance,
            "profit": profit,
            "profit_percent": profit_percent,
            "trades": broker.trades,
        }

        # 保存回测结果
        import uuid

        backtest_id = str(uuid.uuid4())
        result["backtest_id"] = backtest_id
        self.backtest_results[backtest_id] = result

        return result

    def get_backtest_results(self):
        """
        获取所有回测结果列表
        """
        results = []
        for backtest_id, result in self.backtest_results.items():
            results.append(
                {
                    "backtest_id": backtest_id,
                    "strategy_name": result["strategy_name"],
                    "symbol": result["symbol"],
                    "profit_percent": result["profit_percent"],
                    "final_balance": result["final_balance"],
                }
            )
        return results

    def get_backtest_result(self, backtest_id: str):
        """
        获取具体回测结果详情
        """
        return self.backtest_results.get(backtest_id)

        # 防止除零错误
        profit_percentage = 0.0
        if initial_balance > 0:
            profit_percentage = (profit / initial_balance) * 100

        result = {
            "total_trades": len(broker.trades),
            "final_balance": round(final_balance, 2),
            "profit": round(profit, 2),
            "profit_percentage": round(profit_percentage, 2),
            "trades": broker.trades,
        }

        logger.info(f"Backtest finished. Profit: {result['profit']}")
        return result

    def cancel_order(self, order_id: str):
        pass

    def get_account_balance(self, asset: str) -> float:
        return 0.0

    def get_open_orders(self, symbol: str) -> List[Order]:
        return []

    def get_position(self, symbol: str) -> Dict[str, float]:
        return {}

    def get_history_orders(self, symbol: str, limit: int = 10) -> List[Order]:
        return []


backtest_service = BacktestService()
