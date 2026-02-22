// ══════════════════════════════════════════════════════════════════
// AlphaTheta v2 — Dashboard View Controller
// ══════════════════════════════════════════════════════════════════
//
// 负责 "大盘概览" Tab:
// - 宏观雷达卡片 (VIX / SPY / QQQ)
// - 信号引擎面板
// - 持仓表渲染
// - Top 3 智能推荐
// ══════════════════════════════════════════════════════════════════

import { getState, setState, subscribe, t, MOCK_DATA } from "../store/index.js";
import * as api from "../api/services.js";

const $ = (id) => document.getElementById(id);

// ── 模块状态 ────────────────────────────────────────────────────
let _pollTimer = null;

// ── 从后端 /dashboard/sync 拉取行情 ────────────────────────────
async function fetchDashboardData() {
    try {
        const resp = await fetch("/api/v1/dashboard/sync");
        if (!resp.ok) return;
        const data = await resp.json();

        // ── 映射 API 响应 → MOCK_DATA 兼容结构 ──
        // API 返回 data.market, MOCK_DATA 用 radar
        if (data.market) {
            const m = data.market;
            MOCK_DATA.radar.vix = m.vix || MOCK_DATA.radar.vix;
            if (m.spy) {
                MOCK_DATA.radar.spy.price = m.spy.price || MOCK_DATA.radar.spy.price;
                if (m.spy.sma200) MOCK_DATA.radar.spy.sma200 = m.spy.sma200;
                if (m.spy.sma200_distance !== undefined) {
                    MOCK_DATA.radar.spy.trend = m.spy.sma200_distance > 0 ? "bullish" : "bearish";
                }
            }
            if (m.qqq) {
                MOCK_DATA.radar.qqq.price = m.qqq.price || MOCK_DATA.radar.qqq.price;
            }
        }

        // API 返回 data.signal, MOCK_DATA 用 currentSignal
        if (data.signal) {
            const s = data.signal;
            MOCK_DATA.currentSignal.action = s.reasoning || s.action_type || MOCK_DATA.currentSignal.action;
            MOCK_DATA.currentSignal.actionType = s.action_type || MOCK_DATA.currentSignal.actionType;
            if (s.ai_reasons) MOCK_DATA.currentSignal.rationale = s.ai_reasons;
            if (s.scene_label) MOCK_DATA.currentSignal.sceneLabel = s.scene_label;
        }

        if (data.portfolio) Object.assign(MOCK_DATA.portfolio, data.portfolio);

        // marketContext 供 signal.js 使用
        if (data.market) {
            MOCK_DATA.marketContext = {
                vix: data.market.vix,
                rsi_14: data.market.spy?.rsi_14 || 50,
                distance_to_sma200: data.market.spy?.sma200_distance || 0,
                iv_rank: MOCK_DATA.radar.ivRank?.spy || 42,
                projectedMarginUtil: MOCK_DATA.portfolio.marginUsed || 0,
            };
        }

        renderDashboard();
    } catch (err) {
        console.warn("[Dashboard] fetchDashboardData failed:", err);
    }
}

