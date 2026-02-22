// ══════════════════════════════════════════════════════════════════
// AlphaTheta v2 — Portfolio View Controller
// ══════════════════════════════════════════════════════════════════
//
// 负责 "全程跟踪与报告" Tab:
// - 生命周期持仓表
// - 展期 Modal (RollManager)
// - 盯市净值曲线 (EquityCurveManager)
// ══════════════════════════════════════════════════════════════════

import { getState, t, MOCK_DATA } from "../store/index.js";

const $ = (id) => document.getElementById(id);

// ── 辅助: 盈亏双维格式化 ────────────────────────────────────────
function formatPnL(pnlAbs, costBasis) {
    const pct = costBasis > 0 ? (pnlAbs / costBasis) * 100 : 0;
    const sign = pnlAbs >= 0 ? "+" : "";
    const cls = pnlAbs > 0 ? "pnl-positive" : pnlAbs < 0 ? "pnl-negative" : "pnl-zero";
    return `<span class="${cls}">${sign}$${Math.abs(pnlAbs).toFixed(2)} (${sign}${pct.toFixed(1)}%)</span>`;
}

// ── 辅助: 方向数量格式化 ────────────────────────────────────────
function formatDirection(action, qty = 1) {
    if (action === "sell" || action === "short") {
        return `<span class="direction-short">卖出 (Short) · ${qty}张</span>`;
    }
    return `<span class="direction-long">买入 (Long) · ${qty}张</span>`;
}

