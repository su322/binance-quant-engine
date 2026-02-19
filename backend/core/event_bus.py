import asyncio
from typing import Callable, List, Dict, Any
from backend.core.logger import get_logger
from backend.enums.event import EventType

logger = get_logger("EventBus")

class Event:
    """
    基础事件对象
    """

    def __init__(self, type: str, data: Dict[str, Any] = None):
        self.type = type
        self.data = data or {}
        try:
             self.timestamp = asyncio.get_event_loop().time()
        except RuntimeError:
             import time
             self.timestamp = time.time()


class EventBus:
    """
    异步事件总线 (单例模式)
    """

    _instance = None
    _subscribers: Dict[str, List[Callable[[Event], Any]]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance._subscribers = {}
        return cls._instance

    def subscribe(self, event_type: str, callback: Callable[[Event], Any]):
        """
        订阅事件
        :param event_type: 事件类型 (EventType.TICKER_UPDATE)
        :param callback: 回调函数 (async def handle(event))
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.info(f"Subscribed to {event_type}")

    async def publish(self, event: Event):
        """
        发布事件 (异步非阻塞)
        """
        if event.type in self._subscribers:
            tasks = []
            for callback in self._subscribers[event.type]:
                # 如果回调是异步函数，直接调用
                if asyncio.iscoroutinefunction(callback):
                    tasks.append(asyncio.create_task(callback(event)))
                else:
                    # 如果是同步函数，在线程池中运行（避免阻塞事件循环）
                    # 简化起见，这里假设回调尽量使用 async
                    try:
                        callback(event)
                    except Exception as e:
                        logger.error(
                            f"Error in synchronous handler for {event.type}: {e}"
                        )

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # logger.debug(f"No subscribers for {event.type}")
            pass


# 全局单例
event_bus = EventBus()
