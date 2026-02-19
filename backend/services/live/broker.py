from typing import List, Dict, Optional
from backend.exchange.base import BaseBroker
from backend.models.order import Order
from backend.enums.types import MarketType
from backend.core.logger import get_logger
from abc import abstractmethod

logger = get_logger("LiveBroker")

class LiveBroker(BaseBroker):
    """
    实盘交易 Broker 基类
    """
    def __init__(self, api_key: str, secret_key: str, market_type: MarketType):
        super().__init__(market_type)
        self.api_key = api_key
        self.secret_key = secret_key
        # TODO: Initialize exchange client here or in subclasses

    @abstractmethod
    def create_order(self, order: Order) -> Order:
        raise NotImplementedError

    @abstractmethod
    def cancel_order(self, order_id: str):
        raise NotImplementedError

    @abstractmethod
    def get_account_balance(self, asset: str) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_open_orders(self, symbol: str) -> List[Order]:
        raise NotImplementedError

    @abstractmethod
    def get_history_orders(self, symbol: str, limit: int = 10) -> List[Order]:
        raise NotImplementedError

    @abstractmethod
    def get_position(self, symbol: str) -> Dict[str, float]:
        raise NotImplementedError
