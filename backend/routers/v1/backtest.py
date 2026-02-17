from fastapi import APIRouter, HTTPException
from backend.schemas.backtest import BacktestRequest, BacktestResult
from backend.schemas.response import StandardResponse
from backend.services.backtest_service import backtest_service
from backend.core.logger import get_logger

router = APIRouter(prefix="/backtest", tags=["backtest"])

logger = get_logger("BacktestRouter")


from typing import List, Dict, Any


@router.post("/run", response_model=StandardResponse[Dict[str, Any]])
async def run_backtest(request: BacktestRequest):
    """
    运行回测
    """
    try:
        result = await backtest_service.run_backtest(
            request.strategy_name,
            request.symbol,
            request.interval,
            request.initial_balance,
            request.parameters,
        )
        return StandardResponse(data=result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=StandardResponse[List[Dict[str, Any]]])
async def list_backtest_results():
    """
    列出所有回测结果
    """
    try:
        results = backtest_service.get_backtest_results()
        return StandardResponse(data=results)
    except Exception as e:
        logger.error(f"Failed to list backtest results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{backtest_id}", response_model=StandardResponse[Dict[str, Any]])
async def get_backtest_result(backtest_id: str):
    """
    获取具体回测结果详情
    """
    try:
        result = backtest_service.get_backtest_result(backtest_id)
        if not result:
            raise HTTPException(status_code=404, detail="Backtest result not found")
        return StandardResponse(data=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get backtest result: {e}")
        raise HTTPException(status_code=500, detail=str(e))
