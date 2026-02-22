import { uuid } from "./uuid.js";

// ══════════════════════════════════════════════════════════════════
// AlphaTheta v2 — LEAPS Smart Strategy Generator
// ══════════════════════════════════════════════════════════════════
//
// 远期宏观期权组装器 — 拒绝短期 Theta 收割，只做 LEAPS 级别投资
//
// 核心原则:
//   1. 持有期锁死 270-540 天 (9个月 ~ 1.5年)
//   2. Bullish → Deep ITM Call (Δ≈0.80) / PMCC
//   3. Bearish → Deep ITM Put (Δ≈-0.70) / Long Put Spread
//   4. Neutral → 主动拦截 (远期铁鹰 Theta 无效)
//   5. 流动性验证: 绝对价差 ≤ $3.00, 相对价差 ≤ 15%
//
// 依赖: 0 (纯函数，无 DOM/fetch)
// ══════════════════════════════════════════════════════════════════

// ── 常量 ──────────────────────────────────────────────────────────

/** LEAPS 最小 DTE */
const LEAPS_MIN_DTE = 270;

/** LEAPS 最大 DTE */
const LEAPS_MAX_DTE = 540;

/** 远期流动性: 最大绝对价差 */
const LEAPS_MAX_SPREAD_ABS = 3.00;

/** 远期流动性: 最大相对价差 */
const LEAPS_MAX_SPREAD_PCT = 0.15;

/** 最大保证金占用比例 */
const MAX_MARGIN_PCT = 0.30;

/** Bullish: 目标 Delta (深度价内 Call) */
const BULLISH_TARGET_DELTA = 0.80;

/** Bearish: 目标 Delta (深度价内 Put) */
const BEARISH_TARGET_DELTA = -0.70;

/** 旧版常量 (保留向后兼容) */
const WING_WIDTH = 5;
const SHORT_OTM_PCT = 0.05;
const IV_RANK_THRESHOLD = 50;

// ── 异常类型 ─────────────────────────────────────────────────────

export class StrategyGenError extends Error {
    /**
     * @param {string} code
     * @param {string} message
     */
    constructor(code, message) {
        super(message);
        this.name = "StrategyGenError";
        this.code = code;
    }
}

// ══════════════════════════════════════════════════════════════════
// LEAPS 远期目标日期寻址器
// ══════════════════════════════════════════════════════════════════

/**
 * 在可用到期日列表中，寻找 270-540 天内的最优 LEAPS 到期日
 *
 * 策略: 优先选择距离 365 天最近的日期 (1 年甜点)
 *
 * @param {string[]} availableDates — ISO 日期字符串数组 ['2027-01-15', ...]
 * @returns {{ date: string, dte: number }} — 最优到期日 + DTE
 * @throws {StrategyGenError} 无满足条件的到期日时抛出
 */
export function findTargetExpiration(availableDates) {
    if (!availableDates || availableDates.length === 0) {
        throw new StrategyGenError(
            "NO_LEAPS_DATE",
            "到期日列表为空，无法定位 LEAPS 远期合约"
        );
    }

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const TARGET_DTE = 365; // 理想甜点: 1 年
    let bestDate = null;
    let bestDte = 0;
    let bestDistance = Infinity;

    for (const dateStr of availableDates) {
        const expDate = new Date(dateStr);
        const dte = Math.ceil((expDate - today) / 86400000);

        if (dte >= LEAPS_MIN_DTE && dte <= LEAPS_MAX_DTE) {
            const distFromTarget = Math.abs(dte - TARGET_DTE);
            if (distFromTarget < bestDistance) {
                bestDistance = distFromTarget;
                bestDate = dateStr;
                bestDte = dte;
            }
        }
    }

    if (!bestDate) {
        // 报告实际可用范围以帮助用户理解
        const allDtes = availableDates.map(d => {
            const dte = Math.ceil((new Date(d) - today) / 86400000);
            return { date: d, dte };
        }).filter(x => x.dte > 0);

        const maxAvail = allDtes.length > 0
            ? Math.max(...allDtes.map(x => x.dte))
            : 0;

        throw new StrategyGenError(
            "NO_LEAPS_DATE",
            `无法找到 ${LEAPS_MIN_DTE}-${LEAPS_MAX_DTE} 天的 LEAPS 到期日。` +
            `当前最远可用: ${maxAvail} 天。` +
            `该标的可能不支持远期期权或需要等待新的年度期权上线。`
        );
    }

    return { date: bestDate, dte: bestDte };
}

