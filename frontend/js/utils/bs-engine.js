// ══════════════════════════════════════════════════════════════════
// AlphaTheta v2 — Black-Scholes Engine (纯 JS, 零依赖)
// ══════════════════════════════════════════════════════════════════
//
// Abramowitz & Stegun 近似 normalCDF, 精度 < 1e-7
// 导出: normalCDF, normalPDF, bsPrice, bsDelta, bsGamma, bsTheta, bsVega
// ══════════════════════════════════════════════════════════════════

/**
 * 标准正态分布累积分布函数
 * Abramowitz & Stegun approximation (精度 < 1e-7)
 */
export function normalCDF(x) {
    const a1 = 0.254829592;
    const a2 = -0.284496736;
    const a3 = 1.421413741;
    const a4 = -1.453152027;
    const a5 = 1.061405429;
    const p = 0.3275911;

    const sign = x < 0 ? -1 : 1;
    x = Math.abs(x) / Math.sqrt(2);
    const t = 1.0 / (1.0 + p * x);
    const y =
        1.0 -
        ((((a5 * t + a4) * t + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);
    return 0.5 * (1.0 + sign * y);
}

/** 标准正态分布概率密度函数 */
export function normalPDF(x) {
    return Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI);
}

/** 内部: 计算 d1, d2 */
function _d1d2(S, K, T, r, sigma) {
    const d1 =
        (Math.log(S / K) + (r + 0.5 * sigma * sigma) * T) /
        (sigma * Math.sqrt(T));
    const d2 = d1 - sigma * Math.sqrt(T);
    return { d1, d2 };
}

/**
 * Black-Scholes 期权定价
 * @param {number} S — 标的价格 (Spot)
 * @param {number} K — 行权价 (Strike)
 * @param {number} T — 年化到期时间 (e.g. 30/365)
 * @param {number} r — 无风险利率 (e.g. 0.05)
 * @param {number} sigma — 隐含波动率 (e.g. 0.25)
 * @param {'call'|'put'} [type='put']
 * @returns {number} 理论价格
 */
export function bsPrice(S, K, T, r, sigma, type = "put") {
    if (T <= 0) {
        return type === "call" ? Math.max(S - K, 0) : Math.max(K - S, 0);
    }
    const { d1, d2 } = _d1d2(S, K, T, r, sigma);
    if (type === "call") {
        return S * normalCDF(d1) - K * Math.exp(-r * T) * normalCDF(d2);
    }
    return K * Math.exp(-r * T) * normalCDF(-d2) - S * normalCDF(-d1);
}

/**
 * Delta — 价格敏感度
 * @returns {number} call: [0, 1], put: [-1, 0]
 */
export function bsDelta(S, K, T, r, sigma, type = "put") {
    if (T <= 0) {
        return type === "call" ? (S > K ? 1 : 0) : S < K ? -1 : 0;
    }
    const { d1 } = _d1d2(S, K, T, r, sigma);
    return type === "call" ? normalCDF(d1) : normalCDF(d1) - 1;
}

/**
 * Gamma — Delta 变化率
 * @returns {number}
 */
export function bsGamma(S, K, T, r, sigma) {
    if (T <= 0) return 0;
    const { d1 } = _d1d2(S, K, T, r, sigma);
    return normalPDF(d1) / (S * sigma * Math.sqrt(T));
}

/**
 * Theta — 时间衰减 (每日)
 * @returns {number}
 */
export function bsTheta(S, K, T, r, sigma, type = "put") {
    if (T <= 0) return 0;
    const { d1, d2 } = _d1d2(S, K, T, r, sigma);
    const common = -(S * normalPDF(d1) * sigma) / (2 * Math.sqrt(T));
    if (type === "call") {
        return (common - r * K * Math.exp(-r * T) * normalCDF(d2)) / 365;
    }
    return (common + r * K * Math.exp(-r * T) * normalCDF(-d2)) / 365;
}

/**
 * Vega — 波动率敏感度 (per 1% IV change)
 * @returns {number}
 */
export function bsVega(S, K, T, r, sigma) {
    if (T <= 0) return 0;
    const { d1 } = _d1d2(S, K, T, r, sigma);
    return (S * normalPDF(d1) * Math.sqrt(T)) / 100;
}

export default { normalCDF, normalPDF, bsPrice, bsDelta, bsGamma, bsTheta, bsVega };
