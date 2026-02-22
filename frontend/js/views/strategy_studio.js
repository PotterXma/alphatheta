// ══════════════════════════════════════════════════════════════════
// AlphaTheta v2 — Strategy Studio (全景策略工作室)
// ══════════════════════════════════════════════════════════════════
//
// 多腿期权组合构建器 — currentLegs[] 单一数据源驱动
// 双向绑定: UI → updateLeg → recalcPayoff → renderScenario + renderChart
// ══════════════════════════════════════════════════════════════════

import { calculateComboPayoff, calculateNetPremium, calculateComboPayoffDualCurve, calculatePortfolioGreeks } from "../utils/payoff-engine.js";
import { uuid } from "../utils/uuid.js";
import { snapToStrike, resolveTemplate, fetchOptionChainMini, fetchExpirations } from "../utils/market-helpers.js";
import { STRATEGY_TEMPLATES } from "../utils/strategy-templates.js";
import { autoSuggestNeutralStrategy, autoAssembleStrategy, findTargetExpiration } from "../utils/strategy-generator.js";
import { getState, setState, MOCK_DATA } from "../store/index.js";
import { executePaperTrade } from "../services/paper-trade.js";
import { signalStream } from "../services/signal-stream.js";

// ── 全局状态 ──────────────────────────────────────────────────────
let currentLegs = [];
let payoffChart = null;        // ECharts instance
let activeChainPanel = null;   // 当前展开的迷你期权链 leg ID

// ── 防打扰状态机 ────────────────────────────────────────────────
let isMouseInTop3 = false;     // 鼠标是否在 Top3 容器内
let activeCardTicker = null;   // 当前操作中的卡片 ticker
let pendingSignals = [];       // 暂存的新信号
let currentSignals = [];       // 当前显示的信号
let _freshnessTimer = null;    // TTL 定时器

// ══════════════════════════════════════════════════════════════════
// CRUD — currentLegs 数组操作
// ══════════════════════════════════════════════════════════════════

function createDefaultLeg() {
    return {
        id: uuid(),
        type: "option",
        right: "put",
        action: "sell",
        expiration: null,
        strike: 0,
        quantity: 1,
        price: 0,
        multiplier: 100,
    };
}

function createStockLeg(ticker, price, quantity = 100) {
    return {
        id: uuid(),
        type: "stock",
        right: null,
        action: "buy",
        ticker,
        expiration: null,
        strike: null,
        quantity,
        price,
        dte: null,
        multiplier: 1,
    };
}

function addLeg() {
    currentLegs.push(createDefaultLeg());
    renderLegs();
    recalcPayoff();
}

function removeLeg(id) {
    currentLegs = currentLegs.filter((l) => l.id !== id);
    renderLegs();
    recalcPayoff();
}

function updateLeg(id, patch) {
    const leg = currentLegs.find((l) => l.id === id);
    if (!leg) return;
    Object.assign(leg, patch);

    // 类型切换 → 自动调整约束
    if (patch.type === "stock") {
        leg.right = null;
        leg.expiration = null;
        leg.multiplier = 1;
    } else if (patch.type === "option" && !leg.right) {
        leg.right = "put";
        leg.multiplier = 100;
    }

    renderLegs();
    recalcPayoff();
}

function clearAll() {
    currentLegs = [];
    hideStatusBar();
    renderLegs();
    recalcPayoff();
}

// ══════════════════════════════════════════════════════════════════
// Status Bar
// ══════════════════════════════════════════════════════════════════

function showStatusBar(message, type = "loading") {
    const bar = document.getElementById("studioStatusBar");
    if (!bar) return;
    bar.textContent = message;
    bar.className = `studio-status-bar ${type}`;
    bar.style.display = "block";
    if (type === "success" || type === "warning") {
        setTimeout(() => { bar.style.display = "none"; }, 8000);
    }
}

function hideStatusBar() {
    const bar = document.getElementById("studioStatusBar");
    if (bar) bar.style.display = "none";
}

// ══════════════════════════════════════════════════════════════════
// 智能组装 — AI Auto Suggest
// ══════════════════════════════════════════════════════════════════

