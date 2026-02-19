from typing import List, Dict
from backend.models.order import Order
from backend.enums.types import OrderSide, OrderStatus, MarketType
from backend.services.backtest.broker import BacktestBroker
from backend.core.logger import get_logger

logger = get_logger("BrokerService")

class FutureBacktestBroker(BacktestBroker):
    """
    U本位合约回测 Broker
    支持杠杆、保证金、多空双向持仓 (One-way Mode: Net Position)
    """

    def __init__(self, initial_balance: float = 100.0, leverage: int = 1):
        super().__init__(initial_balance=initial_balance, market_type=MarketType.USDT_FUTURE)
        self.leverage = leverage
        # 记录持仓: symbol -> {amount: float, entry_price: float, margin: float}
        # amount > 0: 多仓, amount < 0: 空仓
        self.positions: Dict[str, Dict] = {}

    def create_order(self, order: Order) -> Order:
        """
        合约下单逻辑 (覆盖基类)
        """
        if order.market_type != self.market_type:
            logger.error(f"Market type mismatch: {order.market_type} != {self.market_type}")
            order.status = OrderStatus.REJECTED
            return order

        order.status = OrderStatus.FILLED
        price = self.current_price
        # 合约的名义价值
        notional_value = order.quantity * price
        
        # 计算手续费 (基于名义价值)
        commission = notional_value * self.commission_rate
        order.commission = commission
        order.commission_asset = "USDT"

        # 获取当前持仓
        symbol = order.symbol
        position = self.positions.get(symbol, {"amount": 0.0, "entry_price": 0.0, "margin": 0.0})
        current_qty = position["amount"]

        # 判断是 开仓 还是 平仓
        # 简单逻辑 (One-way Mode):
        # BUY: 增加多头 或 减少空头
        # SELL: 增加空头 或 减少多头
        
        # 变动方向: BUY为正, SELL为负
        qty_change = order.quantity if order.side == OrderSide.BUY else -order.quantity
        new_qty = current_qty + qty_change

        # 1. 计算实现的盈亏 (Realized PnL)
        # 只有在减少持仓绝对值时，才会有 Realized PnL
        realized_pnl = 0.0
        
        # 情况A: 同向加仓 (e.g. 持多买入, 持空卖出, 或 空仓开多/空) -> 更新平均开仓价
        if (current_qty == 0) or (current_qty > 0 and qty_change > 0) or (current_qty < 0 and qty_change < 0):
            # 增加持仓，需要扣除保证金
            # 所需保证金 = 增量价值 / 杠杆
            margin_required = (abs(qty_change) * price) / self.leverage
            
            # 检查余额 (可用余额 = 总余额 - 已占用保证金)
            # 这里简化：self.balance 视为 "Wallet Balance" (包含已实现盈亏，不包含未实现盈亏)
            # 但为了严谨，我们应该维护 available_balance
            # 简单处理: 直接从 balance 扣除手续费，并检查是否有足够资金做保证金
            
            total_cost = commission + margin_required
            # 注意: 保证金不是花费，是冻结。但如果余额不足以支付手续费+冻结，则拒单。
            # 这里简单起见，假设 margin 也是从 balance 划转出去的 (隔离仓位模式)
            
            if self.balance >= total_cost:
                self.balance -= commission # 扣手续费
                # self.balance -= margin_required # 冻结保证金? 
                # 通常 backtest 引擎会将 balance 视为 Equity 或者 Wallet Balance.
                # 让我们定义 self.balance 为 Wallet Balance (可用现金).
                # 开仓占用保证金，意味着可用现金减少.
                
                # 更新持仓均价
                # new_entry_price = (old_val + new_val) / new_qty
                old_val = abs(current_qty) * position["entry_price"]
                new_val_increment = abs(qty_change) * price
                new_avg_price = (old_val + new_val_increment) / abs(new_qty)
                
                position["entry_price"] = new_avg_price
                position["amount"] = new_qty
                # 累加保证金
                position["margin"] += margin_required
                
                # 只有手续费是实际支出的
                # 保证金只是被挪到了 position["margin"]
                self.balance -= margin_required 

            else:
                order.status = OrderStatus.REJECTED
                logger.warning("Insufficient balance for margin + commission")
                return order

        # 情况B: 反向平仓 (e.g. 持多卖出, 持空买入) -> 计算盈亏, 释放保证金
        else:
            # 能够平掉的数量
            # 如果 new_qty 符号改变，说明是 "平仓 + 反向开仓"
            # 这里先处理 "平仓" 部分
            
            closed_qty = 0.0
            remaining_qty = 0.0 # 反向开仓部分
            
            if abs(qty_change) <= abs(current_qty):
                # 只是部分或全部平仓
                closed_qty = abs(qty_change)
                remaining_qty = 0.0
            else:
                # 平仓后反向开仓
                closed_qty = abs(current_qty)
                remaining_qty = abs(qty_change) - closed_qty
            
            # 1. 结算平仓部分
            # PnL = (Exit Price - Entry Price) * qty * direction
            # direction: 多头平仓(卖)为1, 空头平仓(买)为-1
            direction = 1 if current_qty > 0 else -1
            pnl = (price - position["entry_price"]) * closed_qty * direction
            
            realized_pnl += pnl
            
            # 释放保证金 (按比例)
            margin_released = position["margin"] * (closed_qty / abs(current_qty))
            position["margin"] -= margin_released
            
            # 更新余额: 余额 + 释放的保证金 + 盈亏 - 手续费
            self.balance += margin_released + pnl - commission
            
            # 更新持仓数量
            # 如果完全平仓，amount归零
            if remaining_qty == 0:
                position["amount"] = new_qty # 此时 new_qty 应该是 current + change (同符号或0)
                if position["amount"] == 0:
                    position["entry_price"] = 0.0
                    position["margin"] = 0.0
            
            # 2. 处理反向开仓部分 (如果 qty_change 很大)
            if remaining_qty > 0:
                # 这部分相当于新的开仓
                # 方向与 qty_change 相同
                new_side_direction = 1 if qty_change > 0 else -1
                
                margin_required = (remaining_qty * price) / self.leverage
                
                if self.balance >= margin_required: # 手续费前面已经全扣了? 不，应该分开算手续费
                    # 刚才手续费是按总 order.quantity 算的，已经扣了
                    # 这里只要检查保证金够不够
                    
                    self.balance -= margin_required
                    position["amount"] = remaining_qty * new_side_direction
                    position["entry_price"] = price
                    position["margin"] = margin_required
                else:
                    # 资金不足以反向开仓，这就尴尬了。
                    # 回测简单处理：拒绝整个订单，或者只执行平仓部分。
                    # 为了简化，如果钱不够反手，就只平仓，不反手 (Reject remaining?)
                    # 或者直接 Reject 整个订单.
                    order.status = OrderStatus.REJECTED
                    logger.warning("Insufficient balance for reverse position opening")
                    # 此时要回滚前面的操作吗？
                    # 简单起见，拒绝整个订单
                    # 恢复 balance
                    self.balance -= (margin_released + pnl - commission)
                    position["margin"] += margin_released
                    return order

        # 保存状态
        self.positions[symbol] = position
        
        self._record_trade(order.side.name, price, order.quantity, commission)
        return order

    def get_position(self, symbol: str) -> Dict[str, float]:
        pos = self.positions.get(symbol, {"amount": 0.0, "entry_price": 0.0, "margin": 0.0})
        # 估算未实现盈亏
        amount = pos["amount"]
        entry = pos["entry_price"]
        current = self.current_price
        unrealized_pnl = 0.0
        if amount != 0:
            if amount > 0:
                unrealized_pnl = (current - entry) * amount
            else:
                unrealized_pnl = (entry - current) * abs(amount)
        
        return {
            "amount": amount,
            "entryPrice": entry,
            "margin": pos["margin"],
            "unrealizedPnL": unrealized_pnl,
            "leverage": self.leverage
        }

    def get_account_balance(self, asset: str) -> float:
        """
        获取账户余额
        USDT: 返回 钱包余额 + 未实现盈亏 (Equity) ? 还是仅 Wallet Balance?
        通常 API get_account_balance 返回的是 Wallet Balance.
        但交易决策通常看 Equity.
        """
        if asset == "USDT":
            # 计算总权益 Equity = Balance + Unrealized PnL
            total_unrealized_pnl = 0.0
            for symbol, pos in self.positions.items():
                p = self.get_position(symbol)
                total_unrealized_pnl += p["unrealizedPnL"]
            return self.balance + total_unrealized_pnl
            
        return 0.0
