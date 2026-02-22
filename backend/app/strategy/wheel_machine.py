"""
车轮策略状态机 (The Wheel FSM) — 期权卖方全生命周期管理

The Wheel 策略流程:
┌─────────────────┐    Sell Put     ┌──────────────┐
│ SEARCHING_PUT   │ ─────────────→ │ HOLDING_PUT  │
│ (寻找卖 Put)    │                │ (持有空Put)   │
└─────────────────┘                └──────┬───────┘
                                          │ Assigned (被指派)
                                          │ → 被迫以 Strike 价买入 100 股
                                          ▼
┌─────────────────────┐            ┌──────────────┐
│ HOLDING_COVERED_CALL│ ←───────── │ HOLDING_STOCK│
│ (持有备兑看涨)       │  Sell Call │ (持有正股)     │
└──────────┬──────────┘            └──────────────┘
           │ Assigned / Expired
           │ → 正股被 Call 走 或 期权到期
           ▼
┌─────────────────┐
│ SEARCHING_PUT   │ ← 循环回到起点
└─────────────────┘

设计要点:
1. 每个 Ticker 独立维护一个 FSM 实例
2. 状态转换严格校验 — 非法转换直接拒绝
3. 每次转换记录审计日志
4. 前端可通过 API 获取当前状态用于渲染
"""

import logging
from datetime import datetime, timezone
from enum import StrEnum

logger = logging.getLogger("alphatheta.wheel_fsm")


class WheelState(StrEnum):
    """车轮策略状态枚举"""
    SEARCHING_PUT = "searching_put"           # 寻找 Sell Put 机会
    HOLDING_PUT = "holding_put"               # 已卖出 Put, 等待到期或被指派
    HOLDING_STOCK = "holding_stock"           # 被指派后持有正股
    HOLDING_COVERED_CALL = "holding_call"     # 已卖出备兑 Call, 等待到期或被 call 走


class WheelEvent(StrEnum):
    """触发状态转换的事件"""
    PUT_SOLD = "put_sold"                     # Put 卖出成交
    PUT_EXPIRED = "put_expired"               # Put 到期作废 (OTM, 保留权利金)
    PUT_ASSIGNED = "put_assigned"             # Put 被指派 (ITM, 被迫买入正股)
    CALL_SOLD = "call_sold"                   # 备兑 Call 卖出成交
    CALL_EXPIRED = "call_expired"             # Call 到期作废 (OTM, 保留正股+权利金)
    CALL_ASSIGNED = "call_assigned"           # Call 被指派 (ITM, 正股被 call 走)
    MANUAL_EXIT = "manual_exit"               # 手动平仓退出


# ── 合法的状态转换矩阵 ──
# key = (当前状态, 事件) → value = 目标状态
_TRANSITION_TABLE: dict[tuple[WheelState, WheelEvent], WheelState] = {
    # 从 SEARCHING_PUT 开始
    (WheelState.SEARCHING_PUT, WheelEvent.PUT_SOLD): WheelState.HOLDING_PUT,

    # HOLDING_PUT 的可能出路
    (WheelState.HOLDING_PUT, WheelEvent.PUT_EXPIRED): WheelState.SEARCHING_PUT,      # OTM 到期 → 重新找机会
    (WheelState.HOLDING_PUT, WheelEvent.PUT_ASSIGNED): WheelState.HOLDING_STOCK,     # ITM 被指派 → 接货

    # HOLDING_STOCK: 卖出备兑 Call
    (WheelState.HOLDING_STOCK, WheelEvent.CALL_SOLD): WheelState.HOLDING_COVERED_CALL,

    # HOLDING_COVERED_CALL 的可能出路
    (WheelState.HOLDING_COVERED_CALL, WheelEvent.CALL_EXPIRED): WheelState.HOLDING_STOCK,      # OTM 到期 → 继续持股, 再卖 Call
    (WheelState.HOLDING_COVERED_CALL, WheelEvent.CALL_ASSIGNED): WheelState.SEARCHING_PUT,     # ITM 被 call 走 → 循环回到起点

    # 任意状态可手动退出
    (WheelState.SEARCHING_PUT, WheelEvent.MANUAL_EXIT): WheelState.SEARCHING_PUT,
    (WheelState.HOLDING_PUT, WheelEvent.MANUAL_EXIT): WheelState.SEARCHING_PUT,
    (WheelState.HOLDING_STOCK, WheelEvent.MANUAL_EXIT): WheelState.SEARCHING_PUT,
    (WheelState.HOLDING_COVERED_CALL, WheelEvent.MANUAL_EXIT): WheelState.SEARCHING_PUT,
}


