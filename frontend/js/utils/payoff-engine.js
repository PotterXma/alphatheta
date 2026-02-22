// ══════════════════════════════════════════════════════════════════
// AlphaTheta v2 — Universal Payoff Engine (通用盈亏推演引擎)
// ══════════════════════════════════════════════════════════════════
//
// 设计哲学: 严禁硬编码任何策略公式 (Iron Condor, Straddle 等)。
// 本引擎将任意多腿组合视为"分段线性函数的叠加"：
//
//   totalPayoff(S) = Σ legPayoff_i(S)   ∀ i ∈ legs
//
// 每条腿的到期盈亏都是关于标的价格 S 的分段线性函数:
//   - Call: kink 在 K 处，左侧 flat (= -premium)，右侧斜率 ±1
//   - Put:  kink 在 K 处，右侧 flat (= -premium)，左侧斜率 ∓1
//   - Stock: 全域线性，斜率 ±1
//
// 叠加任意数量的分段线性函数，结果仍为分段线性函数。
// 因此只需在足够密集的价格点上采样，即可精确重构盈亏曲线。
//
// 关键数学:
//   - Break-even: 线性插值 (相邻采样点间的零点)
//   - Max/Min: 分段线性函数的极值必出现在 kink 点或边界
//   - 无限检测: 边界导数 (斜率) 非零 → 收益/亏损随 S 线性增长 → 无限
// ══════════════════════════════════════════════════════════════════

/**
 * ┌─────────────────────────────────────────────────────────────────┐
 * │ 计算单腿到期盈亏 (Intrinsic Value at Expiry)                   │
 * │                                                                 │
 * │ 数学推导:                                                       │
 * │   Call 内在价值 = max(0, S - K)                                 │
 * │   Put  内在价值 = max(0, K - S)                                 │
 * │                                                                 │
 * │   买方盈亏 = (内在价值 - 权利金) × 数量 × 乘数                  │
 * │   卖方盈亏 = (权利金 - 内在价值) × 数量 × 乘数                  │
 * │                                                                 │
 * │   正股: 线性盈亏 = (S - 入场价) × 数量 × 方向符号               │
 * └─────────────────────────────────────────────────────────────────┘
 */
function legPayoff(leg, S) {
    const { type, right, action, strike, price, quantity, multiplier } = leg;

    // 跳过无效腿 (数量为 0 或价格未填)
    if (!quantity || quantity <= 0) return 0;

    // ── 方向乘子: buy=+1 (做多内在价值), sell=-1 (做空内在价值) ──
    const dir = action === "buy" ? 1 : -1;
    const mult = multiplier || (type === "stock" ? 1 : 100);

    if (type === "stock") {
        // ── 正股: 纯线性 ──
        // Buy Stock:  盈亏 = (S - entryPrice) × qty
        // Sell Stock: 盈亏 = (entryPrice - S) × qty
        return dir * (S - price) * quantity * mult;
    }

    // ── 期权: 分段线性 ──
    let intrinsic;
    if (right === "call") {
        intrinsic = Math.max(0, S - strike);
    } else {
        // put
        intrinsic = Math.max(0, strike - S);
    }

    // Buy:  (intrinsic - premium) × qty × mult   → 支付权利金，收获内在价值
    // Sell: (premium - intrinsic) × qty × mult   → 收取权利金，承担内在价值
    return dir * (intrinsic - price) * quantity * mult;
}

/**
 * ┌─────────────────────────────────────────────────────────────────┐
 * │ 通用组合盈亏推演引擎 (Universal Combo Payoff Engine)            │
 * │                                                                 │
 * │ 算法概览:                                                       │
 * │ 1. 自适应步长生成 ~1000 个模拟价格点                             │
 * │ 2. 对每个价格点叠加所有腿的到期盈亏                             │
 * │ 3. 边界斜率检测 → 判断收益/风险是否无限                          │
 * │ 4. 线性插值 → 精确定位盈亏平衡点                                │
 * └─────────────────────────────────────────────────────────────────┘
 *
 * @param {Array} legs — currentLegs 数组 (see multi-leg-state spec R1)
 * @param {number} spotPrice — 当前标的价格
 * @returns {{
 *   pricePoints: number[],
 *   payoffData: number[],
 *   maxProfit: number|string,
 *   maxLoss: number|string,
 *   breakevens: number[],
 *   estCollateral: number|string
 * }}
 */