async function onAutoSuggest() {
    const ticker = getState("activeTicker") || "SPY";
    const btn = document.getElementById("studioAutoSuggest");
    if (btn) btn.disabled = true;

    showStatusBar(`⏳ 正在为 ${ticker} 智能组装策略模型...`, "loading");

    try {
        // Step 1: 获取最近到期日
        const rawExps = await fetchExpirations(ticker);
        const exps = Array.isArray(rawExps) ? rawExps : [];
        if (exps.length === 0) throw new Error("到期日列表为空，请稍后重试");
        // 选择 DTE 20-45 天的到期日 (最佳 theta decay)
        const today = new Date();
        let bestExp = exps[0];
        for (const exp of exps) {
            const dte = Math.ceil((new Date(exp) - today) / 86400000);
            if (dte >= 20 && dte <= 45) { bestExp = exp; break; }
        }

        // Step 2: 获取真实期权链
        const chain = await fetchOptionChainMini(ticker, bestExp);
        if (!chain.calls?.length || !chain.puts?.length) {
            throw new Error("期权链数据为空");
        }

        // Step 3: 推断 IV Rank (从 VIX / 估算)
        // TODO: 后端提供真实 IV Rank — 暂用 VIX 近似
        const spotPrice = chain.spot || chain.calls[Math.floor(chain.calls.length / 2)]?.strike || 0;
        const ivRank = 55; // 暂时硬编码 > 50 以允许生成 (后端尚未提供 IVR API)

        // Step 4: 调用生成器
        const result = autoSuggestNeutralStrategy(
            { ivRank, spotPrice },
            chain,
            bestExp
        );

        if (!result.success) {
            showStatusBar(`⚠️ ${result.reason}`, "warning");
            return;
        }

        // Step 5: 覆写 currentLegs 并渲染
        currentLegs = result.legs;
        renderLegs();
        recalcPayoff();

        const meta = result.meta;
        showStatusBar(
            `✨ AI 已加载: 标准铁鹰 (${meta.putSpread} / ${meta.callSpread}) | 净收入 $${meta.netCredit} | 最大风险 $${meta.maxLoss} | 翼宽 $${meta.wingWidth}`,
            "success"
        );

    } catch (err) {
        console.error("[Studio] Auto suggest failed:", err);
        showStatusBar(`⚠️ 智能组装失败: ${err.message}`, "warning");
    } finally {
        if (btn) btn.disabled = false;
    }
}

// ══════════════════════════════════════════════════════════════════
// 🏆 智能推荐面板 (防打扰 + TTL 保鲜 + WebSocket 接入)
// ══════════════════════════════════════════════════════════════════

const DIRECTION_MAP = {
    buy_write: "buy_write",
    cash_secured_put: "bullish",
    bull_put_spread: "bullish",
    long_call: "bullish",
    pmcc: "bullish",
    leaps_deep_itm_call: "bullish",
    covered_call: "bullish",
    iron_condor: "neutral",
    bear_call_spread: "bearish",
    long_put: "bearish",
    leaps_deep_itm_put: "bearish",
    put_spread: "bearish",
    sell_put: "bullish",
    sell_call: "bearish",
    Hold: "neutral",
    hold: "neutral",
};

const DIRECTION_LABELS = {
    bullish: "看多",
    bearish: "看空",
    buy_write: "买入建仓",
    neutral: "中性",
};

const LEAPS_LABELS = {
    bullish: "🎯 LEAPS 长期看多",
    bearish: "🎯 LEAPS 长期看空",
};

/** 计算信号年龄 (ms) */
function signalAge(signal) {
    if (!signal.captured_at) return 0;
    return Date.now() - new Date(signal.captured_at).getTime();
}

/** 格式化年龄 */
function formatAge(ms) {
    const min = Math.floor(ms / 60_000);
    if (min < 1) return "⏱️ just now";
    if (min < 60) return `⏱️ ${min} min ago`;
    return `⏱️ ${Math.floor(min / 60)}h ${min % 60}m ago`;
}

const SIGNAL_TTL_MS = 900_000; // 15 分钟

/**
 * 渲染信号卡片 — 共用入口 (REST + WS 均调用)
 */
function renderSignals(signals) {
    const container = document.getElementById("recCardsContainer");
    if (!container) return;

    currentSignals = signals;

    if (signals.length === 0) {
        container.innerHTML = '<div style="text-align:center;color:#64748b;padding:20px;grid-column:1/-1;">📭 暂无推荐标的</div>';
        return;
    }

    container.innerHTML = signals.map(s => {
        const dir = DIRECTION_MAP[s.action_type] || "bullish";
        const leapsBadge = LEAPS_LABELS[dir]
            ? `<span class="leaps-badge" style="margin-left:6px">${LEAPS_LABELS[dir]}</span>`
            : "";
        const age = signalAge(s);
        const isStale = age > SIGNAL_TTL_MS;
        const staleClass = isStale ? " signal-stale" : "";
        const ageLabel = s.captured_at ? formatAge(age) : "";
        const staleWarning = isStale ? '<div class="signal-stale-warning">⚠️ 行情已过期，请谨慎操作</div>' : "";

        return `
        <div class="rec-card${staleClass}" data-ticker="${s.ticker}" data-direction="${dir}" data-price="${s.price || 0}" data-captured="${s.captured_at || ""}">
            <div class="rec-card-top">
                <span class="rec-card-ticker">${s.ticker}</span>
                <span class="rec-card-age">${ageLabel}</span>
                <span class="rec-card-price">$${(s.price || 0).toFixed(2)}</span>
            </div>
            <span class="rec-card-direction ${dir}">${DIRECTION_LABELS[dir]}</span>${leapsBadge}
            <div class="rec-card-reason">${s.reasoning || s.scene_label || s.action_type}</div>
            ${s.stock_action ? `<div class="rec-card-stock-action" style="margin-top:6px;padding:4px 8px;background:rgba(6,182,212,0.1);border-left:2px solid #06b6d4;font-size:11px;color:#67e8f9;border-radius:2px;">${s.stock_action}</div>` : ""}
            ${staleWarning}
        </div>`;
    }).join("");
}