// ── 渲染仪表盘 ─────────────────────────────────────────────────
function renderDashboard() {
    const d = MOCK_DATA;
    const isZh = getState("lang") === "zh";

    // Portfolio cards
    const net = $("portfolioNet");
    if (net) net.textContent = `$${d.portfolio.totalValue.toLocaleString()}`;
    const cash = $("portfolioCash");
    if (cash) cash.textContent = `$${d.portfolio.cash.toLocaleString()}`;
    const marginBar = $("marginBar");
    if (marginBar) marginBar.style.width = `${d.portfolio.marginUsed}%`;
    const marginValue = $("marginValue");
    if (marginValue) marginValue.textContent = `${d.portfolio.marginUsed}%`;

    // VIX card
    const vixVal = $("vixValue");
    if (vixVal) vixVal.textContent = d.radar.vix;
    const vixLabel = $("vixLabel");
    if (vixLabel) {
        const v = d.radar.vix;
        vixLabel.textContent =
            v < 15
                ? isZh ? "低波动 (< 15)" : "Low Vol (< 15)"
                : v > 25
                    ? isZh ? "⚠ 高波动 (> 25)" : "⚠ High Vol (> 25)"
                    : isZh ? "常态波动 (15-25)" : "Normal (15-25)";
    }

    // SPY card
    const spyPrice = $("spyPrice");
    if (spyPrice) spyPrice.textContent = `$${d.radar.spy.price}`;
    const spySma = $("spySma");
    if (spySma) {
        const pct = (((d.radar.spy.price - d.radar.spy.sma200) / d.radar.spy.sma200) * 100).toFixed(2);
        spySma.textContent = `SMA200: $${d.radar.spy.sma200} (${pct > 0 ? "+" : ""}${pct}%)`;
    }

    // QQQ card
    const qqqPrice = $("qqqPrice");
    if (qqqPrice) qqqPrice.textContent = `$${d.radar.qqq.price}`;
    const qqqSma = $("qqqSma");
    if (qqqSma) {
        const pct = (((d.radar.qqq.price - d.radar.qqq.sma200) / d.radar.qqq.sma200) * 100).toFixed(2);
        qqqSma.textContent = `SMA200: $${d.radar.qqq.sma200} (${pct > 0 ? "+" : ""}${pct}%)`;
    }

    // Signal engine card
    const sig = d.currentSignal;
    const sigAction = $("signalAction");
    if (sigAction) sigAction.textContent = sig.action;
    const sigTicker = $("sigTicker");
    if (sigTicker) sigTicker.textContent = sig.ticker;
    const sigStrike = $("sigStrike");
    if (sigStrike) sigStrike.textContent = `$${sig.strike}`;
    const sigExpiry = $("sigExpiry");
    if (sigExpiry) sigExpiry.textContent = sig.expiration;
    const sigQty = $("sigQuantity");
    if (sigQty) sigQty.textContent = sig.quantity;
    const sigCap = $("sigCapital");
    if (sigCap) sigCap.textContent = sig.capitalImpact;

    // Rationale
    const rationaleWrap = $("signalRationale");
    if (rationaleWrap && sig.rationale) {
        rationaleWrap.innerHTML = sig.rationale
            .map((r) => `<li>${r}</li>`)
            .join("");
    }

    // Active positions table
    renderPositionsTable(d.activePositions);
}

// ── 持仓表 (事件委托) ──────────────────────────────────────────
function renderPositionsTable(positions) {
    const tbody = $("positionsBody");
    if (!tbody) return;
    const isZh = getState("lang") === "zh";

    if (!positions || positions.length === 0) {
        tbody.innerHTML = `
        <tr>
          <td colspan="9" style="border:none;">
            <div class="positions-empty-state">
              <div class="radar-container">
                <div class="radar-ring"></div>
              </div>
              <div class="empty-state-text">
                <div class="es-title">资金已就位 ($100,000)</div>
                <div class="es-sub">全天候扫描引擎运行中，等待 LEAPS 黄金坑信号...</div>
              </div>
            </div>
          </td>
        </tr>`;
        return;
    }

    tbody.innerHTML = positions.map((pos) => {
        const pnlAbs = (pos.currentValue - pos.initialPremium) * (pos.quantity || 1) * 100;
        const costBasis = pos.initialPremium * (pos.quantity || 1) * 100;
        const pnlPct = costBasis > 0 ? (pnlAbs / costBasis) * 100 : 0;
        const sign = pnlAbs >= 0 ? "+" : "";
        const cls = pnlAbs > 0 ? "pnl-positive" : pnlAbs < 0 ? "pnl-negative" : "pnl-zero";
        return `
    <tr>
      <td class="mono">${pos.ticker}</td>
      <td>${isZh ? pos.typeCn || pos.type : pos.type}</td>
      <td class="mono">$${pos.strike}</td>
      <td>${pos.expiry}</td>
      <td class="${pos.dte <= 7 ? "dte-danger" : pos.dte <= 21 ? "dte-warn" : ""}">${pos.dte}d</td>
      <td class="mono">$${pos.initialPremium.toFixed(2)}</td>
      <td class="mono">$${pos.currentValue.toFixed(2)}</td>
      <td><span class="${cls}">${sign}$${Math.abs(pnlAbs).toFixed(2)} (${sign}${pnlPct.toFixed(1)}%)</span></td>
      <td>
        <button class="action-btn close-btn" data-action="close" data-ticker="${pos.ticker}">平仓</button>
        <button class="action-btn roll-btn" data-action="roll" data-ticker="${pos.ticker}"
                data-strike="${pos.strike}" data-expiry="${pos.expiry}"
                data-dte="${pos.dte}" data-premium="${pos.initialPremium}">展期</button>
      </td>
    </tr>`;
    }).join("");
}