export function calculateComboPayoff(legs, spotPrice) {
    // ── 参数校验 ──────────────────────────────────────────────────
    if (!legs || legs.length === 0 || !spotPrice || spotPrice <= 0) {
        return {
            pricePoints: [],
            payoffData: [],
            maxProfit: 0,
            maxLoss: 0,
            breakevens: [],
            estCollateral: 0,
        };
    }

    // ══════════════════════════════════════════════════════════════
    // STEP 1: 构建自适应模拟价格数组 — 动态包裹边界 (Dynamic Bounding)
    // ══════════════════════════════════════════════════════════════
    //
    // ⚠ 致命 Bug 修复 (v2.1):
    // 旧版硬编码 [spot*0.5, spot*1.5] 会截断深虚值 (Deep OTM) 策略。
    // 例: 现价 $100, 卖出 $40 Put → $40 在 [$50, $150] 区间外
    //     → 引擎扫描不到行权价 → 左侧斜率误判为 0
    //     → 向用户展示"零风险"的致命错误推演。
    //
    // 修复: 动态边界 = max(默认范围, 所有行权价的包裹范围)
    //
    // 步长 = spot × 0.001 → 保证基础 ~1000 个采样点
    // ──────────────────────────────────────────────────────────────

    // ── Step 1a: 提取所有期权腿的行权价极值 ──
    // 忽略正股腿 (type=stock) 和未填写 strike 的腿
    let minStrike = Infinity;
    let maxStrike = -Infinity;

    for (const leg of legs) {
        if (leg.type === "stock" || !leg.strike) continue;
        if (leg.strike < minStrike) minStrike = leg.strike;
        if (leg.strike > maxStrike) maxStrike = leg.strike;
    }

    // 无期权腿 (纯正股) → 回退到默认范围
    if (minStrike === Infinity) minStrike = spotPrice;
    if (maxStrike === -Infinity) maxStrike = spotPrice;

    // ── Step 1b: 计算动态边界 ──
    // loBound = min(spot * 0.5, minStrike * 0.8)
    //   → 确保最低行权价下方还有 20% 缓冲区，
    //     用于检测左侧边界斜率是否趋向 -∞
    //
    // hiBound = max(spot * 1.5, maxStrike * 1.2)
    //   → 确保最高行权价上方还有 20% 缓冲区
    //
    // Math.max(0, loBound): 股价不能跌穿 $0 (有限责任公司)
    const loBound = Math.max(0, Math.min(spotPrice * 0.5, minStrike * 0.8));
    const hiBound = Math.max(spotPrice * 1.5, maxStrike * 1.2);

    // ── Step 1c: 自适应步长生成价格数组 ──
    const step = spotPrice * 0.001;
    const pricePoints = [];
    for (let s = loBound; s <= hiBound; s += step) {
        pricePoints.push(Math.round(s * 100) / 100); // 保留 2 位小数
    }

    // 确保末端包含 hiBound
    if (pricePoints[pricePoints.length - 1] < hiBound) {
        pricePoints.push(Math.round(hiBound * 100) / 100);
    }

    // ══════════════════════════════════════════════════════════════
    // STEP 2: 叠加所有腿的到期盈亏
    // ══════════════════════════════════════════════════════════════
    //
    // 核心公式:
    //   totalPayoff(S) = Σ_i legPayoff(leg_i, S)
    //
    // 分段线性叠加的数学保证:
    //   有限条分段线性函数的和仍为分段线性函数。
    //   因此在 kink 点 (行权价) 之间的区间内，
    //   payoff(S) 是 S 的线性函数 → 极值必在 kink 或边界。
    // ──────────────────────────────────────────────────────────────
    const payoffData = new Float64Array(pricePoints.length);

    for (let i = 0; i < pricePoints.length; i++) {
        const S = pricePoints[i];
        let total = 0;
        for (let j = 0; j < legs.length; j++) {
            total += legPayoff(legs[j], S);
        }
        payoffData[i] = Math.round(total * 100) / 100; // 精度: $0.01
    }

    // ══════════════════════════════════════════════════════════════
    // STEP 3: 特征提取 — Max/Min + 边界斜率无限检测
    // ══════════════════════════════════════════════════════════════
    //
    // 关键数学: 分段线性函数在无穷远处的行为完全由边界斜率决定。
    //
    //   若 rightSlope > 0 → payoff(S) → +∞ as S → +∞ → Unlimited Profit
    //   若 rightSlope < 0 → payoff(S) → -∞ as S → +∞ → Unlimited Loss
    //   若 leftSlope  > 0 → payoff(S) → +∞ as S → 0  → (不太可能，但裸卖 Put 类似)
    //   若 leftSlope  < 0 → payoff(S) → -∞ as S → 0  → Unlimited Loss (左侧)
    //
    // 容差 = step * 0.5：避免浮点精度误判"零斜率"为"非零"。
    // ──────────────────────────────────────────────────────────────
    const n = payoffData.length;
    const tolerance = step * 0.5;

    // 边界导数 (离散近似)
    const leftSlope = payoffData[1] - payoffData[0];
    const rightSlope = payoffData[n - 1] - payoffData[n - 2];

    // 扫描全局极值
    let rawMax = -Infinity;
    let rawMin = Infinity;
    for (let i = 0; i < n; i++) {
        if (payoffData[i] > rawMax) rawMax = payoffData[i];
        if (payoffData[i] < rawMin) rawMin = payoffData[i];
    }

    // ── 无限利润检测 ──
    // 条件: 最大值出现在边界，且该边界斜率显著为正
    // 物理含义: 盈亏曲线在区间外继续上升，利润无上限
    let maxProfit;
    const maxAtRightBoundary = payoffData[n - 1] === rawMax;
    const maxAtLeftBoundary = payoffData[0] === rawMax;

    if ((maxAtRightBoundary && rightSlope > tolerance) ||
        (maxAtLeftBoundary && leftSlope < -tolerance)) {
        maxProfit = "Unlimited";
    } else {
        maxProfit = rawMax;
    }

    // ── 无限亏损检测 ──
    // 条件: 最小值出现在边界，且该边界斜率显著为负 (向下延伸)
    // 物理含义: 盈亏曲线在区间外继续下降，亏损无下限
    let maxLoss;
    const minAtRightBoundary = payoffData[n - 1] === rawMin;
    const minAtLeftBoundary = payoffData[0] === rawMin;

    if ((minAtRightBoundary && rightSlope < -tolerance) ||
        (minAtLeftBoundary && leftSlope > tolerance)) {
        maxLoss = "Unlimited Risk";
    } else {
        maxLoss = rawMin;
    }

    // ── 预估保证金 ──
    // 实盘保证金计算极为复杂 (SPAN, PM)，此处使用 |maxLoss| 作为近似。
    // 若无限风险 → 保证金也标记为 Unlimited。
    const estCollateral =
        maxLoss === "Unlimited Risk" ? "Unlimited Risk" : Math.abs(rawMin);

    // ══════════════════════════════════════════════════════════════
    // STEP 4: 盈亏平衡点 — 线性插值求零点
    // ══════════════════════════════════════════════════════════════
    //
    // 数学原理:
    //   在相邻采样点 (S_i, pnl_i) 和 (S_{i+1}, pnl_{i+1}) 之间，
    //   若 pnl_i × pnl_{i+1} < 0 (符号翻转)，则存在零点。
    //
    //   线性插值公式:
    //     S_zero = S_i - pnl_i × (S_{i+1} - S_i) / (pnl_{i+1} - pnl_i)
    //
    //   这利用了分段线性函数在两个 kink 之间是严格线性的性质，
    //   因此插值结果是精确的 (非近似)。
    // ──────────────────────────────────────────────────────────────
    const breakevens = [];

    for (let i = 0; i < n - 1; i++) {
        const pnlA = payoffData[i];
        const pnlB = payoffData[i + 1];

        // 检测符号翻转 (包括从零穿越)
        if (pnlA * pnlB < 0) {
            // 线性插值求精确零点
            const sA = pricePoints[i];
            const sB = pricePoints[i + 1];
            const zero = sA - pnlA * (sB - sA) / (pnlB - pnlA);
            breakevens.push(Math.round(zero * 100) / 100);
        } else if (pnlA === 0 && (i === 0 || payoffData[i - 1] * pnlB < 0)) {
            // 精确踩在零点上 (罕见但处理)
            breakevens.push(pricePoints[i]);
        }
    }

    return {
        pricePoints: Array.from(pricePoints), // Float64Array → Array for JSON
        payoffData: Array.from(payoffData),
        maxProfit,
        maxLoss,
        breakevens,
        estCollateral,
    };
}