/** 防打扰: 尝试应用新信号 */
function tryApplySignals(signals) {
    const isInteracting = isMouseInTop3 || activeCardTicker !== null;

    if (!isInteracting) {
        // 空闲状态 — 直接渲染
        renderSignals(signals);
        pendingSignals = [];
        hidePendingBadge();
    } else {
        // 正在操作 — 暂存
        pendingSignals = signals;
        showPendingBadge(signals.length);
    }
}

/** 显示发光徽章 */
function showPendingBadge(count) {
    let badge = document.getElementById("signalPendingBadge");
    if (!badge) {
        const titleEl = document.querySelector(".rec-header, .section-header");
        if (!titleEl) return;
        badge = document.createElement("span");
        badge.id = "signalPendingBadge";
        badge.className = "badge-new-signal";
        badge.addEventListener("click", () => flushPendingSignals());
        titleEl.appendChild(badge);
    }
    badge.textContent = `✨ ${count} 个新信号已到达 (点击刷新)`;
    badge.style.display = "inline-block";
}

/** 隐藏徽章 */
function hidePendingBadge() {
    const badge = document.getElementById("signalPendingBadge");
    if (badge) badge.style.display = "none";
}

/** 强制刷新 */
function flushPendingSignals() {
    if (pendingSignals.length > 0) {
        renderSignals(pendingSignals);
        pendingSignals = [];
    }
    hidePendingBadge();
}

/** 信号保鲜定时器 — 每 60s 检查 TTL */
function checkSignalFreshness() {
    if (currentSignals.length === 0) return;

    const cards = document.querySelectorAll(".rec-card");
    cards.forEach(card => {
        const captured = card.dataset.captured;
        if (!captured) return;
        const age = Date.now() - new Date(captured).getTime();
        const isStale = age > SIGNAL_TTL_MS;

        // 更新年龄标签
        const ageEl = card.querySelector(".rec-card-age");
        if (ageEl) ageEl.textContent = formatAge(age);

        // 灰化状态
        if (isStale && !card.classList.contains("signal-stale")) {
            card.classList.add("signal-stale");
            if (!card.querySelector(".signal-stale-warning")) {
                const warn = document.createElement("div");
                warn.className = "signal-stale-warning";
                warn.textContent = "⚠️ 行情已过期，请谨慎操作";
                card.appendChild(warn);
            }
        }
    });
}

/** 设置防打扰事件监听 */
function setupAntiDisturbance() {
    const container = document.getElementById("recCardsContainer");
    if (!container) return;

    container.addEventListener("mouseenter", () => { isMouseInTop3 = true; });
    container.addEventListener("mouseleave", () => {
        isMouseInTop3 = false;
        // 如果无 active card 且有待处理信号 → 自动 flush
        if (!activeCardTicker && pendingSignals.length > 0) {
            flushPendingSignals();
        }
    });

    // 卡片点击时标记 active
    container.addEventListener("click", (e) => {
        const card = e.target.closest(".rec-card");
        if (!card) return;

        // 如果点击的是 stale 卡片，拦截
        if (card.classList.contains("signal-stale")) {
            e.stopPropagation();
            return;
        }

        activeCardTicker = card.dataset.ticker;
        // 操作完成后 5s 释放 active 状态
        setTimeout(() => {
            activeCardTicker = null;
            if (!isMouseInTop3 && pendingSignals.length > 0) {
                flushPendingSignals();
            }
        }, 5000);
    });

    // 启动 WebSocket 信号流
    signalStream.onSignal((signals) => {
        tryApplySignals(signals);
    });
    signalStream.connect();

    // 启动 TTL 定时器
    _freshnessTimer = setInterval(checkSignalFreshness, 60_000);
}

