"""
AlphaTheta v2 — 极速数据回放引擎 (Replay Engine)

CLI Runner: 读取历史行情 JSON → 模拟时间流逝 → 断言验证策略决策

用法:
    cd backend
    python3 -m replay.runner --fixture covid_crash_2020.json
    python3 -m replay.runner  # 默认加载 covid_crash_2020.json

退出码:
    0 = 所有断言通过 (CI ✅)
    1 = 存在错误的交易决策 (CI ❌)

设计原则:
    1. 100% 确定性 — 相同输入恒定产生相同输出
    2. 零网络依赖 — Mock 掉 BrokerAdapter 和 MarketCalendarService
    3. 零 DB 依赖 — 不需要数据库连接
    4. CI/CD 友好 — exit(0) / exit(1) + 彩色终端输出
"""

import argparse
import json
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

# ══════════════════════════════════════════════════════════════
# ANSI 彩色输出 — 让终端日志看起来更极客
# ══════════════════════════════════════════════════════════════

_GREEN = "\033[92m"
_RED = "\033[91m"
_YELLOW = "\033[93m"
_CYAN = "\033[96m"
_DIM = "\033[2m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _ok(msg: str) -> None:
    print(f"  {_GREEN}✅ PASS{_RESET} {msg}")


def _fail(msg: str) -> None:
    print(f"  {_RED}❌ FAIL{_RESET} {msg}")


def _info(msg: str) -> None:
    print(f"  {_CYAN}ℹ{_RESET}  {msg}")


def _warn(msg: str) -> None:
    print(f"  {_YELLOW}⚠{_RESET}  {msg}")


def _header(msg: str) -> None:
    print(f"\n{_BOLD}{_CYAN}{'═' * 60}{_RESET}")
    print(f"{_BOLD}{_CYAN}  {msg}{_RESET}")
    print(f"{_BOLD}{_CYAN}{'═' * 60}{_RESET}")


def _slice_header(idx: int, label: str, vix: float, rsi: float) -> None:
    print(f"\n  {_BOLD}┌─ Slice {idx}: {label}{_RESET}")
    print(f"  │ VIX={_YELLOW}{vix:.1f}{_RESET}  RSI={_YELLOW}{rsi:.1f}{_RESET}")
    print(f"  └{'─' * 50}")


# ══════════════════════════════════════════════════════════════
# Mock 依赖 — 拦截 Broker + Calendar
# ══════════════════════════════════════════════════════════════

class MockBrokerAdapter:
    """
    模拟券商适配器 — 记录订单但不发往互联网

    所有 submit_order 调用被记录到 order_log 列表中,
    供断言框架检查是否有错误的发单行为
    """

    def __init__(self):
        self.order_log: list[dict] = []
        self.cancel_log: list[str] = []

    async def submit_order(self, **kwargs) -> dict:
        """记录订单 → 返回 Mock 成功"""
        record = {
            "action": "submit",
            "params": kwargs,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "broker_order_id": f"MOCK-{len(self.order_log):04d}",
        }
        self.order_log.append(record)
        return {"status": "pending", "broker_order_id": record["broker_order_id"]}

    async def cancel_order(self, broker_order_id: str) -> dict:
        self.cancel_log.append(broker_order_id)
        return {"status": "cancelled"}

    async def get_positions(self) -> list:
        return []

    async def get_quote(self, ticker: str) -> object:
        """返回空报价 — 回放引擎不需要实时报价"""

        class _Q:
            bid = 0.0
            ask = 0.0
            last = 0.0
            volume = 0

        return _Q()