// ══════════════════════════════════════════════════════════════════
// 宽容流动性熔断 (LEAPS 专用)
// ══════════════════════════════════════════════════════════════════

/**
 * 验证远期期权流动性 — 远期合约 Spread 自然较宽，采用宽容规则
 *
 * 规则:
 *   1. Bid/Ask 必须 > 0
 *   2. 绝对价差 ≤ $3.00 (远期合约允许更宽)
 *   3. 相对价差 (ask-bid)/bid ≤ 15%
 *
 * @param {number} bid
 * @param {number} ask
 * @param {string} [context] — 合约描述 (用于错误信息)
 * @throws {StrategyGenError} 不满足时抛出
 */
export function validateLiquidity(bid, ask, context = "") {
    if (!bid || bid <= 0 || !ask || ask <= 0) {
        throw new StrategyGenError(
            "NO_LIQUIDITY",
            `流动性枯竭${context ? ` (${context})` : ""}: Bid/Ask 为零，远期合约可能尚无做市商报价`
        );
    }

    const spread = ask - bid;
    const spreadPct = spread / ask;  // 分母用 ask — bid 极小时更稳定 (Design D2)

    if (spread > LEAPS_MAX_SPREAD_ABS) {
        throw new StrategyGenError(
            "NO_LIQUIDITY",
            `远期流动性警告${context ? ` (${context})` : ""}: 绝对价差 $${spread.toFixed(2)} 超过 $${LEAPS_MAX_SPREAD_ABS} 上限，滑点过大`
        );
    }

    if (spreadPct > LEAPS_MAX_SPREAD_PCT) {
        throw new StrategyGenError(
            "NO_LIQUIDITY",
            `远期流动性警告${context ? ` (${context})` : ""}: 相对价差 ${(spreadPct * 100).toFixed(1)}% 超过 ${(LEAPS_MAX_SPREAD_PCT * 100)}% 上限`
        );
    }
}

// ══════════════════════════════════════════════════════════════════
// 离散行权价寻址 (通用)
// ══════════════════════════════════════════════════════════════════

/**
 * 在期权链数组中找到距离 targetPrice 最近的合约
 *
 * @param {Array<{strike: number, bid: number, ask: number}>} chain
 * @param {number} targetPrice — 目标行权价
 * @returns {{strike: number, bid: number, ask: number}}
 * @throws {StrategyGenError}
 */
export function findClosestStrike(chain, targetPrice) {
    if (!chain || chain.length === 0) {
        throw new StrategyGenError("CHAIN_EMPTY", "期权链为空，无法寻址");
    }

    let bestIdx = 0;
    let bestDist = Math.abs(chain[0].strike - targetPrice);

    for (let i = 1; i < chain.length; i++) {
        const dist = Math.abs(chain[i].strike - targetPrice);
        if (dist < bestDist) {
            bestDist = dist;
            bestIdx = i;
        }
    }

    return chain[bestIdx];
}

// ══════════════════════════════════════════════════════════════════
// 报价验证
// ══════════════════════════════════════════════════════════════════

/**
 * 验证合约报价有效性
 */
export function validateQuote(contract, side) {
    if (side === "sell") {
        if (!contract.bid || contract.bid <= 0) {
            throw new StrategyGenError(
                "NO_LIQUIDITY",
                `行权价 $${contract.strike} 的 Bid 为 0，流动性不足`
            );
        }
    } else {
        if (!contract.ask || contract.ask <= 0) {
            throw new StrategyGenError(
                "NO_LIQUIDITY",
                `行权价 $${contract.strike} 的 Ask 为 0，流动性不足`
            );
        }
    }
}

// ══════════════════════════════════════════════════════════════════
// LEAPS 策略: Deep ITM Call (Bullish)
// ══════════════════════════════════════════════════════════════════

/**
 * 生成 Deep ITM LEAPS Call — 替代正股的高资金效率做多
 *
 * 寻找 Delta ≈ 0.80 的深度价内 Call:
 *   strike ≈ spot × (1 - 0.20) = spot × 0.80
 *
 * @param {number} spotPrice
 * @param {Array<{strike:number,bid:number,ask:number}>} calls
 * @param {string} expiration — LEAPS 到期日
 * @returns {Array<Object>} — 1-2 腿
 */