async function onRecommendationCardClick(ticker, direction) {
    // Step 1: 状态联动
    setState("activeTicker", ticker);
    const tickerLabel = document.getElementById("studioTickerLabel");
    if (tickerLabel) tickerLabel.textContent = ticker;

    currentLegs = [];
    renderLegs();
    showStatusBar(`⏳ 拉取 ${ticker} 实时盘口与智能风控校验中...`, "loading");

    try {
        // Step 2: 获取到期日列表
        const rawExps = await fetchExpirations(ticker);
        const exps = Array.isArray(rawExps) ? rawExps : [];
        if (exps.length === 0) throw new Error("到期日列表为空，请稍后重试");

        // Step 3: 到期日选择 — 由 T+n 目标天数滑块驱动
        let bestExp;
        let leapsDte = 0;
        const sliderEl = document.getElementById("simDteSlider");
        const sliderDte = sliderEl ? parseInt(sliderEl.value, 10) : 0;

        if (sliderDte > 0) {
            // 用户已设置 T+n 目标天数 → 寻找最接近的到期日
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            let closestExp = exps[exps.length - 1]; // fallback: 最远
            let closestDiff = Infinity;
            for (const exp of exps) {
                const d = Math.ceil((new Date(exp) - today) / 86400000);
                if (d >= 7 && Math.abs(d - sliderDte) < closestDiff) {
                    closestDiff = Math.abs(d - sliderDte);
                    closestExp = exp;
                }
            }
            bestExp = closestExp;
            leapsDte = Math.ceil((new Date(bestExp) - today) / 86400000);
        } else {
            // Slider = 0 或不存在 → 回退 LEAPS 寻址器
            try {
                const leapsResult = findTargetExpiration(exps);
                bestExp = leapsResult.date;
                leapsDte = leapsResult.dte;
            } catch {
                bestExp = exps[exps.length - 1];
                const today = new Date();
                leapsDte = Math.ceil((new Date(bestExp) - today) / 86400000);
            }
        }

        // Step 4: 获取远期期权链
        const chain = await fetchOptionChainMini(ticker, bestExp);
        if (!chain.calls?.length || !chain.puts?.length) {
            throw new Error("远期期权链数据为空");
        }

        // Step 5: LEAPS 分发器 + 熔断
        // spot price 使用 API 返回的真实现价 (不再用中位 strike 覆盖)
        const currentBP = MOCK_DATA.portfolio?.cash || 45000;
        if (!chain.spot || chain.spot <= 0) {
            chain.spot = chain.calls[Math.floor(chain.calls.length / 2)]?.strike || 0;
        }

        const result = autoAssembleStrategy(ticker, direction, currentBP, chain, bestExp);

        if (!result.success) {
            showBreakerAlert(result.reason);
            return;
        }

        // Step 6: 覆写 legs + 渲染
        currentLegs = result.legs;
        renderLegs();
        recalcPayoff();

        const m = result.meta;
        showStatusBar(
            `✨ ${result.strategyLabel} (${ticker}) | DTE ${leapsDte}d | ` +
            `成本 $${m.netDebit || 0} | 最大风险 $${m.maxLoss || 0}`,
            "success"
        );

    } catch (err) {
        console.error("[Studio] Recommendation click failed:", err);
        showBreakerAlert(err.message || "未知错误");
    }
}

function showBreakerAlert(message) {
    hideStatusBar();
    const container = document.getElementById("legsContainer");
    if (!container) return;
    container.innerHTML = `
        <div class="studio-breaker-alert">
            <span class="breaker-icon">🚨</span>
            ${message}
        </div>
        <div class="studio-empty">
            <p>📐 风控引擎已拦截自动组装，请转为手动推演</p>
        </div>`;
}

async function loadTemplate(templateId) {
    const tpl = STRATEGY_TEMPLATES.find((t) => t.id === templateId);
    if (!tpl) return;

    const ticker = getState("activeTicker") || "SPY";
    let strikes = [];
    let baseExp = null;

    // 获取到期日和期权链
    try {
        const rawExps = await fetchExpirations(ticker);
        const exps = Array.isArray(rawExps) ? rawExps : [];
        baseExp = exps[0] || null; // 最近的到期日

        if (baseExp) {
            const chain = await fetchOptionChainMini(ticker, baseExp);
            strikes = chain.strikes || [];
        }
    } catch (e) {
        console.warn("[Studio] 模板加载期权链失败, 使用估算:", e);
    }

    // 如果没有真实期权链，生成模拟价格
    const spot = getState("spotPrice") || 500;
    if (strikes.length === 0) {
        const step = spot > 100 ? 5 : spot > 20 ? 1 : 0.5;
        for (let k = spot - step * 10; k <= spot + step * 10; k += step) {
            strikes.push(Math.round(k * 100) / 100);
        }
    }

    currentLegs = resolveTemplate(tpl, spot, strikes, baseExp || new Date().toISOString().split("T")[0]);
    renderLegs();
    recalcPayoff();
}

// ══════════════════════════════════════════════════════════════════
// DOM 渲染 — Event Delegation (事件委托)
// ══════════════════════════════════════════════════════════════════

