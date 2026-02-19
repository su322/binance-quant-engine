from fastapi import APIRouter, HTTPException
from typing import List
from backend.schemas.trade import (
    StartStrategyRequest,
    StopStrategyRequest,
    StrategyStatusResponse,
)
from backend.schemas.response import StandardResponse
from backend.services.live.engine import trade_service
from backend.core.logger import get_logger

router = APIRouter(prefix="/trade", tags=["trade"])

logger = get_logger("TradeRouter")


@router.post("/start", response_model=StandardResponse[StrategyStatusResponse])
async def start_strategy(request: StartStrategyRequest):
    """
    启动实盘策略
    """
    try:
        strategy_id = await trade_service.start_strategy(
            request.strategy_name, request.symbol, request.parameters
        )
        return StandardResponse(
            data=StrategyStatusResponse(
                strategy_id=strategy_id,
                strategy_name=request.strategy_name,
                symbol=request.symbol,
                status="running",
                parameters=request.parameters,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop", response_model=StandardResponse[StrategyStatusResponse])
async def stop_strategy(request: StopStrategyRequest):
    """
    停止实盘策略
    """
    try:
        # 先获取信息用于返回
        strategies = trade_service.get_strategies()
        target = next(
            (s for s in strategies if s["strategy_id"] == request.strategy_id), None
        )

        if not target:
            raise HTTPException(status_code=404, detail="Strategy not found")

        await trade_service.stop_strategy(request.strategy_id)

        # 更新状态为 stopped
        target["status"] = "stopped"

        return StandardResponse(data=StrategyStatusResponse(**target))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=StandardResponse[List[StrategyStatusResponse]])
async def list_strategies():
    """
    列出所有运行中的策略
    """
    try:
        strategies = trade_service.get_strategies()
        return StandardResponse(data=[StrategyStatusResponse(**s) for s in strategies])
    except Exception as e:
        logger.error(f"Failed to list strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))