function generateDeepITMCall(spotPrice, calls, expiration) {
    if (!calls?.length) {
        throw new StrategyGenError("CHAIN_EMPTY", "远期 Calls 链为空");
    }

    // Deep ITM Call: strike ≈ spot × 0.80 (Δ ≈ 0.80)
    const deepITMTarget = spotPrice * (1 - (1 - BULLISH_TARGET_DELTA));
    const deepCall = findClosestStrike(calls, deepITMTarget);
    validateQuote(deepCall, "buy");
    validateLiquidity(deepCall.bid, deepCall.ask, `Call $${deepCall.strike}`);

    return [{
        id: uuid(),
        type: "option",
        right: "call",
        action: "buy",
        expiration,
        strike: deepCall.strike,
        quantity: 1,
        price: deepCall.ask,
        multiplier: 100,
        _leaps: true,
    }];
}

// ══════════════════════════════════════════════════════════════════
// LEAPS 策略: Deep ITM Put + Put Spread (Bearish)
// ══════════════════════════════════════════════════════════════════

/**
 * 生成 Deep ITM LEAPS Put Spread — 远期做空
 *
 * Long Leg: Delta ≈ -0.70 的价内 Put (strike ≈ spot × 1.30)
 * Short Leg: 更低行权价的 OTM Put 用来部分对冲 Vega + 降低成本
 *
 * @param {number} spotPrice
 * @param {Array<{strike:number,bid:number,ask:number}>} puts
 * @param {string} expiration
 * @returns {Array<Object>} — 2 腿
 */
function generateDeepITMPutSpread(spotPrice, puts, expiration) {
    if (!puts?.length) {
        throw new StrategyGenError("CHAIN_EMPTY", "远期 Puts 链为空");
    }

    // Deep ITM Put: strike ≈ spot × 1.30 (Δ ≈ -0.70)
    const deepPutTarget = spotPrice * (1 + Math.abs(BEARISH_TARGET_DELTA + 1));
    const longPut = findClosestStrike(puts, deepPutTarget);
    validateQuote(longPut, "buy");
    validateLiquidity(longPut.bid, longPut.ask, `Put $${longPut.strike}`);

    // Short Leg: 距 Long 下方 $15-20 (远期 wing 更宽)
    const shortPutTarget = longPut.strike - 20;
    const shortPut = findClosestStrike(puts, shortPutTarget);

    const legs = [{
        id: uuid(),
        type: "option",
        right: "put",
        action: "buy",
        expiration,
        strike: longPut.strike,
        quantity: 1,
        price: longPut.ask,
        multiplier: 100,
        _leaps: true,
    }];

    // 只在 Short Put 有效且在 Long 下方时添加
    if (shortPut.bid > 0 && shortPut.strike < longPut.strike) {
        try {
            validateLiquidity(shortPut.bid, shortPut.ask, `Put $${shortPut.strike}`);
            legs.push({
                id: uuid(),
                type: "option",
                right: "put",
                action: "sell",
                expiration,
                strike: shortPut.strike,
                quantity: 1,
                price: shortPut.bid,
                multiplier: 100,
                _leaps: true,
            });
        } catch {
            // Short leg 流动性不足 → 降级为裸 Put 买入
        }
    }

    return legs;
}

// ══════════════════════════════════════════════════════════════════
// 旧版保留: Iron Condor (供手动组装 / autoSuggestNeutralStrategy)
// ══════════════════════════════════════════════════════════════════

export function generateIronCondor(spotPrice, optionChainData, expiration = null) {
    const { calls, puts } = optionChainData;

    if (!calls?.length || !puts?.length) {
        throw new StrategyGenError("CHAIN_EMPTY", "期权链数据不完整");
    }

    const shortPutTarget = spotPrice * (1 - SHORT_OTM_PCT);
    const shortPutContract = findClosestStrike(puts, shortPutTarget);
    validateQuote(shortPutContract, "sell");

    const longPutTarget = shortPutContract.strike - WING_WIDTH;
    const longPutContract = findClosestStrike(puts, longPutTarget);
    validateQuote(longPutContract, "buy");

    if (longPutContract.strike >= shortPutContract.strike) {
        throw new StrategyGenError("NO_WING", `Put 翼展异常: Long $${longPutContract.strike} ≥ Short $${shortPutContract.strike}`);
    }

    const shortCallTarget = spotPrice * (1 + SHORT_OTM_PCT);
    const shortCallContract = findClosestStrike(calls, shortCallTarget);
    validateQuote(shortCallContract, "sell");

    const longCallTarget = shortCallContract.strike + WING_WIDTH;
    const longCallContract = findClosestStrike(calls, longCallTarget);
    validateQuote(longCallContract, "buy");

    if (longCallContract.strike <= shortCallContract.strike) {
        throw new StrategyGenError("NO_WING", `Call 翼展异常: Long $${longCallContract.strike} ≤ Short $${shortCallContract.strike}`);
    }

    const exp = expiration || new Date().toISOString().split("T")[0];
    const makeLeg = (right, action, contract) => ({
        id: uuid(),
        type: "option",
        right,
        action,
        expiration: exp,
        strike: contract.strike,
        quantity: 1,
        price: action === "sell" ? contract.bid : contract.ask,
        multiplier: 100,
    });

    return [
        makeLeg("put", "buy", longPutContract),
        makeLeg("put", "sell", shortPutContract),
        makeLeg("call", "sell", shortCallContract),
        makeLeg("call", "buy", longCallContract),
    ];
}

