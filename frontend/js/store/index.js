// ══════════════════════════════════════════════════════════════════
// AlphaTheta v2 — Store (Pub/Sub State Machine)
// ══════════════════════════════════════════════════════════════════
// 
// 轻量级响应式状态管理器，使用 Proxy 拦截 set 操作。
// 任何视图通过 subscribe(key, callback) 订阅状态变化，
// setState(key, value) 触发所有订阅者。
//
// 防坑:
// 1. 每个 subscriber 回调在 try/catch 中执行 — 单点异常不传播
// 2. subscribe() 返回 unsubscribe 函数 — 防止视图销毁后内存泄漏
// 3. Proxy set trap 只在值真正变化时触发 — 避免无意义的重渲染
// ══════════════════════════════════════════════════════════════════

/** @type {Map<string, Set<Function>>} 订阅表 */
const _listeners = new Map();

/** 初始状态 — 从 sessionStorage 恢复持久化字段 */
const _rawState = {
    activeTicker: sessionStorage.getItem("globalActiveTicker") || "SPY",
    activeTab: "dashboard",
    lang: "zh",
    isHalted: false,
    isAutoTrading: false,
    theme: "dark",
};

/**
 * 通知所有订阅了 key 的回调
 * @param {string} key
 * @param {*} value
 */
function _notify(key, value) {
    const subs = _listeners.get(key);
    if (!subs || subs.size === 0) return;
    for (const fn of subs) {
        try {
            fn(value, key);
        } catch (err) {
            console.error(`[Store] Subscriber error on "${key}":`, err);
        }
    }
}

/**
 * Proxy-based 响应式状态
 * set trap: 值变化时触发订阅者 + 持久化特定字段
 */
const state = new Proxy(_rawState, {
    set(target, key, value) {
        const oldValue = target[key];
        if (oldValue === value) return true; // 值未变化, 跳过
        target[key] = value;

        // 持久化特定字段到 sessionStorage
        if (key === "activeTicker") {
            sessionStorage.setItem("globalActiveTicker", value);
        }

        _notify(key, value);
        return true;
    },

    get(target, key) {
        return target[key];
    },
});

// ── Public API ──────────────────────────────────────────────────

/**
 * 获取状态值
 * @param {string} [key] — 不传则返回整个 state 快照
 * @returns {*}
 */
export function getState(key) {
    if (key === undefined) return { ..._rawState };
    return state[key];
}

/**
 * 设置状态 — 触发所有该 key 的订阅者
 * @param {string} key
 * @param {*} value
 */
export function setState(key, value) {
    state[key] = value; // Proxy set trap 处理通知
}

/**
 * 订阅状态变化
 * @param {string} key
 * @param {Function} callback — (newValue, key) => void
 * @returns {Function} unsubscribe — 调用后取消订阅
 */
export function subscribe(key, callback) {
    if (!_listeners.has(key)) {
        _listeners.set(key, new Set());
    }
    _listeners.get(key).add(callback);

    // 返回取消订阅函数
    return () => {
        const subs = _listeners.get(key);
        if (subs) {
            subs.delete(callback);
            if (subs.size === 0) _listeners.delete(key);
        }
    };
}

// ── i18n Dictionary ─────────────────────────────────────────────
// 从 app.js 迁移，供 t() 翻译函数使用

