// ══════════════════════════════════════════════════════════════════
// AlphaTheta v2 — Market Helpers (期权链工具函数)
// ══════════════════════════════════════════════════════════════════
//
// 核心函数:
//   snapToStrike()   — 行权价吸附: 将模板的"档位偏移"映射到离散期权链
//   resolveTemplate() — 将策略模板骨架转换为可用的 currentLegs 数组
// ══════════════════════════════════════════════════════════════════

/**
 * ┌─────────────────────────────────────────────────────────────────┐
 * │ 行权价吸附算法 (Strike Snapping)                                │
 * │                                                                 │
 * │ 问题: 真实期权链的行权价是离散的 (如 495, 500, 505, 510)。      │
 * │       模板不能用 "strikeOffset: -10" 这样的绝对偏移，           │
 * │       因为不同标的的行权价间距不同 ($1, $2.5, $5, $10)。        │
 * │                                                                 │
 * │ 解法: 使用"档位偏移 (strikeStep)"代替绝对偏移。                 │
 * │       例如 strikeStep = -2 表示"ATM 下方第 2 个行权价"。        │
 * │                                                                 │
 * │ 算法:                                                           │
 * │   1. 在 availableStrikes[] 中二分查找最接近 spot 的 ATM 索引      │
 * │   2. 目标索引 = ATM索引 + strikeStep                            │
 * │   3. 边界 clamp: Math.max(0, Math.min(len-1, targetIdx))       │
 * └─────────────────────────────────────────────────────────────────┘
 *
 * @param {number} spotPrice — 当前标的价格 (e.g. 502.30)
 * @param {number} strikeStep — 档位偏移 (e.g. -2 = ATM 下方第 2 档)
 * @param {number[]} availableStrikes — 已排序的离散行权价数组 (升序)
 * @returns {number} 吸附后的行权价
 *
 * @example
 * snapToStrike(502.30, 0, [495, 500, 505, 510])  → 500  (ATM)
 * snapToStrike(502.30, -2, [495, 500, 505, 510]) → 495  (ATM 下方 2 档 → clamp)
 * snapToStrike(502.30, +1, [495, 500, 505, 510]) → 510  (ATM 上方 1 档)
 */
export function snapToStrike(spotPrice, strikeStep, availableStrikes) {
    if (!availableStrikes || availableStrikes.length === 0) {
        // Fallback: 无期权链数据时，返回现价取整
        return Math.round(spotPrice);
    }

    // ── Step 1: 找 ATM 索引 (最小距离) ──
    // 使用线性扫描 (期权链通常 <50 档，O(n) 足够)
    let atmIdx = 0;
    let minDist = Math.abs(availableStrikes[0] - spotPrice);

    for (let i = 1; i < availableStrikes.length; i++) {
        const dist = Math.abs(availableStrikes[i] - spotPrice);
        if (dist < minDist) {
            minDist = dist;
            atmIdx = i;
        }
        // 已排序 → 距离开始增大时可以提前退出
        if (dist > minDist) break;
    }

    // ── Step 2: 应用档位偏移 ──
    const targetIdx = atmIdx + strikeStep;

    // ── Step 3: 边界 clamp ──
    const clampedIdx = Math.max(0, Math.min(availableStrikes.length - 1, targetIdx));

    return availableStrikes[clampedIdx];
}

/**
 * ┌─────────────────────────────────────────────────────────────────┐
 * │ 策略模板解析 — 将 JSON 骨架转换为 currentLegs 数组              │
 * │                                                                 │
 * │ 模板中的每条腿使用相对值:                                       │
 * │   - strikeStep: 相对于 ATM 的档位偏移                           │
 * │   - dteOffset:  相对于基准日期的天数偏移                         │
 * │                                                                 │
 * │ 本函数将这些相对值"实例化"为绝对值:                              │
 * │   strikeStep = -2 + spot = 502 → snap → 495                    │
 * │   dteOffset  = 30 + baseDate → '2026-04-17'                    │
 * └─────────────────────────────────────────────────────────────────┘
 *
 * @param {Object} template — 策略模板 (see templates.json)
 * @param {number} spotPrice — 当前标的价格
 * @param {number[]} availableStrikes — 该到期日的离散行权价数组 (升序)
 * @param {string} baseExpiration — 基准到期日 ISO string (e.g. '2026-03-20')
 * @returns {Array} 可直接赋值给 currentLegs 的数组
 */