// ══════════════════════════════════════════════════════════════════
// 旧版保留: autoSuggestNeutralStrategy (手动 AI 按钮)
// ══════════════════════════════════════════════════════════════════

export function autoSuggestNeutralStrategy(tickerData, optionChainData, expiration = null) {
    const { ivRank = 0, spotPrice = 0 } = tickerData;

    if (ivRank < IV_RANK_THRESHOLD) {
        return {
            success: false,
            reason: `当前 IV Rank ${ivRank} < ${IV_RANK_THRESHOLD}，强行构建铁鹰性价比极低，建议观望。`,
        };
    }

    try {
        const legs = generateIronCondor(spotPrice, optionChainData, expiration);
        const netCredit =
            legs.filter(l => l.action === "sell").reduce((sum, l) => sum + l.price, 0) -
            legs.filter(l => l.action === "buy").reduce((sum, l) => sum + l.price, 0);

        const putWing = Math.abs(legs[1].strike - legs[0].strike);
        const callWing = Math.abs(legs[3].strike - legs[2].strike);
        const maxWing = Math.max(putWing, callWing);
        const maxLoss = (maxWing - netCredit) * 100;

        return {
            success: true,
            strategy: "iron_condor",
            legs,
            meta: {
                netCredit: Math.round(netCredit * 100) / 100,
                maxLoss: Math.round(maxLoss),
                putSpread: `$${legs[0].strike}/$${legs[1].strike}`,
                callSpread: `$${legs[2].strike}/$${legs[3].strike}`,
                wingWidth: maxWing,
                riskRewardRatio: maxLoss > 0 ? Math.round((netCredit * 100 / maxLoss) * 100) / 100 : 0,
            },
        };
    } catch (err) {
        if (err instanceof StrategyGenError) {
            return { success: false, reason: err.message, code: err.code };
        }
        throw err;
    }
}

// ══════════════════════════════════════════════════════════════════
// Buy-Write: Short OTM Call (Delta ≈ 0.16)
// ══════════════════════════════════════════════════════════════════

/**
 * 生成短期/远期 OTM Call (卖出) -- Buy-Write 策略的期权腿
 *
 * 寻找 Delta ≈ 0.16 的虚值 Call:
 *   strike ≈ spot × (1 + SHORT_OTM_PCT)
 *
 * @param {number} spotPrice
 * @param {Array<{strike:number,bid:number,ask:number}>} calls
 * @param {string} expiration
 * @returns {Object|null} — 单腿对象, 无合约时返回 null
 */
function generateShortOTMCall(spotPrice, calls, expiration) {
    if (!calls?.length) return null;

    const otmTarget = spotPrice * (1 + SHORT_OTM_PCT);
    try {
        const otmCall = findClosestStrike(calls, otmTarget);
        validateQuote(otmCall, "sell");
        validateLiquidity(otmCall.bid, otmCall.ask, `OTM Call $${otmCall.strike}`);
        return {
            id: uuid(),
            type: "option",
            right: "call",
            action: "sell",
            expiration,
            strike: otmCall.strike,
            quantity: 1,
            price: otmCall.bid,
            multiplier: 100,
        };
    } catch {
        return null;
    }
}

// ══════════════════════════════════════════════════════════════════
// 公共入口: Smart 策略组装
// ══════════════════════════════════════════════════════════════════

/**
 * 自动组装策略 — 方向性投资 + Buy-Write 混合资产
 *
 * 路由规则:
 *   Bullish   → Deep ITM Call (Δ≈0.80) — 代替正股，极高资金效率
 *   Bearish   → Deep ITM Put Spread (Δ≈-0.70) — 锁定 Vega 风险
 *   buy_write → 100 股正股 + OTM Call 卖出 — 经典 Covered Call 建仓
 *   Neutral   → 主动拦截
 *
 * @param {string} ticker
 * @param {"bullish"|"bearish"|"buy_write"|"neutral"} direction
 * @param {number} currentBP — 可用购买力
 * @param {{calls: Array, puts: Array, spot?: number}} chainData
 * @param {string} expiration — 到期日
 * @returns {{success: boolean, strategy?: string, legs?: Array, meta?: Object, reason?: string, leapsDte?: number}}
 */
