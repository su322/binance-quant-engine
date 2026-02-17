from fastapi import APIRouter
from backend.routers.v1.data import router as data_router
from backend.routers.v1.backtest import router as backtest_router
from backend.routers.v1.trade import router as trade_router

router = APIRouter(prefix="/api/v1")

router.include_router(data_router)
router.include_router(backtest_router)
router.include_router(trade_router)