/**
 * 计算组合的 Net Premium (净权利金收支)
 *
 * @param {Array} legs — currentLegs 数组
 * @returns {{ net: number, isCredit: boolean }}
 */
export function calculateNetPremium(legs) {
    if (!legs || legs.length === 0) return { net: 0, isCredit: true };

    let net = 0;
    for (const leg of legs) {
        if (!leg.quantity || leg.quantity <= 0 || !leg.price) continue;
        const mult = leg.multiplier || (leg.type === "stock" ? 1 : 100);
        const amount = leg.price * leg.quantity * mult;

        if (leg.action === "sell") {
            net += amount; // 收取
        } else {
            net -= amount; // 支付
        }
    }

    return {
        net: Math.round(net * 100) / 100,
        isCredit: net >= 0,
    };
}

export default { calculateComboPayoff, calculateNetPremium };

// ══════════════════════════════════════════════════════════════════
// BLACK-SCHOLES 定价引擎 (European Options)
// ══════════════════════════════════════════════════════════════════
//
// 数学基础:
//   C(S,K,T,r,σ) = S·N(d₁) - K·e^(-rT)·N(d₂)
//   P(S,K,T,r,σ) = K·e^(-rT)·N(-d₂) - S·N(-d₁)
//
//   d₁ = [ln(S/K) + (r + σ²/2)·T] / (σ·√T)
//   d₂ = d₁ - σ·√T
//
// CDF 精度: Abramowitz & Stegun 近似 (max error 7.5×10⁻⁸)
// ══════════════════════════════════════════════════════════════════

