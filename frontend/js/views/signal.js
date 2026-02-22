// ══════════════════════════════════════════════════════════════════
// AlphaTheta v2 — Signal View Controller
// ══════════════════════════════════════════════════════════════════
//
// 负责 "信号与执行" Tab:
// - 期权链表格
// - 三段式分析面板 + 风控面板
// - Timing Decision Tree + CRO Risk Evaluator
// - 下单/批量操作
// ══════════════════════════════════════════════════════════════════

import { getState, subscribe, MOCK_DATA } from "../store/index.js";

const $ = (id) => document.getElementById(id);

let _pollTimer = null;
let SIGNAL_DATA = null;

// ── 获取信号数据 ────────────────────────────────────────────────
async function fetchSignalData() {
    try {
        const resp = await fetch("/api/v1/dashboard/sync");
        if (!resp.ok) return;
        const data = await resp.json();
        SIGNAL_DATA = data;

        // 合并到 MOCK_DATA
        if (data.currentSignal) Object.assign(MOCK_DATA.currentSignal, data.currentSignal);
        if (data.marketContext) Object.assign(MOCK_DATA.marketContext, data.marketContext);

        renderSignal();
    } catch (err) {
        console.warn("[Signal] fetchSignalData failed:", err);
    }
}

// ── 格式化资金数 ────────────────────────────────────────────────
function _formatCap(cap) {
    if (typeof cap === "string") return cap;
    if (typeof cap === "number") {
        return cap >= 0 ? `+$${cap.toLocaleString()}` : `-$${Math.abs(cap).toLocaleString()}`;
    }
    return String(cap);
}

// ── 渲染信号面板 ────────────────────────────────────────────────
function renderSignal() {
    const sig = MOCK_DATA.currentSignal || {};
    const ctx = MOCK_DATA.marketContext || {};  // 防御: 首次渲染时 API 尚未返回
    const isZh = getState("lang") === "zh";

    // 信号卡片
    const action = $("signalAction2") || $("signalAction");
    if (action) action.textContent = sig.action;

    // 分析面板
    renderAnalysisPanel(ctx, isZh);
    renderRiskPanel(ctx, isZh);

    // Timing decision
    const timingResult = evaluateTimingDecision(ctx);
    renderTimingPanel(timingResult, isZh);

    // CRO evaluation
    const croResult = evaluateTradeProposal(sig, ctx);
    renderCRO(croResult, isZh);
}

// ── 三段式分析面板 ──────────────────────────────────────────────
function renderAnalysisPanel(ctx, isZh) {
    const panel = $("analysisPanel");
    if (!panel) return;

    const rows = [
        { label: isZh ? "隐含波动率排名" : "IV Rank", value: `${ctx.iv_rank || 0}%`, color: (ctx.iv_rank || 0) > 50 ? "#22c55e" : "#f59e0b" },
        { label: isZh ? "历史波动率 (30d)" : "HV 30d", value: `${ctx.hv_30d || 0}%`, color: "#64748b" },
        { label: "RSI (14)", value: ctx.rsi_14 || "—", color: (ctx.rsi_14 > 70 || ctx.rsi_14 < 30) ? "#ef4444" : "#22c55e" },
        { label: isZh ? "距 SMA200" : "Dist to SMA200", value: `${ctx.distance_to_sma200 || 0}%`, color: "#00e5ff" },
        { label: isZh ? "预测保证金" : "Proj. Margin", value: `${ctx.projectedMarginUtil || 0}%`, color: (ctx.projectedMarginUtil || 0) > 70 ? "#ef4444" : "#22c55e" },
        { label: "Delta", value: ctx.delta || "—", color: "#00e5ff" },
        { label: isZh ? "距除息日" : "Days to Ex-Div", value: `${ctx.daysToExDividend || "—"}d`, color: "#64748b" },
    ];

    panel.innerHTML = rows.map((r) => `
    <div class="analysis-row">
      <span class="analysis-label">${r.label}</span>
      <span class="analysis-value" style="color:${r.color}">${r.value}</span>
    </div>
  `).join("");
}

// ── 风控面板 ────────────────────────────────────────────────────
function renderRiskPanel(ctx, isZh) {
    const panel = $("riskPanel");
    if (!panel) return;

    const checks = [
        { label: isZh ? "Wash Sale 风险" : "Wash Sale Risk", ok: !ctx.is_wash_sale_risk },
        { label: isZh ? "预估税拖" : "Est. Tax Drag", ok: (ctx.estTaxDrag || 0) < 1, value: `${ctx.estTaxDrag || 0}%` },
        { label: isZh ? "价内状态" : "ITM Status", ok: !ctx.isITM, value: ctx.isITM ? "ITM ⚠" : "OTM ✓" },
        { label: isZh ? "数据延迟" : "Data Latency", ok: (ctx.dataLatency || 0) < 10, value: `${ctx.dataLatency || 0}s` },
    ];

    panel.innerHTML = checks.map((c) => `
    <div class="risk-row ${c.ok ? "risk-ok" : "risk-warn"}">
      <span>${c.ok ? "✅" : "⚠️"} ${c.label}</span>
      ${c.value ? `<span class="risk-value">${c.value}</span>` : ""}
    </div>
  `).join("");
}