export function autoAssembleStrategy(ticker, direction, currentBP, chainData, expiration = null) {
    try {
        const spotPrice = chainData.spot || 0;
        let legs;
        let strategyName;
        let strategyLabel;

        // ── LEAPS 日期提示 ───────────────────────────────────────
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const dte = expiration
            ? Math.ceil((new Date(expiration) - today) / 86400000)
            : 0;

        // ── 方向路由 (LEAPS 优化) ────────────────────────────────
        switch (direction) {
            case "bullish":
                legs = generateDeepITMCall(spotPrice, chainData.calls, expiration);
                strategyName = "leaps_deep_itm_call";
                strategyLabel = `LEAPS 深度 ITM Call (Δ≈${BULLISH_TARGET_DELTA})`;
                break;

            case "bearish":
                legs = generateDeepITMPutSpread(spotPrice, chainData.puts, expiration);
                strategyName = legs.length > 1 ? "leaps_put_spread" : "leaps_deep_itm_put";
                strategyLabel = legs.length > 1
                    ? "LEAPS 远期看跌价差"
                    : `LEAPS 深度 ITM Put (Δ≈${BEARISH_TARGET_DELTA})`;
                break;

            case "buy_write": {
                // ── Buy-Write: 100 股正股 + OTM Call 卖出 ──────────
                const stockLeg = {
                    id: uuid(),
                    type: "stock",
                    right: null,
                    action: "buy",
                    ticker,
                    expiration: null,
                    strike: null,
                    quantity: 100,
                    price: spotPrice,
                    dte: null,
                    multiplier: 1,
                };
                const callLeg = generateShortOTMCall(spotPrice, chainData.calls, expiration);
                legs = callLeg ? [stockLeg, callLeg] : [stockLeg];
                strategyName = "buy_write";
                strategyLabel = callLeg
                    ? `Buy-Write ${ticker} (100 股 + OTM Call)`
                    : `Buy ${ticker} (100 股, 无可用 Call)`;
                break;
            }

            case "neutral":
            default:
                // ── 主动拦截: 远期中性策略无效 ──────────────────────
                return {
                    success: false,
                    reason:
                        "⚠️ 持有期长达 1 年的中性策略资金利用率极低 (Theta 衰减在远期几乎无效)。" +
                        "系统不建议在 LEAPS 周期构建铁鹰组合，已自动拦截。" +
                        "建议: 等待明确方向信号后再执行宏观投资。",
                    code: "NEUTRAL_BLOCKED",
                    ticker,
                    direction,
                };
        }

        // ── 计算组合指标 ────────────────────────────────────────
        // ⚠ 乘数陷阱防护: 正股 ×1, 期权 ×100
        const _mult = (l) => l.type === "stock" ? 1 : (l.multiplier || 100);
        const totalBuy = legs
            .filter(l => l.action === "buy")
            .reduce((sum, l) => sum + l.price * _mult(l) * l.quantity, 0);
        const totalSell = legs
            .filter(l => l.action === "sell")
            .reduce((sum, l) => sum + l.price * _mult(l) * l.quantity, 0);

        const netDebit = totalBuy - totalSell;
        const maxLoss = netDebit; // 买入型策略最大亏损 = 净支出

        // ── 资金熔断 ────────────────────────────────────────────
        if (currentBP > 0 && maxLoss > currentBP * MAX_MARGIN_PCT) {
            throw new StrategyGenError(
                "MARGIN_BREACH",
                `保证金穿透: LEAPS 策略成本 $${Math.round(maxLoss)} 超出购买力 ` +
                `${(MAX_MARGIN_PCT * 100)}% 水位线 ($${Math.round(currentBP * MAX_MARGIN_PCT)})，已拦截`
            );
        }

        return {
            success: true,
            strategy: strategyName,
            strategyLabel,
            ticker,
            direction,
            leapsDte: dte,
            legs,
            meta: {
                netDebit: Math.round(netDebit),
                maxLoss: Math.round(maxLoss),
                legCount: legs.length,
                dte,
                isLeaps: true,
            },
        };
    } catch (err) {
        if (err instanceof StrategyGenError) {
            return {
                success: false,
                reason: err.message,
                code: err.code,
                ticker,
                direction,
            };
        }
        throw err;
    }
}