// ── 生命周期持仓表 ──────────────────────────────────────────────
function renderPositions() {
    const tbody = $("lifecycleBody");
    if (!tbody) return;
    const isZh = getState("lang") === "zh";
    const positions = MOCK_DATA.activePositions || [];

    // ── 空状态: 雷达扫描占位 ──
    if (positions.length === 0) {
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

    // ── 有数据: 完整行模板 ──
    tbody.innerHTML = positions.map((pos) => {
        const pnlAbs = (pos.currentValue - pos.initialPremium) * (pos.quantity || 1) * 100;
        const costBasis = pos.initialPremium * (pos.quantity || 1) * 100;
        return `
    <tr>
      <td class="mono">${pos.ticker}</td>
      <td>${isZh ? pos.typeCn || pos.type : pos.type}</td>
      <td class="mono">$${pos.strike}</td>
      <td>${pos.expiry}</td>
      <td class="${pos.dte <= 7 ? "dte-danger" : pos.dte <= 21 ? "dte-warn" : ""}">${pos.dte}d</td>
      <td class="mono">$${pos.initialPremium.toFixed(2)}</td>
      <td class="mono">$${pos.currentValue.toFixed(2)}</td>
      <td>${formatPnL(pnlAbs, costBasis)}</td>
      <td>
        <button class="action-btn close-btn" data-action="close" data-ticker="${pos.ticker}">平仓</button>
        <button class="action-btn roll-btn" data-action="roll" data-ticker="${pos.ticker}"
                data-strike="${pos.strike}" data-expiry="${pos.expiry}"
                data-dte="${pos.dte}" data-premium="${pos.initialPremium}">展期</button>
      </td>
    </tr>`;
    }).join("");
}

// ── 绩效报告 (已合并到 renderBotTelemetry) ──────────────────────
function renderReport() {
    // 报告权利金已在 renderBotTelemetry 中统一处理
}

// ── Portfolio HUD (空仓安全初始化) ────────────────────────────────
function renderHUD() {
    const data = MOCK_DATA.hud || { marginUtilization: 0, netSpyDelta: 0, netTheta: 0 };

    // Margin utilization bar
    const fill = $("hudMarginFill");
    const val = $("hudMarginValue");
    const mu = data.marginUtilization ?? 0;
    if (fill) {
        fill.style.width = `${mu}%`;
        fill.classList.toggle("margin-danger", mu >= 80);
    }
    if (val) val.textContent = `${mu}%`;

    // Net SPY Delta
    const delta = $("hudNetDelta");
    if (delta) {
        const d = data.netSpyDelta ?? 0;
        delta.textContent = d === 0 ? "0" : `${d >= 0 ? "+" : ""}${d.toFixed(1)}`;
        delta.style.color = d === 0 ? "#64748b" : d >= 0 ? "#22c55e" : "#ef4444";
    }

    // Net Theta
    const theta = $("hudNetTheta");
    if (theta) {
        const t = data.netTheta ?? 0;
        theta.textContent = `$${t.toFixed(2)}`;
        theta.style.color = t === 0 ? "#64748b" : "#facc15";
    }
}

// ── Bot Telemetry (空仓安全初始化) ────────────────────────────────
function renderBotTelemetry() {
    const data = MOCK_DATA.botTelemetry || { status: "scanning", todayOrders: 0, apiLatencyMs: 0 };

    const beacon = $("telemetryBeacon");
    const label = $("telemetryStatusLabel");
    if (beacon) {
        beacon.className = "beacon";
        const statusMap = {
            scanning: { cls: "beacon--scanning", text: "🟢 扫描中" },
            halted: { cls: "beacon--halted", text: "🔴 熔断" },
            standby: { cls: "beacon--standby", text: "🟡 待机" },
        };
        const s = statusMap[data.status] || statusMap.scanning;
        beacon.classList.add(s.cls);
        if (label) label.textContent = `${s.text} · ${data.todayOrders ?? 0} 指令`;
    }

    const orders = $("telemetryOrders");
    if (orders) orders.textContent = `${data.todayOrders ?? 0} 笔`;

    const latency = $("telemetryLatency");
    if (latency) latency.textContent = data.apiLatencyMs ? `${data.apiLatencyMs}ms` : "--";

    const premium = $("reportPremium");
    if (premium) premium.textContent = `$${(MOCK_DATA.tracking?.totalPremiumCollected ?? 0).toLocaleString()}`;
}

// ── Performance Metrics Grid (N/A 安全处理) ─────────────────────
function renderPerfMetrics() {
    const data = MOCK_DATA.perfMetrics;
    const hasHistory = data && (data.totalTrades ?? 0) > 0;

    const setMetric = (id, text, colorClass) => {
        const el = $(id);
        if (!el) return;
        el.textContent = text;
        el.className = "perf-metric-value mono " + colorClass;
    };

    if (!hasHistory) {
        // 无交易历史 → 统一 N/A
        setMetric("perfWinRate", "N/A", "perf-na");
        setMetric("perfMaxDrawdown", "N/A", "perf-na");
        setMetric("perfProfitFactor", "N/A", "perf-na");
        setMetric("perfSharpe", "N/A", "perf-na");
        return;
    }

    setMetric("perfWinRate", `${data.winRate}%`, data.winRate > 50 ? "perf-positive" : "perf-negative");
    setMetric("perfMaxDrawdown", `${data.maxDrawdown}%`, "perf-negative");
    setMetric("perfProfitFactor", data.profitFactor.toFixed(2), data.profitFactor > 1 ? "perf-positive" : "perf-negative");
    setMetric("perfSharpe", data.sharpeRatio.toFixed(2), data.sharpeRatio > 1 ? "perf-accent" : "perf-warn");
}

// ── Roll Manager ────────────────────────────────────────────────
const RollManager = {
    _orderId: null,
    _oldBid: 0,
    _newAsk: 0,

    openModal(pos) {
        const overlay = $("rollModalOverlay");
        if (!overlay) return;

        overlay.classList.add("active");

        const setText = (id, v) => { const el = $(id); if (el) el.textContent = v; };
        setText("rollOldTicker", pos.ticker);
        setText("rollOldStrike", `$${pos.strike}`);
        setText("rollOldExpiry", pos.expiry);
        setText("rollOldDTE", `${pos.dte}d`);

        // Simulate new position
        const newStrike = pos.strike + 5;
        const newExpiry = new Date(new Date(pos.expiry).getTime() + 30 * 86400000);
        const newExpiryStr = newExpiry.toISOString().split("T")[0];
        setText("rollNewStrike", `$${newStrike}`);
        setText("rollNewExpiry", newExpiryStr);

        this._oldBid = pos.currentValue || pos.initialPremium * 0.3;
        this._newAsk = pos.initialPremium * 1.1;
        setText("rollOldBid", `$${this._oldBid.toFixed(2)}`);
        setText("rollNewAsk", `$${this._newAsk.toFixed(2)}`);

        this._recalcNet();
    },

    close() {
        const overlay = $("rollModalOverlay");
        if (overlay) overlay.classList.remove("active");
    },

    _recalcNet() {
        const limitInput = $("rollLimitPrice");
        const limitPrice = limitInput ? parseFloat(limitInput.value) || 0 : 0;
        const net = (this._newAsk - this._oldBid - limitPrice) * 100;
        const el = $("rollNetValue");
        if (el) {
            el.textContent = `${net >= 0 ? "+" : ""}$${net.toFixed(2)}`;
            el.style.color = net >= 0 ? "#22c55e" : "#ef4444";
        }
    },

    async submit() {
        const btn = $("rollSubmitBtn");
        if (btn) btn.disabled = true;

        try {
            const resp = await fetch("/api/v1/orders/roll_combo", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ old_order_id: this._orderId || 1, new_strike: 0, new_expiry: "" }),
            });

            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            this.close();
            window.showToast?.("展期指令已提交 ✓", "success");
        } catch (err) {
            window.showToast?.(`展期失败: ${err.message}`, "error");
        } finally {
            if (btn) btn.disabled = false;
        }
    },
};

