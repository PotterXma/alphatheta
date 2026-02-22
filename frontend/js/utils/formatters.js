// ══════════════════════════════════════════════════════════════════
// AlphaTheta v2 — Format Utilities (纯函数, 零 DOM 依赖)
// ══════════════════════════════════════════════════════════════════

/**
 * 格式化金额
 * @param {number} v
 * @returns {string} e.g. "$1,234.56" or "-$1,234.56"
 */
export function formatMoney(v) {
    if (v == null || isNaN(v)) return "$0.00";
    const abs = Math.abs(v);
    const formatted = abs.toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
    return v < 0 ? `-$${formatted}` : `$${formatted}`;
}

/**
 * 格式化百分比 (带正号)
 * @param {number} v — 已经是百分比值 (e.g. 12.34)
 * @returns {string} e.g. "+12.34%" or "-5.67%"
 */
export function formatPercentage(v) {
    if (v == null || isNaN(v)) return "0.00%";
    const sign = v > 0 ? "+" : "";
    return `${sign}${v.toFixed(2)}%`;
}

/**
 * 格式化日期
 * @param {string|Date} dateStr
 * @returns {string} e.g. "2026-02-21"
 */
export function formatDate(dateStr) {
    if (!dateStr) return "—";
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return String(dateStr);
    return d.toISOString().split("T")[0];
}

/**
 * 格式化 Delta/Greeks 值
 * @param {number} num
 * @param {number} [digits=4]
 * @returns {string} e.g. "Δ 0.3500"
 */
export function formatDelta(num, digits = 4) {
    if (num == null || isNaN(num)) return "Δ —";
    return `Δ ${num.toFixed(digits)}`;
}

/**
 * 格式化资金变动
 * @param {string|number} cap
 * @returns {string} e.g. "+$1,234" or "-$5,678"
 */
export function formatCapitalImpact(cap) {
    if (typeof cap === "string") return cap;
    if (typeof cap === "number") {
        return cap >= 0
            ? `+$${cap.toLocaleString()}`
            : `-$${Math.abs(cap).toLocaleString()}`;
    }
    return String(cap);
}

/**
 * 数字补零
 * @param {number} n
 * @returns {string} e.g. "05"
 */
export function pad(n) {
    return String(n).padStart(2, "0");
}

/**
 * 计算百分比差异
 * @param {number} price
 * @param {number} sma
 * @returns {string} e.g. "+9.71%"
 */
export function pctDiff(price, sma) {
    if (!sma || sma === 0) return "0.00%";
    const pct = ((price - sma) / sma) * 100;
    return formatPercentage(pct);
}

export default { formatMoney, formatPercentage, formatDate, formatDelta, formatCapitalImpact, pad, pctDiff };