export function resolveTemplate(template, spotPrice, availableStrikes, baseExpiration) {
    if (!template?.legs) return [];

    const baseDate = new Date(baseExpiration);

    return template.legs.map((tl) => {
        // ── 计算行权价: strikeStep → 离散吸附 ──
        const strike = tl.type === "stock"
            ? spotPrice
            : snapToStrike(spotPrice, tl.strikeStep || 0, availableStrikes);

        // ── 计算到期日: dteOffset → 绝对日期 ──
        let expiration = null;
        if (tl.type === "option") {
            const expDate = new Date(baseDate);
            expDate.setDate(expDate.getDate() + (tl.dteOffset || 0));
            expiration = expDate.toISOString().split("T")[0];
        }

        return {
            id: crypto.randomUUID(),
            type: tl.type || "option",
            right: tl.right || "put",
            action: tl.action || "sell",
            expiration,
            strike,
            quantity: tl.qty || 1,
            price: 0, // 价格需后续从期权链获取
            multiplier: tl.type === "stock" ? 1 : 100,
        };
    });
}

/**
 * 期权链缓存管理器 — 同一 ticker+date 缓存 30 秒
 */
const _chainCache = new Map();
const CHAIN_TTL_MS = 30_000;

/**
 * 获取迷你期权链 (带缓存)
 *
 * @param {string} ticker
 * @param {string} date — ISO date string
 * @returns {Promise<{calls: Array, puts: Array, strikes: number[]}>}
 */
export async function fetchOptionChainMini(ticker, date) {
    const key = `${ticker}:${date}`;
    const cached = _chainCache.get(key);

    if (cached && Date.now() - cached.ts < CHAIN_TTL_MS) {
        return cached.data;
    }

    const resp = await fetch(
        `/api/v1/market_data/option_chain_mini?ticker=${encodeURIComponent(ticker)}&date=${encodeURIComponent(date)}`
    );

    if (!resp.ok) {
        throw new Error(`Option chain fetch failed: HTTP ${resp.status}`);
    }

    const data = await resp.json();

    // 提取唯一行权价 (升序排列)
    const strikesSet = new Set();
    (data.calls || []).forEach((c) => strikesSet.add(c.strike));
    (data.puts || []).forEach((p) => strikesSet.add(p.strike));
    data.strikes = [...strikesSet].sort((a, b) => a - b);

    _chainCache.set(key, { data, ts: Date.now() });
    return data;
}

/**
 * 获取可用到期日列表 (带缓存)
 *
 * @param {string} ticker
 * @returns {Promise<string[]>}
 */
export async function fetchExpirations(ticker) {
    const key = `exp:${ticker}`;
    const cached = _chainCache.get(key);

    if (cached && Date.now() - cached.ts < CHAIN_TTL_MS) {
        return cached.data;
    }

    const resp = await fetch(
        `/api/v1/market_data/expirations?ticker=${encodeURIComponent(ticker)}`
    );

    if (!resp.ok) throw new Error(`Expirations fetch failed: HTTP ${resp.status}`);

    const data = await resp.json();
    const expirations = Array.isArray(data.expirations) ? data.expirations
        : Array.isArray(data) ? data
            : [];

    _chainCache.set(key, { data: expirations, ts: Date.now() });
    return expirations;
}

export default {
    snapToStrike,
    resolveTemplate,
    fetchOptionChainMini,
    fetchExpirations,
};