export const I18N = {
    zh: {
        nav_status_synced: "数据已同步",
        nav_dashboard: "大盘概览",
        nav_signal: "信号与执行",
        nav_sandbox: "策略沙盒",
        nav_tracking: "全程跟踪与报告",
        nav_settings: "系统设置",
        kill_switch: "紧急暂停",
        halt_msg: "交易引擎已暂停",
        portfolio_net: "账户总净值",
        portfolio_cash: "可用购买力",
        margin_util: "保证金使用率",
        radar_vix: "恐慌指数与波动率",
        radar_spy: "标普500 状态",
        radar_qqq: "纳指100 状态",
        pos_title: "活跃持仓",
        pos_col_ticker: "标的",
        pos_col_type: "类型",
        pos_col_strike: "行权价",
        pos_col_expiry: "到期日",
        pos_col_dte: "DTE",
        pos_col_premium: "初始权利金",
        pos_col_current: "当前价值",
        pos_col_pnl: "盈亏 %",
        pos_col_actions: "操作",
        report_title: "运营报告",
        report_saved_ops: "自动化操作",
        report_premium: "累计权利金",
        sandbox_title: "策略沙盒",
        sandbox_strategy: "策略",
        sandbox_underlying: "标的",
        sandbox_strike: "行权价",
        sandbox_premium: "权利金",
        sandbox_net_cost: "净成本",
        sandbox_breakeven: "盈亏平衡点",
        sandbox_max_profit: "最大利润",
        sandbox_annualized: "年化收益率",
        settings_api: "API 密钥保险箱",
        settings_permission: "读写模式",
        terminal_title: "系统健康终端",
    },
    en: {
        nav_status_synced: "Data Synced",
        nav_dashboard: "Dashboard",
        nav_signal: "Signal & Execution",
        nav_sandbox: "Strategy Sandbox",
        nav_tracking: "Lifecycle Tracking",
        nav_settings: "System Settings",
        kill_switch: "Kill Switch",
        halt_msg: "Trading Engine Halted",
        portfolio_net: "Total Equity",
        portfolio_cash: "Buying Power",
        margin_util: "Margin Utilization",
        radar_vix: "VIX & Volatility",
        radar_spy: "S&P 500 Status",
        radar_qqq: "Nasdaq 100 Status",
        pos_title: "Active Positions",
        pos_col_ticker: "Ticker",
        pos_col_type: "Type",
        pos_col_strike: "Strike",
        pos_col_expiry: "Expiry",
        pos_col_dte: "DTE",
        pos_col_premium: "Initial Premium",
        pos_col_current: "Current Value",
        pos_col_pnl: "P&L %",
        pos_col_actions: "Actions",
        report_title: "Operations Report",
        report_saved_ops: "Automated Ops",
        report_premium: "Total Premium",
        sandbox_title: "Strategy Sandbox",
        sandbox_strategy: "Strategy",
        sandbox_underlying: "Underlying",
        sandbox_strike: "Strike",
        sandbox_premium: "Premium",
        sandbox_net_cost: "Net Cost",
        sandbox_breakeven: "Break-Even",
        sandbox_max_profit: "Max Profit",
        sandbox_annualized: "Annualized Return",
        settings_api: "API Key Vault",
        settings_permission: "Read/Write Mode",
        terminal_title: "System Health Terminal",
    },
};

/**
 * 翻译函数
 * @param {string} key
 * @returns {string}
 */
export function t(key) {
    const dict = I18N[state.lang];
    return dict?.[key] || I18N.en?.[key] || key;
}

// ── MOCK_DATA 兼容层 ────────────────────────────────────────────
// 过渡期: 尚未迁移到 API 的视图仍可引用此数据
// 最终目标: 各 view 从 API 获取数据后逐步删除

export const MOCK_DATA = {
    // ── $100,000 初始空仓状态 ──
    // API 返回真实数据后会覆盖这些默认值
    portfolio: { totalValue: 100000, cash: 100000, marginUsed: 0 },
    radar: {
        vix: 0,
        ivRank: { qqq: 0, spy: 0 },
        spy: { price: 0, sma200: 0, trend: "--" },
        qqq: { price: 0, sma200: 0, trend: "--" },
    },
    currentSignal: {
        actionType: "",
        action: "等待扫描引擎信号...",
        ticker: "--",
        strike: 0,
        limitPrice: 0,
        expiration: "--",
        quantity: "--",
        capitalImpact: "$0.00",
        isBuy: false,
        dte: 0,
        actionTypeSell: false,
        rationale: ["全天候扫描引擎运行中，等待 LEAPS 黄金坑信号..."],
    },
    activePositions: [],
    tracking: { automatedOps: 0, totalPremiumCollected: 0 },
    systemLogs: [
        "[System] AlphaTheta v2 初始化完成",
        "[Engine] 扫描引擎已启动，监控核心票池",
        "[Portfolio] 初始资金 $100,000 已就绪",
    ],
    hud: {
        marginUtilization: 0,
        netSpyDelta: 0,
        netTheta: 0,
    },
    botTelemetry: {
        status: "scanning",
        todayOrders: 0,
        apiLatencyMs: 0,
    },
    perfMetrics: {
        winRate: 0,
        maxDrawdown: 0,
        profitFactor: 0,
        sharpeRatio: 0,
        totalTrades: 0,  // 用于 N/A 判断
    },
    equityCurve: [100000],
    marketContext: null,
};

// ── Convenience: direct state reference (for legacy compat) ─────

export { state };
export default { getState, setState, subscribe, state, t, I18N, MOCK_DATA };