// ── Equity Curve Manager ────────────────────────────────────────
const EquityCurveManager = {
    _chart: null,

    init() {
        const el = $("equityCurveChart");
        if (!el || this._chart) return;

        const today = new Date().toISOString().split("T")[0];

        this._chart = echarts.init(el, "dark");
        this._chart.setOption({
            backgroundColor: "transparent",
            tooltip: {
                trigger: "axis",
                backgroundColor: "rgba(15, 23, 42, 0.95)",
                borderColor: "rgba(0, 229, 255, 0.3)",
                textStyle: { color: "#e2e8f0", fontSize: 12 },
            },
            grid: { top: 30, bottom: 30, left: 60, right: 20 },
            xAxis: { type: "category", data: [today], axisLabel: { color: "#64748b" } },
            yAxis: {
                type: "value",
                min: 95000,
                max: 105000,
                axisLabel: { color: "#64748b", formatter: (v) => `$${(v / 1000).toFixed(0)}k` },
                splitLine: { lineStyle: { color: "rgba(148,163,184,0.1)" } },
            },
            series: [{
                type: "line",
                smooth: true,
                lineStyle: { color: "#00e5ff", width: 2, shadowColor: "rgba(0, 229, 255, 0.4)", shadowBlur: 8 },
                areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: "rgba(0,229,255,0.25)" }, { offset: 1, color: "rgba(0,229,255,0.02)" }] } },
                itemStyle: { color: "#00e5ff" },
                data: [100000],
                // $100k 基准虚线
                markLine: {
                    silent: true,
                    symbol: "none",
                    lineStyle: { color: "rgba(6, 182, 212, 0.4)", type: "dashed", width: 1 },
                    label: { formatter: "初始资金 $100K", color: "#64748b", fontSize: 11 },
                    data: [{ yAxis: 100000 }],
                },
            }],
        });

        // 空仓时直接显示 equity summary
        this._renderZeroSummary();
    },

    async fetchAndRender() {
        try {
            const resp = await fetch("/api/v1/portfolio/equity-curve?days=90");
            if (!resp.ok) throw new Error("API error");
            const data = await resp.json();

            if (!data.curve || data.curve.length === 0) {
                // 无数据 → 保持 $100k 锚点 (init 已设置)
                return;
            }

            const xData = data.curve.map((d) => d.date);
            const seriesData = data.curve.map((d) => d.total_equity);

            this._chart?.setOption({
                yAxis: { min: undefined, max: undefined },
                xAxis: { data: xData },
                series: [{ data: seriesData, markLine: { data: [{ yAxis: 100000 }] } }],
            });

            if (data.summary) this._renderSummary(data.summary);
        } catch {
            // 失败时保持 $100k 锚点
        }
    },

    _renderZeroSummary() {
        const el = $("equitySummary");
        if (!el) return;
        el.style.display = "";
        const setVal = (id, text) => { const e = $(id); if (e) e.textContent = text; };
        setVal("eqReturn", "$0.00 (0%)");
        setVal("eqDrawdown", "0%");
        setVal("eqSharpe", "N/A");
    },

    _renderSummary(s) {
        const el = $("equitySummary");
        if (!el) return;
        el.style.display = "";
        const setVal = (id, text) => { const e = $(id); if (e) e.textContent = text; };
        setVal("eqReturn", `${s.total_return >= 0 ? "+" : ""}${s.total_return.toFixed(2)}%`);
        setVal("eqDrawdown", `${s.max_drawdown.toFixed(2)}%`);
        setVal("eqSharpe", s.sharpe_ratio.toFixed(2));
    },
};

// ── 导出 View Controller ────────────────────────────────────────

export function initPortfolioView() {
    console.log("[Portfolio] init");

    renderPositions();
    renderReport();
    renderHUD();
    renderBotTelemetry();
    renderPerfMetrics();
    EquityCurveManager.init();
    EquityCurveManager.fetchAndRender();

    // 事件委托: 展期按钮
    const tbody = $("lifecycleBody");
    if (tbody) {
        tbody.addEventListener("click", (e) => {
            const btn = e.target.closest("[data-action='roll']");
            if (!btn) return;
            RollManager.openModal({
                ticker: btn.dataset.ticker,
                strike: parseFloat(btn.dataset.strike),
                expiry: btn.dataset.expiry,
                dte: parseInt(btn.dataset.dte) || 30,
                initialPremium: parseFloat(btn.dataset.premium) || 3.5,
                currentValue: 0.5,
            });
        });
    }

    // Roll modal close
    const closeBtn = $("rollModalClose");
    if (closeBtn) closeBtn.addEventListener("click", () => RollManager.close());
    const overlay = $("rollModalOverlay");
    if (overlay) overlay.addEventListener("click", (e) => { if (e.target === overlay) RollManager.close(); });

    // Roll submit
    const submitBtn = $("rollSubmitBtn");
    if (submitBtn) submitBtn.addEventListener("click", () => RollManager.submit());

    // Roll limit price input
    const limitInput = $("rollLimitPrice");
    if (limitInput) limitInput.addEventListener("input", () => RollManager._recalcNet());

    // Escape key
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") RollManager.close(); });
}

export function onShow() {
    if (EquityCurveManager._chart) {
        requestAnimationFrame(() => EquityCurveManager._chart.resize());
    }
}

export function onHide() {
    // 无轮询
}

export default { init: initPortfolioView, onShow, onHide };
