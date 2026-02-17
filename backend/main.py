from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
from backend.core.logger import get_logger
from backend.core.event_bus import event_bus, Event, EventType
from backend.routers.router import router
from backend.schemas.response import (
    StandardResponse,
    http_exception_handler,
    validation_exception_handler,
    global_exception_handler,
)

# 获取系统日志记录器
logger = get_logger("System")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 生命周期管理
    在应用启动前和关闭后执行逻辑
    """
    # --- 启动阶段 ---
    logger.info("Binance Quant Engine is starting up...")

    # 订阅测试事件
    async def on_test_event(event: Event):
        logger.info(f"Received TEST_EVENT: {event.data}")

    event_bus.subscribe("TEST_EVENT", on_test_event)

    yield

    # --- 关闭阶段 ---
    logger.info("Binance Quant Engine is shutting down...")


app = FastAPI(
    title="Binance Quant Engine",
    description="Algorithmic Trading System with Backtesting and Live Trading Capabilities",
    version="1.0.0",
    lifespan=lifespan,
)

# 注册异常处理器
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# 注册 API 路由
app.include_router(router)


@app.get("/", response_model=StandardResponse[dict])
async def root():
    """
    健康检查接口
    """
    return StandardResponse(
        data={"status": "ok", "message": "Binance Quant Engine is running"}
    )


@app.get("/test-event", response_model=StandardResponse[dict])
async def test_event(msg: str = "Hello Event Bus"):
    """
    测试事件总线功能
    """
    # 发布一个自定义事件
    event = Event("TEST_EVENT", {"message": msg})
    await event_bus.publish(event)
    logger.info(f"Published TEST_EVENT: {msg}")
    return StandardResponse(data={"status": "published", "event_data": event.data})


if __name__ == "__main__":
    import uvicorn

    # 启动开发服务器
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
