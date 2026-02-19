from enum import Enum

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class OrderStatus(Enum):
    NEW = "NEW"  # 新订单，已挂单但未成交
    PARTIALLY_FILLED = "PARTIALLY_FILLED"  # 部分成交
    FILLED = "FILLED"  # 全部成交
    CANCELED = "CANCELED"  # 已撤销
    REJECTED = "REJECTED"  # 被拒绝（资金不足、参数错误等）


class MarketType(Enum):  # 我就交易这两种
    SPOT = "SPOT"  # 现货
    USDT_FUTURE = "USDT_FUTURE"  # U本位合约