class WheelMachine:
    """
    车轮策略有限状态机 — 每个 Ticker 一个实例

    使用:
        wheel = WheelMachine("SPY")
        wheel.advance(WheelEvent.PUT_SOLD, details={"strike": 505, "premium": 3.80})
        wheel.advance(WheelEvent.PUT_ASSIGNED, details={"cost_basis": 501.20})
        # → 自动切换到 HOLDING_STOCK, 并生成 Sell Call 指令
    """

    def __init__(self, ticker: str, initial_state: WheelState = WheelState.SEARCHING_PUT):
        self.ticker = ticker
        self.state = initial_state
        self.cost_basis: float | None = None     # 正股成本价 (被指派后设定)
        self.premium_collected: float = 0.0       # 累计收取的权利金
        self.cycle_count: int = 0                 # 完成的车轮循环次数
        self.history: list[dict] = []             # 状态转换审计日志
        self.pending_action: dict | None = None   # 下一步应执行的操作指令

    def advance(self, event: WheelEvent, details: dict | None = None) -> dict:
        """
        推进状态机 — 核心转换方法

        参数:
            event: 触发事件
            details: 事件附加信息 (如 strike, premium, cost_basis)

        返回:
            dict — 包含新状态 + 建议操作指令

        异常:
            ValueError — 非法的状态转换
        """
        details = details or {}
        old_state = self.state
        transition_key = (self.state, event)

        if transition_key not in _TRANSITION_TABLE:
            raise ValueError(
                f"非法状态转换: {self.state.value} + {event.value} → ??? "
                f"(Ticker: {self.ticker})"
            )

        new_state = _TRANSITION_TABLE[transition_key]
        self.state = new_state

        # ── 记录审计日志 ──
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "from_state": old_state.value,
            "event": event.value,
            "to_state": new_state.value,
            "details": details,
        }
        self.history.append(log_entry)
        logger.info(
            f"[Wheel/{self.ticker}] {old_state.value} --({event.value})--> {new_state.value}"
        )

        # ── 副作用: 根据转换生成操作指令 ──
        self.pending_action = None

        if event == WheelEvent.PUT_SOLD:
            premium = details.get("premium", 0)
            self.premium_collected += premium

        elif event == WheelEvent.PUT_ASSIGNED:
            # 被指派: 记录成本价, 立即生成 Sell Call 指令
            self.cost_basis = details.get("cost_basis", details.get("strike", 0))
            self.pending_action = {
                "action": "SELL_COVERED_CALL",
                "ticker": self.ticker,
                "instruction": (
                    f"以成本价 ${self.cost_basis:.2f} 为基准, "
                    f"卖出 OTM Call (Delta 0.20-0.30, DTE 30-45)"
                ),
                "cost_basis": self.cost_basis,
            }
            logger.info(
                f"[Wheel/{self.ticker}] Assigned at ${self.cost_basis:.2f} "
                f"→ Generate Sell Call instruction"
            )

        elif event == WheelEvent.CALL_SOLD:
            premium = details.get("premium", 0)
            self.premium_collected += premium

        elif event == WheelEvent.CALL_ASSIGNED:
            # 正股被 call 走 → 一轮车轮完成
            self.cycle_count += 1
            self.cost_basis = None
            self.pending_action = {
                "action": "CYCLE_COMPLETE",
                "ticker": self.ticker,
                "instruction": "车轮循环完成, 可重新开始 Sell Put",
                "total_premium": self.premium_collected,
                "cycle_count": self.cycle_count,
            }
            logger.info(
                f"[Wheel/{self.ticker}] Wheel cycle #{self.cycle_count} complete! "
                f"Total premium: ${self.premium_collected:.2f}"
            )

        elif event == WheelEvent.CALL_EXPIRED:
            # Call 到期作废 → 继续持股, 再卖 Call
            premium = details.get("premium", 0)
            self.premium_collected += premium
            self.pending_action = {
                "action": "SELL_COVERED_CALL",
                "ticker": self.ticker,
                "instruction": (
                    f"Call 到期作废 (保留权利金 ${premium:.2f}). "
                    f"以成本价 ${self.cost_basis:.2f} 为基准, 继续卖出备兑 Call"
                ),
                "cost_basis": self.cost_basis,
            }

        elif event == WheelEvent.PUT_EXPIRED:
            # Put 到期作废 → 保留权利金, 重新找机会
            premium = details.get("premium", 0)
            self.premium_collected += premium

        return {
            "ticker": self.ticker,
            "old_state": old_state.value,
            "new_state": new_state.value,
            "event": event.value,
            "pending_action": self.pending_action,
            "premium_collected": self.premium_collected,
            "cycle_count": self.cycle_count,
        }

    def get_status(self) -> dict:
        """获取当前 FSM 状态 — 供前端渲染"""
        return {
            "ticker": self.ticker,
            "state": self.state.value,
            "cost_basis": self.cost_basis,
            "premium_collected": round(self.premium_collected, 2),
            "cycle_count": self.cycle_count,
            "pending_action": self.pending_action,
            "history_count": len(self.history),
        }


# ── 全局 FSM 注册表 ──
# key = ticker, value = WheelMachine instance
_wheel_registry: dict[str, WheelMachine] = {}


def get_wheel(ticker: str) -> WheelMachine:
    """获取或创建某个标的的车轮 FSM"""
    if ticker not in _wheel_registry:
        _wheel_registry[ticker] = WheelMachine(ticker)
    return _wheel_registry[ticker]


def get_all_wheels() -> list[dict]:
    """获取所有活跃的车轮 FSM 状态 — 供前端"全程跟踪"视图"""
    return [w.get_status() for w in _wheel_registry.values()]