/** 默认无风险利率 (年化) */
const BS_RISK_FREE_RATE = 0.04;

/**
 * 标准正态分布 PDF — φ(x) = (1/√2π) · e^(-x²/2)
 * @param {number} x
 * @returns {number}
 */
export function normPDF(x) {
    return Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI);
}

/**
 * 标准正态分布 CDF — Φ(x)
 *
 * Abramowitz & Stegun 近似 (公式 26.2.17)
 * 最大绝对误差 < 7.5 × 10⁻⁸
 *
 * @param {number} x
 * @returns {number} 值域 [0, 1]
 */
export function normCDF(x) {
    if (x > 10) return 1;
    if (x < -10) return 0;

    const a1 = 0.254829592;
    const a2 = -0.284496736;
    const a3 = 1.421413741;
    const a4 = -1.453152027;
    const a5 = 1.061405429;
    const p = 0.3275911;

    const sign = x < 0 ? -1 : 1;
    const absX = Math.abs(x);
    const t = 1.0 / (1.0 + p * absX);
    const t2 = t * t;
    const t3 = t2 * t;
    const t4 = t3 * t;
    const t5 = t4 * t;

    const y = 1.0 - (a1 * t + a2 * t2 + a3 * t3 + a4 * t4 + a5 * t5) * Math.exp(-absX * absX / 2.0);

    return 0.5 * (1.0 + sign * y);
}

/**
 * 计算 d₁ — BS 模型核心中间量
 *
 * d₁ = [ln(S/K) + (r + σ²/2)·T] / (σ·√T)
 *
 * @param {number} S — 标的现价
 * @param {number} K — 行权价
 * @param {number} T — 剩余年化时间 (days/365)
 * @param {number} r — 无风险利率
 * @param {number} v — 隐含波动率 (小数, 如 0.30)
 * @returns {number}
 */
export function bsD1(S, K, T, r, v) {
    if (T <= 0 || v <= 0 || S <= 0 || K <= 0) return 0;
    return (Math.log(S / K) + (r + 0.5 * v * v) * T) / (v * Math.sqrt(T));
}

/**
 * 计算 d₂ = d₁ - σ·√T
 */
export function bsD2(S, K, T, r, v) {
    if (T <= 0 || v <= 0) return 0;
    return bsD1(S, K, T, r, v) - v * Math.sqrt(T);
}

/**
 * Black-Scholes 欧式期权定价
 *
 * @param {number} S — 标的现价
 * @param {number} K — 行权价
 * @param {number} T — 剩余年化时间 (days / 365)
 * @param {number} r — 无风险利率
 * @param {number} v — 隐含波动率 (小数)
 * @param {"call"|"put"} type — 期权类型
 * @returns {number} — 理论价值 (每份合约的价格)
 */