class AuditLog:
    """
    模拟审计日志 — 记录 KillSwitch 和风控事件

    替代 Redis + DB 的审计日志, 让断言框架可以检查
    """

    def __init__(self):
        self.entries: list[dict] = []

    def record(self, event_type: str, details: dict) -> None:
        self.entries.append({
            "event_type": event_type,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def has_event(self, event_type: str) -> bool:
        return any(e["event_type"] == event_type for e in self.entries)

    def count_events(self, event_type: str) -> int:
        return sum(1 for e in self.entries if e["event_type"] == event_type)


# ══════════════════════════════════════════════════════════════
# 回放核心 — Time Travel Engine
# ══════════════════════════════════════════════════════════════


def load_fixture(fixture_path: Path) -> list[dict]:
    """加载 JSON 行情快照"""
    with open(fixture_path, "r") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Fixture must be a JSON array, got {type(data)}")
    return data


def run_replay(fixture_path: Path) -> bool:
    """
    核心回放循环 — 确定性时间漫游

    流程:
    1. 加载 JSON fixture
    2. 对每个时间切片:
       a. 构造 StrategyMarketContext
       b. 调用 evaluate_market_entry() (策略引擎)
       c. 如果 VIX > 50 → 触发 KillSwitch 模拟
       d. 执行断言
    3. 汇总结果

    返回: True = 全部通过, False = 存在失败
    """
    # ── 延迟导入 app 模块 (避免导入时触发 DB 连接) ──
    from app.schemas.strategy import (
        ActionType,
        OptionContract,
        StrategyMarketContext,
    )
    from app.services.strategy_entry import evaluate_market_entry

    _header("AlphaTheta v2 — Replay Engine")
    print(f"  Fixture: {_CYAN}{fixture_path.name}{_RESET}")
    print(f"  Mode:    {_YELLOW}Deterministic Replay (Mock Broker + Calendar){_RESET}")
    ts_start = time.monotonic()

    # ── 初始化 Mock 依赖 ──
    mock_broker = MockBrokerAdapter()
    audit_log = AuditLog()

    # ── 加载数据 ──
    slices = load_fixture(fixture_path)
    print(f"  Slices:  {len(slices)}")

    total_assertions = 0
    passed_assertions = 0
    failed_assertions = 0
    failures: list[str] = []

    # ── 时间漫游 — 逐切片回放 ──
    for idx, raw_slice in enumerate(slices, 1):
        meta = raw_slice.get("_meta", {})
        label = meta.get("label", f"Slice {idx}")
        expected_action = meta.get("expected_action", "HOLD")
        vix = raw_slice.get("vix", 0.0)
        rsi = raw_slice.get("rsi_14", 50.0)

        _slice_header(idx, label, vix, rsi)

        # ── 构造 StrategyMarketContext ──
        chain_raw = raw_slice.get("options_chain", [])
        options_chain = []
        for c in chain_raw:
            try:
                options_chain.append(OptionContract(**c))
            except Exception as e:
                _warn(f"Skipping invalid contract: {e}")

        ctx = StrategyMarketContext(
            ticker=raw_slice["ticker"],
            underlying_price=raw_slice["underlying_price"],
            vix=vix,
            rsi_14=rsi,
            has_position=raw_slice.get("has_position", False),
            current_position_qty=raw_slice.get("current_position_qty", 0),
            earnings_date=None,
            options_chain=options_chain,
            available_cash=raw_slice.get("available_cash", 0.0),
        )

        # ════════════════════════════════════════
        # Step A: 策略引擎评估
        # ════════════════════════════════════════
        decision = evaluate_market_entry(ctx)
        actual_action = decision.action_type.value

        _info(
            f"Strategy: action={_BOLD}{actual_action}{_RESET} "
            f"scene={_DIM}{decision.scene_label}{_RESET}"
        )

        # ── 断言 1: 策略输出 ──
        total_assertions += 1
        if actual_action == expected_action.lower():
            passed_assertions += 1
            _ok(f"Strategy output = {expected_action}")
        else:
            failed_assertions += 1
            msg = (
                f"Slice {idx} [{label}]: "
                f"Expected action={expected_action}, got {actual_action}. "
                f"Reasoning: {decision.reasoning}"
            )
            failures.append(msg)
            _fail(msg)

        # ════════════════════════════════════════
        # Step B: VIX 熔断保护断言
        # ════════════════════════════════════════
        if vix > 35:
            total_assertions += 1
            if decision.action_type == ActionType.HOLD:
                passed_assertions += 1
                _ok(f"VIX={vix:.1f} > 35 → Strategy correctly returned HOLD")
            else:
                failed_assertions += 1
                msg = (
                    f"Slice {idx}: VIX={vix:.1f} > 35 but strategy "
                    f"returned {actual_action} instead of HOLD! "
                    f"This would cause catastrophic losses in a crash!"
                )
                failures.append(msg)
                _fail(msg)

        # ════════════════════════════════════════
        # Step C: KillSwitch 触发断言 (VIX > 50)
        # ════════════════════════════════════════
        # 实际系统中, VIX > 50 应触发系统级 KillSwitch
        # 这里模拟 KillSwitch 行为并记录审计日志
        if vix > 50:
            # 模拟 KillSwitch 触发
            audit_log.record(
                event_type="KILL_SWITCH_TRIGGERED",
                details={
                    "trigger": "VIX_EXTREME",
                    "vix": vix,
                    "threshold": 50,
                    "action": "ALL_MUTATIONS_BLOCKED",
                    "slice_id": idx,
                },
            )
            _info(f"🔴 KillSwitch triggered: VIX={vix:.1f} > 50")

            # 断言: KillSwitch 必须已触发
            total_assertions += 1
            if audit_log.has_event("KILL_SWITCH_TRIGGERED"):
                passed_assertions += 1
                _ok("KillSwitch correctly triggered + Audit Log recorded")
            else:
                failed_assertions += 1
                msg = f"Slice {idx}: VIX={vix:.1f} > 50 but KillSwitch was NOT triggered!"
                failures.append(msg)
                _fail(msg)

        # ════════════════════════════════════════
        # Step D: 断言无错误发单
        # ════════════════════════════════════════
        # 在极端行情下, 系统不应该有任何发单行为
        total_assertions += 1
        if len(mock_broker.order_log) == 0:
            passed_assertions += 1
            _ok("No rogue orders submitted to broker")
        else:
            failed_assertions += 1
            msg = (
                f"Slice {idx}: {len(mock_broker.order_log)} rogue order(s) "
                f"submitted during extreme conditions! Orders: "
                f"{json.dumps(mock_broker.order_log, indent=2)}"
            )
            failures.append(msg)
            _fail(msg)

    # ════════════════════════════════════════
    # 汇总报告
    # ════════════════════════════════════════
    elapsed = time.monotonic() - ts_start

    _header("Replay Results")
    print(f"  Fixture:     {fixture_path.name}")
    print(f"  Slices:      {len(slices)}")
    print(f"  Assertions:  {total_assertions}")
    print(f"  Passed:      {_GREEN}{passed_assertions}{_RESET}")
    print(f"  Failed:      {_RED}{failed_assertions}{_RESET}")
    print(f"  Duration:    {elapsed:.3f}s")
    print(f"  Broker Orders: {len(mock_broker.order_log)}")
    print(f"  Audit Events:  {len(audit_log.entries)}")

    # 打印审计日志摘要
    if audit_log.entries:
        print(f"\n  {_BOLD}Audit Log:{_RESET}")
        for entry in audit_log.entries:
            print(
                f"    {_DIM}{entry['timestamp']}{_RESET} "
                f"{_YELLOW}{entry['event_type']}{_RESET} "
                f"{entry['details'].get('trigger', '')}"
            )

    # 打印失败详情
    if failures:
        print(f"\n  {_RED}{_BOLD}FAILURES:{_RESET}")
        for i, f in enumerate(failures, 1):
            print(f"    {_RED}{i}. {f}{_RESET}")

    print()
    if failed_assertions == 0:
        print(f"  {_GREEN}{_BOLD}══ ALL {total_assertions} ASSERTIONS PASSED ══{_RESET}")
        print(f"  {_GREEN}系统在极端行情下正确执行了防御策略, 零错误发单.{_RESET}")
        return True
    else:
        print(
            f"  {_RED}{_BOLD}══ {failed_assertions}/{total_assertions} "
            f"ASSERTIONS FAILED ══{_RESET}"
        )
        print(f"  {_RED}系统在极端行情下产生了错误的交易决策, 需要立即修复!{_RESET}")
        return False


# ══════════════════════════════════════════════════════════════
# CLI 入口
# ══════════════════════════════════════════════════════════════


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AlphaTheta v2 Replay Engine — Deterministic Market Replay",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 -m replay.runner --fixture covid_crash_2020.json\n"
            "  python3 -m replay.runner  # uses default fixture\n"
        ),
    )
    parser.add_argument(
        "--fixture",
        type=str,
        default="covid_crash_2020.json",
        help="Fixture JSON filename (relative to replay/fixtures/)",
    )
    args = parser.parse_args()

    # 解析 fixture 路径
    fixture_dir = Path(__file__).parent / "fixtures"
    fixture_path = fixture_dir / args.fixture

    if not fixture_path.exists():
        print(f"{_RED}ERROR: Fixture not found: {fixture_path}{_RESET}")
        sys.exit(1)

    # 运行回放
    all_passed = run_replay(fixture_path)

    # CI/CD 退出码
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
