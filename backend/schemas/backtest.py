from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List


class BacktestRequest(BaseModel):
    """
    回测请求参数
    """

    strategy_name: str = Field(..., description="策略名称，如 GridStrategy")
    symbol: str = Field(..., description="交易对，如 BTCUSDT")
    interval: str = Field("1m", description="K线周期")
    start_time: Optional[str] = Field(
        None, description="开始时间 (YYYY-MM-DD 或 YYYY-MM-DD HH:mm:ss)"
    )
    end_time: Optional[str] = Field(None, description="结束时间")
    initial_balance: float = Field(10000.0, description="初始资金 (USDT)")
    parameters: Dict[str, Any] = Field({}, description="策略特定参数")


class BacktestResult(BaseModel):
    """
    回测结果摘要
    """

    total_trades: int
    final_balance: float
    profit: float
    profit_percentage: float
    trades: List[Dict[str, Any]] = []


class StrategyConfig(BaseModel):
    """
    策略配置
    """

    name: str
    type: str
    parameters: Dict[str, Any]
    status: str = "stopped"
