// ══════════════════════════════════════════════════════════════════
// AlphaTheta v2 — Strategy Templates (策略模板 JSON)
// ══════════════════════════════════════════════════════════════════
//
// 模板设计原则:
//   1. 废弃 strikeOffset (绝对数值偏移) → 改用 strikeStep (档位偏移)
//   2. 新增 dteOffset (天数偏移) → 支持跨期策略 (Calendar Spread)
//   3. 所有行权价通过 snapToStrike() 在运行时从离散期权链中吸附
//
// strikeStep 语义:
//   0  = ATM (最接近现价的行权价)
//  +N  = ATM 上方第 N 档 (OTM Call 方向)
//  -N  = ATM 下方第 N 档 (OTM Put 方向)
//
// dteOffset 语义:
//   0  = 使用基准到期日 (近端腿)
//  +N  = 基准到期日 + N 天 (远端腿)
// ══════════════════════════════════════════════════════════════════

export const STRATEGY_TEMPLATES = [
    // ── 1. Buy-Write (备兑策略) ──────────────────────────────────
    // 持有正股 + 卖出 OTM Covered Call
    // 收入: Call 权利金 (降低持仓成本)
    // 风险: 正股大涨时利润被 cap 住
    {
        id: "buy-write",
        name: "Buy-Write (备兑策略)",
        description: "持有 100 股正股 + 卖出 1 份 OTM Covered Call，收取权利金降低成本基础",
        legs: [
            { type: "stock", right: null, action: "buy", strikeStep: 0, dteOffset: 0, qty: 100 },
            { type: "option", right: "call", action: "sell", strikeStep: +2, dteOffset: 0, qty: 1 },
        ],
    },

    // ── 2. Cash-Secured Put (现金担保看跌) ──────────────────────
    // 裸卖 ATM-1 Put，用现金担保
    // 收入: Put 权利金
    // 风险: 标的暴跌时被迫接盘
    {
        id: "cash-secured-put",
        name: "Cash-Secured Put (现金担保看跌)",
        description: "卖出 1 份 OTM Put，以现金担保行权风险",
        legs: [
            { type: "option", right: "put", action: "sell", strikeStep: -1, dteOffset: 0, qty: 1 },
        ],
    },

    // ── 3. Bull Put Spread (牛市看跌价差) ──────────────────────
    // 卖 OTM Put + 买更深 OTM Put (风险对冲)
    // 有限收益 + 有限风险
    {
        id: "bull-put-spread",
        name: "Bull Put Spread (牛市看跌价差)",
        description: "卖出近价 Put + 买入远价 Put，净收取权利金，有限风险",
        legs: [
            { type: "option", right: "put", action: "sell", strikeStep: -1, dteOffset: 0, qty: 1 },
            { type: "option", right: "put", action: "buy", strikeStep: -3, dteOffset: 0, qty: 1 },
        ],
    },

    // ── 4. Iron Condor (铁鹰式) ────────────────────────────────
    // 同时卖出 OTM Call + OTM Put，各自用更远 OTM 腿对冲
    // 4 腿组合: 市场中性，赚取时间价值衰减
    // Max Profit = 净收取权利金 (有限)
    // Max Loss   = 翅膀宽度 - 净权利金 (有限)
    {
        id: "iron-condor",
        name: "Iron Condor (铁鹰式)",
        description: "同时卖出 OTM Call 和 OTM Put，各有一腿保护，市场中性策略",
        legs: [
            { type: "option", right: "put", action: "buy", strikeStep: -4, dteOffset: 0, qty: 1 },
            { type: "option", right: "put", action: "sell", strikeStep: -2, dteOffset: 0, qty: 1 },
            { type: "option", right: "call", action: "sell", strikeStep: +2, dteOffset: 0, qty: 1 },
            { type: "option", right: "call", action: "buy", strikeStep: +4, dteOffset: 0, qty: 1 },
        ],
    },

    // ── 5. Long Straddle (买入跨式) ────────────────────────────
    // ATM 同时买 Call + Put → 赌大波动
    // Max Loss = 总权利金 (有限)
    // Max Profit = 无限 (标的双向大幅移动)
    {
        id: "long-straddle",
        name: "Long Straddle (买入跨式)",
        description: "同时买入 ATM Call 和 ATM Put，赌标的大幅波动",
        legs: [
            { type: "option", right: "call", action: "buy", strikeStep: 0, dteOffset: 0, qty: 1 },
            { type: "option", right: "put", action: "buy", strikeStep: 0, dteOffset: 0, qty: 1 },
        ],
    },

    // ── 6. Calendar Spread (日历价差 / 跨期策略) ────────────────
    // 卖近端 + 买远端同行权价期权
    // 利用近端 Theta 快速衰减 vs 远端 Theta 慢降
    // ⚠ dteOffset 非零：这是跨期策略的关键区分
    {
        id: "calendar-spread-put",
        name: "Calendar Spread - Put (日历看跌价差)",
        description: "卖出近端 ATM Put + 买入远端 ATM Put，赚取 Theta 衰减差",
        legs: [
            { type: "option", right: "put", action: "sell", strikeStep: 0, dteOffset: 0, qty: 1 },
            { type: "option", right: "put", action: "buy", strikeStep: 0, dteOffset: 30, qty: 1 },
        ],
    },

    // ── 7. Calendar Spread (Call 版) ────────────────────────────
    {
        id: "calendar-spread-call",
        name: "Calendar Spread - Call (日历看涨价差)",
        description: "卖出近端 ATM Call + 买入远端 ATM Call，赚取 Theta 衰减差",
        legs: [
            { type: "option", right: "call", action: "sell", strikeStep: 0, dteOffset: 0, qty: 1 },
            { type: "option", right: "call", action: "buy", strikeStep: 0, dteOffset: 30, qty: 1 },
        ],
    },

    // ── 8. Diagonal Spread (对角价差) ──────────────────────────
    // Calendar + Strike shift: 卖近端 OTM + 买远端 ATM
    {
        id: "diagonal-spread",
        name: "Diagonal Spread (对角价差)",
        description: "卖出近端 OTM Call + 买入远端 ATM Call，同时利用 Strike 和 DTE 差异",
        legs: [
            { type: "option", right: "call", action: "sell", strikeStep: +2, dteOffset: 0, qty: 1 },
            { type: "option", right: "call", action: "buy", strikeStep: 0, dteOffset: 30, qty: 1 },
        ],
    },

    // ── 9. Protective Put (保护性看跌) ────────────────────────
    {
        id: "protective-put",
        name: "Protective Put (保护性看跌)",
        description: "持有正股 + 买入 OTM Put 作为下行保险",
        legs: [
            { type: "stock", right: null, action: "buy", strikeStep: 0, dteOffset: 0, qty: 100 },
            { type: "option", right: "put", action: "buy", strikeStep: -2, dteOffset: 0, qty: 1 },
        ],
    },
];

export default STRATEGY_TEMPLATES;
