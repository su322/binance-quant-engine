from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List


class StartStrategyRequest(BaseModel):
    """
    启动策略请求
    """

    strategy_name: str = Field(..., description="策略名称，如 GridStrategy")
    symbol: str = Field(..., description="交易对，如 BTCUSDT")
    parameters: Dict[str, Any] = Field({}, description="策略参数")


class StopStrategyRequest(BaseModel):
    """
    停止策略请求
    """

    strategy_id: str = Field(..., description="策略实例 ID")


class StrategyStatusResponse(BaseModel):
    """
    策略状态响应
    """

    strategy_id: str
    strategy_name: str
    symbol: str
    status: str
    parameters: Dict[str, Any]
