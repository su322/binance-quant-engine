from enum import Enum

class EventType(str, Enum):
    """
    事件类型枚举
    """
    TICKER_UPDATE = "TICKER_UPDATE"  # 行情更新
    ORDER_FILLED = "ORDER_FILLED"  # 订单成交
    STRATEGY_SIGNAL = "STRATEGY_SIGNAL"  # 策略信号
    SYSTEM_ERROR = "SYSTEM_ERROR"  # 系统错误
    STRATEGY_STARTED = "STRATEGY_STARTED"  # 策略启动
    STRATEGY_STOPPED = "STRATEGY_STOPPED"  # 策略停止
    TEST_EVENT = "TEST_EVENT" # 测试事件