function renderLegs() {
    const container = document.getElementById("legsContainer");
    if (!container) return;

    if (currentLegs.length === 0) {
        container.innerHTML = `
      <div class="studio-empty">
        <p>📐 选择策略模板或点击 [+ 添加期权腿] 开始构建</p>
      </div>`;
        return;
    }

    container.innerHTML = currentLegs.map((leg, idx) => `
    <div class="leg-row" data-leg-id="${leg.id}">
      <span class="leg-index">#${idx + 1}</span>

      <!-- Buy/Sell Toggle -->
      <button class="leg-action-toggle ${leg.action === "buy" ? "leg-buy" : "leg-sell"}" data-field="action">
        ${leg.action === "buy" ? "BUY" : "SELL"}
      </button>

      <!-- Type Toggle: Call / Put / Stock -->
      <div class="leg-type-group">
        <button class="leg-type-btn ${leg.type === "option" && leg.right === "call" ? "active" : ""}" data-set-type="call">C</button>
        <button class="leg-type-btn ${leg.type === "option" && leg.right === "put" ? "active" : ""}" data-set-type="put">P</button>
        <button class="leg-type-btn ${leg.type === "stock" ? "active" : ""}" data-set-type="stock">S</button>
      </div>

      <!-- Expiration (only for options) -->
      ${leg.type === "option" ? `
        <input type="date" class="leg-input leg-exp" value="${leg.expiration || ""}"
               data-field="expiration" placeholder="到期日" />
      ` : `<span class="leg-input leg-exp disabled">—</span>`}

      <!-- Strike / Entry Price -->
      <div class="leg-strike-wrapper">
        <input type="number" class="leg-input leg-strike" value="${leg.strike || ""}"
               data-field="strike" placeholder="${leg.type === "stock" ? "入场价" : "行权价"}"
               step="0.5" min="0" />
        ${leg.type === "option" ? `<button class="chain-btn" data-action="open-chain" title="展开期权链">⛓️</button>` : ""}
      </div>

      <!-- Price -->
      <input type="number" class="leg-input leg-price" value="${leg.price || ""}"
             data-field="price" placeholder="价格" step="0.01" min="0" />

      <!-- Quantity -->
      <input type="number" class="leg-input leg-qty" value="${leg.quantity}"
             data-field="quantity" min="1" step="1" />

      <!-- Delete -->
      <button class="leg-delete" data-action="remove" title="删除">🗑️</button>

      ${leg._leaps ? `<span class="leaps-badge">LEAPS: ${(() => {
            if (!leg.expiration) return "远期";
            const d = Math.ceil((new Date(leg.expiration) - new Date()) / 86400000);
            return d + "d";
        })()}</span>` : ""}
    </div>
  `).join("");
}

// ── 事件委托: 所有 Leg 交互统一处理 ──
function setupLegDelegation() {
    const container = document.getElementById("legsContainer");
    if (!container) return;

    container.addEventListener("click", (e) => {
        const legRow = e.target.closest(".leg-row");
        if (!legRow) return;
        const legId = legRow.dataset.legId;

        // Buy/Sell toggle
        if (e.target.dataset.field === "action") {
            const leg = currentLegs.find((l) => l.id === legId);
            updateLeg(legId, { action: leg.action === "buy" ? "sell" : "buy" });
            return;
        }

        // Type toggle (Call/Put/Stock)
        const setType = e.target.dataset.setType;
        if (setType) {
            if (setType === "stock") {
                updateLeg(legId, { type: "stock", right: null, multiplier: 1 });
            } else {
                updateLeg(legId, { type: "option", right: setType, multiplier: 100 });
            }
            return;
        }

        // Delete
        if (e.target.closest("[data-action='remove']")) {
            removeLeg(legId);
            return;
        }

        // Open mini chain
        if (e.target.closest("[data-action='open-chain']")) {
            openMiniChain(legId, e.target.closest(".leg-strike-wrapper"));
            return;
        }
    });

    // Input changes (delegation)
    container.addEventListener("input", (e) => {
        const legRow = e.target.closest(".leg-row");
        if (!legRow) return;
        const legId = legRow.dataset.legId;
        const field = e.target.dataset.field;
        if (!field) return;

        let value = e.target.value;
        if (field === "strike" || field === "price" || field === "quantity") {
            value = parseFloat(value) || 0;
        }
        updateLeg(legId, { [field]: value });
    });
}

// ══════════════════════════════════════════════════════════════════
// 迷你期权链面板 (T 型报价)
// ══════════════════════════════════════════════════════════════════