export function blackScholes(S, K, T, r, v, type) {
    // 到期: 回退到内在价值
    if (T <= 0) {
        return type === "call"
            ? Math.max(0, S - K)
            : Math.max(0, K - S);
    }

    // 波动率为 0: 确定性模型
    if (v <= 0) {
        const pv = K * Math.exp(-r * T);
        return type === "call"
            ? Math.max(0, S - pv)
            : Math.max(0, pv - S);
    }

    const d1 = bsD1(S, K, T, r, v);
    const d2 = bsD2(S, K, T, r, v);
    const discount = Math.exp(-r * T);

    if (type === "call") {
        return S * normCDF(d1) - K * discount * normCDF(d2);
    } else {
        return K * discount * normCDF(-d2) - S * normCDF(-d1);
    }
}

// ══════════════════════════════════════════════════════════════════
// GREEKS — 一阶/二阶偏导数
// ══════════════════════════════════════════════════════════════════

/**
 * Delta — ∂V/∂S
 * Call: N(d₁)
 * Put:  N(d₁) - 1
 *
 * @returns {number} Delta 值 (Call: [0,1], Put: [-1,0])
 */
export function bsDelta(S, K, T, r, v, type) {
    if (T <= 0) {
        // 到期 Delta: 深度 ITM = ±1, OTM = 0
        if (type === "call") return S > K ? 1 : 0;
        return S < K ? -1 : 0;
    }
    const d1 = bsD1(S, K, T, r, v);
    return type === "call" ? normCDF(d1) : normCDF(d1) - 1;
}

/**
 * Gamma — ∂²V/∂S²
 *
 * Gamma = φ(d₁) / (S · σ · √T)
 * 注意: Gamma 对 Call/Put 相同 (Put-Call Parity)
 *
 * @returns {number} Gamma 值 (always ≥ 0)
 */
export function bsGamma(S, K, T, r, v, _type) {
    if (T <= 0 || v <= 0 || S <= 0) return 0;
    const d1 = bsD1(S, K, T, r, v);
    return normPDF(d1) / (S * v * Math.sqrt(T));
}

/**
 * Theta — ∂V/∂T (每日)
 *
 * Call: -[S·φ(d₁)·σ / (2√T)] - r·K·e^(-rT)·N(d₂)
 * Put:  -[S·φ(d₁)·σ / (2√T)] + r·K·e^(-rT)·N(-d₂)
 *
 * 返回每日 Theta (除以 365)
 *
 * @returns {number} Theta (通常为负)
 */
export function bsTheta(S, K, T, r, v, type) {
    if (T <= 0 || v <= 0 || S <= 0) return 0;

    const d1 = bsD1(S, K, T, r, v);
    const d2 = bsD2(S, K, T, r, v);
    const sqrtT = Math.sqrt(T);
    const discount = Math.exp(-r * T);

    const term1 = -(S * normPDF(d1) * v) / (2 * sqrtT);

    if (type === "call") {
        return (term1 - r * K * discount * normCDF(d2)) / 365;
    } else {
        return (term1 + r * K * discount * normCDF(-d2)) / 365;
    }
}

/**
 * Vega — ∂V/∂σ
 *
 * Vega = S · √T · φ(d₁)
 * 注意: Vega 对 Call/Put 相同
 *
 * 返回每 1% IV 变化的价格变动 (除以 100)
 *
 * @returns {number} Vega (always ≥ 0)
 */
export function bsVega(S, K, T, r, v, _type) {
    if (T <= 0 || v <= 0 || S <= 0) return 0;
    const d1 = bsD1(S, K, T, r, v);
    return (S * Math.sqrt(T) * normPDF(d1)) / 100;
}

// ══════════════════════════════════════════════════════════════════
// T+n 推演 — BS 定价的单腿盈亏
// ══════════════════════════════════════════════════════════════════

/**
 * 计算单腿在 T+n 时刻的盈亏 (BS 理论价值 vs 入场成本)
 *
 * @param {Object} leg — currentLegs 元素
 * @param {number} S — 假设的标的价格
 * @param {number} T — 剩余年化时间 (days/365)
 * @param {number} v — 隐含波动率 (小数)
 * @param {number} [r=0.04] — 无风险利率
 * @returns {number} — 盈亏金额
 */
export function legPayoffBS(leg, S, T, v, r = BS_RISK_FREE_RATE) {
    const { type, right, action, strike, price, quantity, multiplier } = leg;
    if (!quantity || quantity <= 0) return 0;

    const dir = action === "buy" ? 1 : -1;
    const mult = multiplier || (type === "stock" ? 1 : 100);

    if (type === "stock") {
        return dir * (S - price) * quantity * mult;
    }

    // BS 理论价值
    const theoretical = blackScholes(S, strike, T, r, v, right);

    // 盈亏 = 方向 × (理论价值 - 入场价格) × 数量 × 乘数
    return dir * (theoretical - price) * quantity * mult;
}

