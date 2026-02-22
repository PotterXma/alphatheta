// ══════════════════════════════════════════════════════════════════
// AlphaTheta v2 — Paper Trade Engine (模拟盘结算)
// ══════════════════════════════════════════════════════════════════
//
// executePaperTrade(legs) → 扣减 cash → push positions → update HUD
//
// ⚠ 乘数陷阱防护:
//   - 期权 (Call/Put): cost = price × quantity × 100
//   - 正股 (Stock):    cost = price × quantity × 1
// ══════════════════════════════════════════════════════════════════

import { MOCK_DATA } from "../store/index.js";

/**
 * 按腿类型返回正确乘数
 * @param {Object} leg
 * @returns {number}
 */
function legMultiplier(leg) {
    return leg.type === "stock" ? 1 : (leg.multiplier || 100);
}

/**
 * 执行模拟盘交易 (支持混合资产: Stock + Options)
 * @param {Array} legs — currentLegs 数组
 * @returns {{ success: boolean, message: string }}
 */
export function executePaperTrade(legs) {
    if (!legs || legs.length === 0) {
        return { success: false, message: "无策略腿可执行" };
    }

    // ── 1. 计算 Net Debit/Credit (乘数陷阱防护) ──
    let netCost = 0;
    for (const leg of legs) {
        const mult = legMultiplier(leg);
        const amount = (leg.price || 0) * (leg.quantity || 1) * mult;
        if (leg.action === "buy") {
            netCost += amount;  // 买入 = 支出
        } else {
            netCost -= amount;  // 卖出 = 收入
        }
    }

    // ── 2. 余额检查 ──
    const cash = MOCK_DATA.portfolio.cash;
    if (netCost > cash) {
        return {
            success: false,
            message: `购买力不足: 需要 $${netCost.toFixed(2)}，可用 $${cash.toFixed(2)}`,
        };
    }

    // ── 3. 扣减资金 (原子操作) ──
    MOCK_DATA.portfolio.cash -= netCost;
    MOCK_DATA.portfolio.totalValue = MOCK_DATA.portfolio.cash;

    // ── 4. 统一 order_id + 构造持仓 ──
    const orderId = `paper_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const ticker = legs[0].ticker || "UNKNOWN";
    const strategyGroup = legs.length > 1
        ? `${legs.some(l => l.type === "stock") ? "Buy-Write" : "Combo"} ${ticker}`
        : ticker;

    for (const leg of legs) {
        const isStock = leg.type === "stock";
        const position = {
            ticker: leg.ticker || ticker,
            type: isStock ? "Stock" : (leg.right === "call" ? "Call" : "Put"),
            typeCn: isStock ? "正股 (Stock)" : (leg.right === "call" ? "看涨 (Call)" : "看跌 (Put)"),
            strike: isStock ? null : (leg.strike || 0),
            expiry: isStock ? "—" : (leg.expiration || "--"),
            dte: isStock ? null : (leg.dte || Math.round((new Date(leg.expiration) - new Date()) / 86400000) || 365),
            initialPremium: leg.price || 0,
            currentValue: leg.price || 0,
            pnl: 0,
            quantity: leg.quantity || 1,
            action: leg.action || "buy",
            openedAt: new Date().toISOString(),
            orderId,
            strategyGroup,
            multiplier: legMultiplier(leg),
        };
        MOCK_DATA.activePositions.push(position);
    }

    // ── 5. 更新 HUD 估算 ──
    let totalCost = 0;
    let totalDelta = 0;
    let totalTheta = 0;

    for (const p of MOCK_DATA.activePositions) {
        const mult = p.multiplier || (p.type === "Stock" ? 1 : 100);
        totalCost += p.initialPremium * (p.quantity || 1) * mult;

        const sign = p.action === "buy" ? 1 : -1;
        if (p.type === "Stock") {
            // 正股 Delta = 1.0 per share, Theta = 0
            totalDelta += sign * (p.quantity || 1) / 100;  // 归一化到每 100 股
        } else {
            const delta = p.type === "Call" ? 0.80 : -0.40;
            totalDelta += sign * delta * (p.quantity || 1);
            totalTheta += -0.03 * (p.quantity || 1) * 100;
        }
    }

    const totalValue = MOCK_DATA.portfolio.totalValue || 100000;
    MOCK_DATA.hud.marginUtilization = Math.min(99, Math.round((totalCost / totalValue) * 100));
    MOCK_DATA.hud.netSpyDelta = parseFloat(totalDelta.toFixed(2));
    MOCK_DATA.hud.netTheta = parseFloat(totalTheta.toFixed(2));

    // ── 6. 更新 perfMetrics ──
    MOCK_DATA.perfMetrics.totalTrades = (MOCK_DATA.perfMetrics.totalTrades || 0) + legs.length;

    // ── 7. 更新 tracking ──
    MOCK_DATA.tracking.automatedOps += 1;
    if (netCost < 0) {
        MOCK_DATA.tracking.totalPremiumCollected += Math.abs(netCost);
    }

    const stockCount = legs.filter(l => l.type === "stock").length;
    const optCount = legs.length - stockCount;
    const desc = [
        stockCount > 0 ? `${stockCount} 正股` : "",
        optCount > 0 ? `${optCount} 期权` : "",
    ].filter(Boolean).join(" + ");

    return {
        success: true,
        message: `✨ 模拟盘指令已成交: ${desc} ${ticker} 组合 [${orderId}]，净成本 $${Math.abs(netCost).toFixed(2)}`,
    };
}