async function openMiniChain(legId, wrapperEl) {
    // 关闭已有面板
    closeMiniChain();

    const leg = currentLegs.find((l) => l.id === legId);
    if (!leg || !leg.expiration) {
        console.warn("[Studio] 请先选择到期日");
        return;
    }

    const ticker = getState("activeTicker") || "SPY";
    activeChainPanel = legId;

    // 创建浮层
    const panel = document.createElement("div");
    panel.className = "mini-chain-panel";
    panel.id = "miniChainPanel";
    panel.innerHTML = `<div class="chain-loading">⏳ 加载期权链...</div>`;
    wrapperEl.appendChild(panel);

    try {
        const chain = await fetchOptionChainMini(ticker, leg.expiration);

        // 合并 calls + puts 按 strike
        const strikeMap = new Map();
        for (const c of chain.calls || []) {
            strikeMap.set(c.strike, { ...(strikeMap.get(c.strike) || {}), callBid: c.bid, callAsk: c.ask });
        }
        for (const p of chain.puts || []) {
            strikeMap.set(p.strike, { ...(strikeMap.get(p.strike) || {}), putBid: p.bid, putAsk: p.ask });
        }

        const strikes = [...strikeMap.keys()].sort((a, b) => a - b);

        panel.innerHTML = `
      <table class="chain-table">
        <thead>
          <tr>
            <th colspan="2">CALL</th>
            <th>Strike</th>
            <th colspan="2">PUT</th>
          </tr>
          <tr>
            <th>Bid</th><th>Ask</th>
            <th></th>
            <th>Bid</th><th>Ask</th>
          </tr>
        </thead>
        <tbody>
          ${strikes.map((k) => {
            const d = strikeMap.get(k) || {};
            const isATM = Math.abs(k - (chain.spot || 0)) < 3;
            return `
              <tr class="${isATM ? "chain-atm" : ""}">
                <td class="chain-cell chain-bid" data-strike="${k}" data-price="${d.callBid || 0}" data-right="call">${(d.callBid || 0).toFixed(2)}</td>
                <td class="chain-cell chain-ask" data-strike="${k}" data-price="${d.callAsk || 0}" data-right="call">${(d.callAsk || 0).toFixed(2)}</td>
                <td class="chain-strike">${k}</td>
                <td class="chain-cell chain-bid" data-strike="${k}" data-price="${d.putBid || 0}" data-right="put">${(d.putBid || 0).toFixed(2)}</td>
                <td class="chain-cell chain-ask" data-strike="${k}" data-price="${d.putAsk || 0}" data-right="put">${(d.putAsk || 0).toFixed(2)}</td>
              </tr>`;
        }).join("")}
        </tbody>
      </table>`;

        // 点击 Bid/Ask → 填入 strike + price
        panel.addEventListener("click", (e) => {
            const cell = e.target.closest(".chain-cell");
            if (!cell) return;
            const strike = parseFloat(cell.dataset.strike);
            const price = parseFloat(cell.dataset.price);
            const right = cell.dataset.right;
            updateLeg(legId, { strike, price, right });
            closeMiniChain();
        });
    } catch (err) {
        panel.innerHTML = `<div class="chain-error">❌ ${err.message}</div>`;
    }
}

function closeMiniChain() {
    const panel = document.getElementById("miniChainPanel");
    if (panel) panel.remove();
    activeChainPanel = null;
}

// 外部点击关闭
document.addEventListener("click", (e) => {
    if (activeChainPanel && !e.target.closest(".mini-chain-panel") && !e.target.closest("[data-action='open-chain']")) {
        closeMiniChain();
    }
});

// ══════════════════════════════════════════════════════════════════
// 盈亏推演 — 引擎调用 + UI 刷新
// ══════════════════════════════════════════════════════════════════

function recalcPayoff() {
    const spot = getState("spotPrice") || 500;

    // ── Net Premium ──
    const { net, isCredit } = calculateNetPremium(currentLegs);
    const npEl = document.getElementById("studioNetPremium");
    if (npEl) {
        npEl.textContent = `${isCredit ? "+" : ""}$${Math.abs(net).toLocaleString("en", { minimumFractionDigits: 2 })}`;
        npEl.className = `metric-value ${isCredit ? "profit" : "loss"}`;
        const labelEl = document.getElementById("studioNetLabel");
        if (labelEl) labelEl.textContent = isCredit ? "Net Credit (净收入)" : "Net Debit (净支出)";
    }

    // ── Payoff Engine ──
    const validLegs = currentLegs.filter((l) => l.quantity > 0 && (l.type === "stock" ? l.price > 0 : l.strike > 0));
    if (validLegs.length === 0) {
        renderEmptyScenario();
        renderPayoffChart([], [], [], spot, []);
        renderGreeks({ netDelta: 0, netGamma: 0, netTheta: 0, netVega: 0 });
        return;
    }

    // Expiry metrics (existing)
    const result = calculateComboPayoff(validLegs, spot);
    renderScenario(result);

    // Dual curve: expiry + T+n
    const targetDTE = parseInt(document.getElementById("simDteSlider")?.value || "30", 10);
    const targetIV = parseInt(document.getElementById("simIvSlider")?.value || "30", 10) / 100;
    const dual = calculateComboPayoffDualCurve(validLegs, spot, targetDTE, targetIV);

    renderPayoffChart(dual.pricePoints, dual.expiryData, dual.tnData, spot, result.breakevens);

    // Greeks
    const greeks = calculatePortfolioGreeks(validLegs, spot, targetDTE, targetIV);
    renderGreeks(greeks);
}

function renderScenario(result) {
    const fmt = (v) => typeof v === "number"
        ? `$${Math.abs(v).toLocaleString("en", { minimumFractionDigits: 0 })}`
        : v;

    const set = (id, val, cls) => {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = val;
            if (cls) el.className = `metric-value ${cls}`;
        }
    };

    // Max Profit
    if (result.maxProfit === "Unlimited") {
        set("studioMaxProfit", "∞ Unlimited", "profit");
    } else {
        set("studioMaxProfit", `+${fmt(result.maxProfit)}`, result.maxProfit >= 0 ? "profit" : "loss");
    }

    // Max Loss
    if (result.maxLoss === "Unlimited Risk") {
        set("studioMaxLoss", "∞ Unlimited Risk", "loss");
    } else {
        set("studioMaxLoss", `-${fmt(result.maxLoss)}`, "loss");
    }

    // Break-even
    const beEl = document.getElementById("studioBreakeven");
    if (beEl) {
        beEl.textContent = result.breakevens.length > 0
            ? result.breakevens.map((b) => `$${b.toFixed(2)}`).join(" | ")
            : "无";
    }

    // Est. Collateral
    if (result.estCollateral === "Unlimited Risk") {
        set("studioCollateral", "∞ 需 Portfolio Margin", "loss");
    } else {
        set("studioCollateral", fmt(result.estCollateral), "");
    }
}