// ══════════════════════════════════════════════════════════════════
// 双曲线推演 (Dual Curve Payoff)
// ══════════════════════════════════════════════════════════════════

/**
 * 计算组合的双曲线盈亏数据
 *
 * @param {Array} legs — currentLegs 数组
 * @param {number} spotPrice — 当前标的价格
 * @param {number} targetDTE — T+n 目标天数 (0 = 到期)
 * @param {number} targetIV — 目标隐含波动率 (小数, 如 0.30)
 * @param {number} [r=0.04] — 无风险利率
 * @returns {{pricePoints: number[], expiryData: number[], tnData: number[]}}
 */
export function calculateComboPayoffDualCurve(legs, spotPrice, targetDTE = 0, targetIV = 0.30, r = BS_RISK_FREE_RATE) {
    if (!legs || legs.length === 0) {
        return { pricePoints: [], expiryData: [], tnData: [] };
    }

    // 采样范围: ±30% spot price, 200 个点
    const low = spotPrice * 0.7;
    const high = spotPrice * 1.3;
    const steps = 200;
    const step = (high - low) / steps;

    const T = Math.max(targetDTE, 0) / 365;

    const pricePoints = [];
    const expiryData = [];
    const tnData = [];

    for (let i = 0; i <= steps; i++) {
        const S = low + i * step;
        pricePoints.push(Math.round(S * 100) / 100);

        // 曲线 1: 到期日内在价值 (始终使用 legPayoff)
        let expiryPL = 0;
        let tnPL = 0;

        for (const leg of legs) {
            if (!leg.quantity || leg.quantity <= 0) continue;
            expiryPL += legPayoff(leg, S);
            tnPL += legPayoffBS(leg, S, T, targetIV, r);
        }

        expiryData.push(Math.round(expiryPL * 100) / 100);
        tnData.push(Math.round(tnPL * 100) / 100);
    }

    return { pricePoints, expiryData, tnData };
}

// ══════════════════════════════════════════════════════════════════
// Portfolio Greeks 聚合算法
// ══════════════════════════════════════════════════════════════════

/**
 * 计算多腿组合的加权 Greeks
 *
 * Net Greek = Σ (Leg Greek × Quantity × Multiplier × Direction)
 * Direction: buy = +1, sell = -1
 *
 * @param {Array} legs — currentLegs 数组
 * @param {number} spotPrice — 当前标的价格
 * @param {number} currentDTE — 当前距到期天数
 * @param {number} currentIV — 当前隐含波动率 (小数)
 * @param {number} [r=0.04] — 无风险利率
 * @returns {{netDelta: number, netGamma: number, netTheta: number, netVega: number}}
 */
export function calculatePortfolioGreeks(legs, spotPrice, currentDTE, currentIV, r = BS_RISK_FREE_RATE) {
    let netDelta = 0;
    let netGamma = 0;
    let netTheta = 0;
    let netVega = 0;

    if (!legs || legs.length === 0 || spotPrice <= 0) {
        return { netDelta, netGamma, netTheta, netVega };
    }

    const T = Math.max(currentDTE, 0) / 365;

    for (const leg of legs) {
        if (!leg.quantity || leg.quantity <= 0) continue;

        const dir = leg.action === "buy" ? 1 : -1;
        const mult = leg.multiplier || (leg.type === "stock" ? 1 : 100);
        const qty = leg.quantity;
        const weight = dir * qty * mult;

        if (leg.type === "stock") {
            // 正股: Delta = ±1, Gamma/Theta/Vega = 0
            netDelta += dir * qty * mult;
            continue;
        }

        // 期权: 计算 BS Greeks
        const K = leg.strike;
        const v = currentIV;
        const right = leg.right;

        netDelta += bsDelta(spotPrice, K, T, r, v, right) * weight;
        netGamma += bsGamma(spotPrice, K, T, r, v, right) * weight;
        netTheta += bsTheta(spotPrice, K, T, r, v, right) * weight;
        netVega += bsVega(spotPrice, K, T, r, v, right) * weight;
    }

    return {
        netDelta: Math.round(netDelta * 1000) / 1000,
        netGamma: Math.round(netGamma * 1000) / 1000,
        netTheta: Math.round(netTheta * 100) / 100,
        netVega: Math.round(netVega * 100) / 100,
    };
}