// ── Timing Decision Tree ────────────────────────────────────────
function evaluateTimingDecision(ctx) {
    const rsi = ctx?.rsi_14 || 50;
    const vix = ctx?.vix || MOCK_DATA.radar.vix || 18;
    const hasPosition = ctx?.current_position && ctx.current_position !== "none";

    let action = "hold";
    let reasoning = [];

    if (vix > 30) {
        action = hasPosition ? "sell_call" : "hold";
        reasoning.push(`VIX ${vix} > 30: 极端恐慌`);
    } else if (rsi < 30) {
        action = hasPosition ? "sell_put" : "buy_stock";
        reasoning.push(`RSI ${rsi} < 30: 超卖信号`);
    } else if (rsi > 70) {
        action = hasPosition ? "sell_call" : "hold";
        reasoning.push(`RSI ${rsi} > 70: 超买信号`);
    } else if (vix < 15 && rsi > 40 && rsi < 60) {
        action = hasPosition ? "buy_write" : "buy_stock";
        reasoning.push(`VIX ${vix} < 15 + RSI 中性: 适合建仓`);
    } else {
        action = hasPosition ? "sell_call" : "hold";
        reasoning.push(`VIX ${vix}, RSI ${rsi}: 常规市场`);
    }

    return { action, reasoning, rsi, vix, hasPosition };
}

function renderTimingPanel(result, isZh) {
    const panel = $("timingPanel");
    if (!panel) return;

    const actionLabels = {
        buy_stock: isZh ? "仅买入正股" : "Buy Stock Only",
        sell_call: isZh ? "仅卖出看涨期权" : "Sell Call Only",
        sell_put: isZh ? "仅卖出看跌期权" : "Sell Put Only",
        buy_write: isZh ? "组合建仓 (Buy-Write)" : "Buy-Write Combo",
        hold: isZh ? "观望" : "Hold",
    };

    panel.innerHTML = `
    <div class="timing-action">${actionLabels[result.action] || result.action}</div>
    <div class="timing-meta">
      <span>RSI: ${result.rsi}</span>
      <span>VIX: ${result.vix}</span>
      <span>${result.hasPosition ? (isZh ? "已持仓" : "Holding") : (isZh ? "纯现金" : "Cash")}</span>
    </div>
    <div class="timing-reasoning">${result.reasoning.join(" | ")}</div>
  `;
}

// ── CRO Risk Evaluator ──────────────────────────────────────────
function evaluateTradeProposal(sig, ctx) {
    ctx = ctx || {};  // 防御: API 数据不完整时 ctx 可能为 undefined
    const checks = [];
    let approved = true;

    if ((ctx.projectedMarginUtil || 0) > 80) {
        checks.push({ ok: false, msg: "保证金使用率 > 80%" });
        approved = false;
    } else {
        checks.push({ ok: true, msg: `保证金 ${ctx.projectedMarginUtil}% (< 80%)` });
    }

    if (ctx.is_wash_sale_risk) {
        checks.push({ ok: false, msg: "存在 Wash Sale 风险" });
        approved = false;
    } else {
        checks.push({ ok: true, msg: "无 Wash Sale 风险" });
    }

    if ((ctx.dataLatency || 0) > 10) {
        checks.push({ ok: false, msg: `数据延迟 ${ctx.dataLatency}s (> 10s)` });
        approved = false;
    } else {
        checks.push({ ok: true, msg: `数据延迟 ${ctx.dataLatency}s` });
    }

    return { approved, checks };
}

function renderCRO(result, isZh) {
    const panel = $("croPanel");
    if (!panel) return;

    const statusText = result.approved
        ? (isZh ? "✓ 风控通过" : "✓ Risk Approved")
        : (isZh ? "✗ 风控否决" : "✗ Risk Rejected");

    panel.innerHTML = `
    <div class="cro-status ${result.approved ? "cro-approved" : "cro-rejected"}">${statusText}</div>
    ${result.checks.map((c) => `
      <div class="cro-check ${c.ok ? "cro-ok" : "cro-fail"}">
        ${c.ok ? "✅" : "❌"} ${c.msg}
      </div>
    `).join("")}
  `;
}

// ── 执行按钮: 防连点 ───────────────────────────────────────────
function setupExecuteButton() {
    const btn = $("executeBtn");
    if (!btn) return;

    btn.addEventListener("click", async () => {
        if (getState("isHalted")) return;
        btn.disabled = true;
        btn.textContent = getState("lang") === "zh" ? "执行中..." : "Executing...";

        try {
            // TODO: 调用真实下单 API
            await new Promise((r) => setTimeout(r, 1500));
            btn.textContent = getState("lang") === "zh" ? "指令已发送 ✓" : "Order Sent ✓";
            setTimeout(() => {
                btn.textContent = getState("lang") === "zh" ? "通过 API 自动执行" : "Execute via API";
                btn.disabled = false;
            }, 2000);
        } catch (err) {
            btn.textContent = "Error";
            btn.disabled = false;
        }
    });
}

// ── 导出 View Controller ────────────────────────────────────────

export function initSignalView() {
    console.log("[Signal] init");

    // 订阅全局标的变化
    subscribe("activeTicker", (ticker) => {
        console.log("[Signal] activeTicker changed to:", ticker);
        fetchSignalData();
    });

    setupExecuteButton();
    fetchSignalData();
    _pollTimer = setInterval(fetchSignalData, 30000);
}

export function onShow() {
    if (!_pollTimer) {
        fetchSignalData();
        _pollTimer = setInterval(fetchSignalData, 30000);
    }
}

export function onHide() {
    if (_pollTimer) {
        clearInterval(_pollTimer);
        _pollTimer = null;
    }
}

export default { init: initSignalView, onShow, onHide };