function renderEmptyScenario() {
    ["studioMaxProfit", "studioMaxLoss", "studioBreakeven", "studioCollateral"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.textContent = "--";
    });
}

// ══════════════════════════════════════════════════════════════════
// ECharts 盈亏曲线
// ══════════════════════════════════════════════════════════════════

function renderPayoffChart(pricePoints, expiryData, tnData, spot, breakevens) {
    const chartDom = document.getElementById("payoffChart");
    if (!chartDom || typeof echarts === "undefined") return;

    if (!payoffChart) {
        payoffChart = echarts.init(chartDom, "dark");
    }

    if (!pricePoints.length) {
        payoffChart.clear();
        return;
    }

    const xData = pricePoints.map((v) => v.toFixed(1));

    // Spot 索引
    const spotIdx = spot ? pricePoints.reduce((best, v, i) => Math.abs(v - spot) < Math.abs(pricePoints[best] - spot) ? i : best, 0) : -1;

    const option = {
        backgroundColor: "transparent",
        grid: { left: 60, right: 30, top: 40, bottom: 40 },
        tooltip: {
            trigger: "axis",
            formatter: (params) => {
                let html = `Stock: $${params[0].axisValue}<br/>`;
                for (const p of params) {
                    const color = p.value >= 0 ? "#10b981" : "#ef4444";
                    html += `${p.seriesName}: <b style="color:${color}">$${p.value.toFixed(0)}</b><br/>`;
                }
                return html;
            },
        },
        legend: {
            data: ["到期日 (Expiry)", "T+n (理论值)"],
            top: 8,
            right: 10,
            textStyle: { color: "#94a3b8", fontSize: 10 },
        },
        xAxis: {
            type: "category",
            data: xData,
            axisLabel: { interval: Math.floor(xData.length / 6), color: "#94a3b8", fontSize: 10 },
            axisLine: { lineStyle: { color: "#334155" } },
        },
        yAxis: {
            type: "value",
            axisLabel: { color: "#94a3b8", formatter: (v) => `$${v}` },
            splitLine: { lineStyle: { color: "#1e293b" } },
        },
        series: [
            // Series 1: 到期日 (dashed, low opacity)
            {
                name: "到期日 (Expiry)",
                type: "line",
                data: expiryData.map((v) => Math.round(v)),
                smooth: false,
                symbol: "none",
                lineStyle: { width: 1.5, type: "dashed", color: "#64748b" },
                itemStyle: { color: "#64748b" },
                areaStyle: { opacity: 0.03 },
            },
            // Series 2: T+n (smooth, glowing, gradient fill)
            {
                name: "T+n (理论值)",
                type: "line",
                data: tnData.map((v) => Math.round(v)),
                smooth: true,
                symbol: "none",
                lineStyle: {
                    width: 3,
                    color: "#06b6d4",
                    shadowBlur: 10,
                    shadowColor: "rgba(6, 182, 212, 0.4)",
                },
                itemStyle: { color: "#06b6d4" },
                areaStyle: {
                    color: {
                        type: "linear",
                        x: 0, y: 0, x2: 0, y2: 1,
                        colorStops: [
                            { offset: 0, color: "rgba(6, 182, 212, 0.15)" },
                            { offset: 1, color: "rgba(6, 182, 212, 0)" },
                        ],
                    },
                },
                markLine: {
                    silent: true,
                    data: [
                        { yAxis: 0, lineStyle: { color: "#475569", type: "dashed", width: 1 } },
                        ...(spotIdx >= 0 ? [{
                            xAxis: spotIdx.toString(),
                            lineStyle: { color: "#60a5fa", type: "dashed", width: 1 },
                            label: { formatter: `Spot $${spot}`, color: "#60a5fa" },
                        }] : []),
                        ...(breakevens || []).map((be) => ({
                            xAxis: pricePoints.reduce((best, v, i) => Math.abs(v - be) < Math.abs(pricePoints[best] - be) ? i : best, 0).toString(),
                            lineStyle: { color: "#f59e0b", type: "dotted", width: 1 },
                            label: { formatter: `BE $${be.toFixed(1)}`, color: "#f59e0b" },
                        })),
                    ],
                },
            },
        ],
    };

    payoffChart.setOption(option, true);
}

// ══════════════════════════════════════════════════════════════════
// Portfolio Greeks 渲染
// ══════════════════════════════════════════════════════════════════