// ── Top Picks Manager ──────────────────────────────────────────
const TopPicksManager = {
    _TIMEOUT_MS: 15000,

    async fetchTopPicks() {
        const container = $("topPicksContainer");
        if (!container) return;

        container.innerHTML = '<div style="text-align:center;color:#64748b;padding:20px;">⏳ 正在扫描票池...</div>';

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this._TIMEOUT_MS);

        try {
            const resp = await fetch("/api/v1/dashboard/scan", { signal: controller.signal });
            if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
            const raw = await resp.json();
            // API returns { signals: [...] }, TopPicks expects { picks: [...] }
            const data = { picks: raw.signals || [], scanned: raw.pool?.length || 0 };

            if (!data.picks || data.picks.length === 0) {
                const msg = "暂无符合条件的推荐标的，建议观望。";
                container.innerHTML = `
          <div style="text-align:center;padding:24px;">
            <div style="font-size:28px;margin-bottom:8px;">📭</div>
            <div style="color:#94a3b8;font-size:13px;">${msg}</div>
            ${data.scanned ? `<div style="color:#475569;font-size:11px;margin-top:6px;">已扫描 ${data.scanned} 个标的</div>` : ""}
          </div>`;
                return;
            }

            this.renderCards(data.picks, container);
        } catch (err) {
            const isTimeout = err.name === "AbortError";
            const errMsg = isTimeout
                ? "⚠️ 扫描超时 (>15s)，yfinance 可能拥堵，请稍后重试。"
                : `⚠️ 扫描异常: ${err.message || "未知错误"}，请检查后端网络后重试。`;
            container.innerHTML = `
        <div style="text-align:center;padding:20px;">
          <div style="color:#ef4444;font-size:13px;margin-bottom:10px;">${errMsg}</div>
          <button onclick="TopPicksManager.fetchTopPicks()"
            style="background:rgba(239,68,68,0.15);color:#ef4444;border:1px solid rgba(239,68,68,0.3);
                   padding:6px 16px;border-radius:6px;cursor:pointer;font-size:12px;">
            🔄 重试
          </button>
        </div>`;
            console.warn("[TopPicks] fetchTopPicks failed:", err);
        } finally {
            clearTimeout(timeoutId);
        }
    },

    renderCards(picks, container) {
        if (picks.length === 0) {
            container.innerHTML = '<div style="text-align:center;color:#64748b;padding:20px;">暂无推荐</div>';
            return;
        }
        container.innerHTML = picks.map((p, i) => `
      <div class="tp-card" onclick="window.setGlobalTicker?.('${p.ticker}')" title="点击切换全局标的">
        <div class="tp-rank">#${i + 1}</div>
        <div class="tp-ticker">${p.ticker}</div>
        <div class="tp-price">$${p.current_price}</div>
        <div class="tp-yield">
          <span class="tp-yield-val">${p.premium_yield}%</span>
          <span class="tp-yield-label">Premium Yield</span>
        </div>
        <div class="tp-meta">
          ${p.next_earnings ? `<span class="tp-safe">✅ 财报安全</span>` : '<span class="tp-safe">ℹ️ 无财报数据</span>'}
          <span class="tp-dte">DTE ${p.dte || "—"}</span>
        </div>
      </div>
    `).join("");
    },
};

// 暴露给 onclick retry 按钮
window.TopPicksManager = TopPicksManager;

// ── 导出 View Controller ────────────────────────────────────────

export function initDashboardView() {
    console.log("[Dashboard] init");

    // K线图表初始化 (legacy renderCharts.js global)
    if (typeof initDashboardCharts === "function") {
        try {
            initDashboardCharts();
            console.log("[Dashboard] ✅ Charts initialized");
        } catch (e) {
            console.warn("[Dashboard] Charts init failed:", e);
        }
    }

    // 事件委托: 持仓表按钮
    const tbody = $("positionsBody");
    if (tbody) {
        tbody.addEventListener("click", (e) => {
            const btn = e.target.closest("[data-action]");
            if (!btn) return;
            if (btn.dataset.action === "roll") {
                // Phase 3.4 实现后调用 RollManager
                console.log("[Dashboard] Roll clicked:", btn.dataset.ticker);
            }
        });
    }

    // 首次拉取
    fetchDashboardData();
    TopPicksManager.fetchTopPicks();

    // 定时轮询
    _pollTimer = setInterval(fetchDashboardData, 30000);
}

export function onShow() {
    // ECharts resize (如果有图表)
    const section = $("view-dashboard");
    if (section) {
        requestAnimationFrame(() => {
            section.querySelectorAll("[_echarts_instance_]").forEach((el) => {
                const chart = echarts?.getInstanceByDom(el);
                if (chart) chart.resize();
            });
        });
    }
}

export function onHide() {
    // 暂停轮询 (优化: 不在后台浪费请求)
    if (_pollTimer) {
        clearInterval(_pollTimer);
        _pollTimer = null;
    }
}

export default { init: initDashboardView, onShow, onHide };
