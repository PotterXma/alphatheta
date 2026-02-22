// ══════════════════════════════════════════════════════════════════
// AlphaTheta v2 — API Services
// ══════════════════════════════════════════════════════════════════
//
// 所有业务 API 调用收敛在此文件，上层 view 只需 import 使用。
// 每个函数返回 Promise<data>，异常由 client.js 统一包装为 ApiError。
// ══════════════════════════════════════════════════════════════════

import { get, post, del } from "./client.js";

// ── Dashboard ───────────────────────────────────────────────────

/** 同步仪表盘数据 (宏观雷达 + 信号引擎 + 持仓) */
export function fetchDashboardSync() {
    return get("/api/v1/dashboard/sync");
}

/** 获取标的行情图表数据 */
export function fetchMarketChart(ticker, period = "1D") {
    return get(`/api/v1/market/chart/${ticker}?period=${period}`);
}

// ── Strategy (Top Picks + Search) ───────────────────────────────

/** 智能推荐 Top 3 */
export function fetchTopPicks() {
    return get("/api/v1/strategy/top-picks");
}

/** Ticker 模糊搜索 */
export function searchTickers(query) {
    return get(`/api/v1/strategy/search?q=${encodeURIComponent(query)}`);
}

// ── Orders ──────────────────────────────────────────────────────

/** 获取订单列表 */
export function fetchOrders(status = "") {
    const qs = status ? `?status=${status}` : "";
    return get(`/api/v1/orders${qs}`);
}

/** 提交新订单 */
export function submitOrder(orderData) {
    return post("/api/v1/orders", orderData);
}

/** 展期组合单 (Buy to Close + Sell to Open) */
export function rollCombo(rollData) {
    return post("/api/v1/orders/roll_combo", rollData);
}

// ── Watchlist ───────────────────────────────────────────────────

/** 获取 Watchlist */
export function fetchWatchlist() {
    return get("/api/v1/watchlist");
}

/** 添加标的到 Watchlist */
export function addTicker(ticker) {
    return post("/api/v1/watchlist", { ticker });
}

/** 从 Watchlist 移除标的 */
export function removeTicker(ticker) {
    return del(`/api/v1/watchlist/${encodeURIComponent(ticker)}`);
}

/** 切换标的激活状态 */
export function toggleTicker(ticker) {
    return post(`/api/v1/watchlist/${encodeURIComponent(ticker)}/toggle`);
}

// ── Portfolio ───────────────────────────────────────────────────

/** 获取盯市净值曲线 */
export function fetchEquityCurve(days = 90) {
    return get(`/api/v1/portfolio/equity-curve?days=${days}`);
}

// ── Settings ────────────────────────────────────────────────────

/** 获取全部设置 */
export function fetchSettings() {
    return get("/api/v1/settings");
}

/** 更新设置 */
export function updateSetting(key, value) {
    return post("/api/v1/settings", { key, value });
}

/** 获取 API Key 信息 */
export function fetchApiKeys() {
    return get("/api/v1/settings/api-keys");
}

/** 更新 Kill Switch */
export function updateKillSwitch(enabled) {
    return post("/api/v1/settings/kill-switch", { enabled });
}

export default {
    fetchDashboardSync,
    fetchMarketChart,
    fetchTopPicks,
    searchTickers,
    fetchOrders,
    submitOrder,
    rollCombo,
    fetchWatchlist,
    addTicker,
    removeTicker,
    toggleTicker,
    fetchEquityCurve,
    fetchSettings,
    updateSetting,
    fetchApiKeys,
    updateKillSwitch,
};