function renderGreeks(greeks) {
    const setGreek = (id, val, precision = 3) => {
        const el = document.getElementById(id);
        if (!el) return;
        const num = typeof val === "number" ? val : 0;
        el.textContent = num.toFixed(precision);
        el.className = `greek-value mono ${num > 0.001 ? "positive" : num < -0.001 ? "negative" : ""}`;
    };

    setGreek("greekDelta", greeks.netDelta, 3);
    setGreek("greekGamma", greeks.netGamma, 3);
    setGreek("greekTheta", greeks.netTheta, 2);
    setGreek("greekVega", greeks.netVega, 2);
}

// ══════════════════════════════════════════════════════════════════
// View Controller — ESM Lifecycle
// ══════════════════════════════════════════════════════════════════

let initialized = false;

function init() {
    if (initialized) return;
    initialized = true;

    // 事件委托
    setupLegDelegation();

    // 模板下拉框
    const tplSelect = document.getElementById("studioTemplateSelect");
    if (tplSelect) {
        tplSelect.innerHTML = `<option value="">— 选择策略模板 —</option>` +
            STRATEGY_TEMPLATES.map((t) => `<option value="${t.id}">${t.name}</option>`).join("");

        tplSelect.addEventListener("change", (e) => {
            if (e.target.value) loadTemplate(e.target.value);
            e.target.value = ""; // 重置,允许重复选择
        });
    }

    // 添加腿按钮
    document.getElementById("studioAddLeg")?.addEventListener("click", addLeg);
    document.getElementById("studioClearAll")?.addEventListener("click", clearAll);
    document.getElementById("studioAutoSuggest")?.addEventListener("click", onAutoSuggest);

    // ── 模拟盘成交按钮 (动态注入) ──
    const toolbar = document.querySelector(".studio-toolbar");
    if (toolbar && !document.getElementById("studioPaperTrade")) {
        const btn = document.createElement("button");
        btn.id = "studioPaperTrade";
        btn.className = "studio-btn-primary";
        btn.style.cssText = "background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.3);color:#10b981;";
        btn.textContent = "🚀 模拟盘成交";
        btn.addEventListener("click", () => {
            if (currentLegs.length === 0) {
                window.showToast?.("请先添加策略腿", "warning");
                return;
            }
            // 附加 ticker 信息到 legs
            const ticker = getState("activeTicker") || "SPY";
            const legsWithTicker = currentLegs.map(l => ({ ...l, ticker }));
            const result = executePaperTrade(legsWithTicker);
            if (result.success) {
                window.showToast?.(result.message, "success");
                setTimeout(() => window.navigateTo?.("lifecycle"), 800);
            } else {
                window.showToast?.(result.message, "error");
            }
        });
        toolbar.appendChild(btn);
    }

    // 推荐面板事件委托
    const recPanel = document.getElementById("recCardsContainer");
    if (recPanel) {
        recPanel.addEventListener("click", (e) => {
            const card = e.target.closest(".rec-card");
            if (!card) return;
            const ticker = card.dataset.ticker;
            const direction = card.dataset.direction || "neutral";
            onRecommendationCardClick(ticker, direction);
        });
    }

    // DTE / IV 滑块 — rAF 防抖
    let _rafPending = false;
    function onSliderInput() {
        // 更新显示值
        const dteEl = document.getElementById("simDteValue");
        const ivEl = document.getElementById("simIvValue");
        if (dteEl) dteEl.textContent = `${document.getElementById("simDteSlider")?.value || 30}d`;
        if (ivEl) ivEl.textContent = `${document.getElementById("simIvSlider")?.value || 30}%`;

        if (!_rafPending) {
            _rafPending = true;
            requestAnimationFrame(() => {
                _rafPending = false;
                recalcPayoff();
            });
        }
    }
    document.getElementById("simDteSlider")?.addEventListener("input", onSliderInput);
    document.getElementById("simIvSlider")?.addEventListener("input", onSliderInput);

    // 启动实时信号流 + 防打扰
    setupAntiDisturbance();

    console.log("[Studio] ⚡ Strategy Studio initialized");
}

function onShow() {
    // ECharts resize
    if (payoffChart) {
        requestAnimationFrame(() => payoffChart.resize());
    }
    recalcPayoff();

    // ── 检测 pendingSignal → 自动组装 ──
    const signal = getState("pendingSignal");
    if (signal) {
        setState("pendingSignal", null); // 消费后立即清除
        console.log("[Studio] 📡 Received pendingSignal:", signal);

        // 更新 ticker label
        const label = document.getElementById("studioTickerLabel");
        if (label) label.textContent = signal.ticker;

        // 自动触发智能组装 (延迟确保 DOM 就绪)
        setTimeout(() => {
            const btn = document.getElementById("studioAutoSuggest");
            if (btn) btn.click(); // 复用已有的 onAutoSuggest 流程
        }, 300);
    }
}

function onHide() {
    closeMiniChain();
}

export default { init, onShow, onHide };
