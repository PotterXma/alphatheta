// ══════════════════════════════════════════════════════════════════
// AlphaTheta v2 — Signal Toast (暗黑玻璃态信号通知)
// ══════════════════════════════════════════════════════════════════
//
// 接收 Scanner/WS 信号 → 显示富通知卡片 → CTA 跳转策略工作室
// ══════════════════════════════════════════════════════════════════

import { setState } from "../store/index.js";

let _toastEl = null;

const DEFAULT_SIGNAL = {
    ticker: "AAPL",
    type: "LEAPS_CALL",
    dte: 365,
    reason: "RSI 超卖且 IVR 极低",
};

/**
 * 显示信号 Toast
 * @param {Object} payload — { ticker, type, dte, reason }
 */
export function showSignalToast(payload) {
    // 若已存在, 先移除
    dismissSignalToast();

    const p = { ...DEFAULT_SIGNAL, ...payload };
    const typeLabel = p.type === "LEAPS_CALL" ? "LEAPS 看涨" : p.type === "LEAPS_PUT" ? "LEAPS 看跌" : p.type;

    _toastEl = document.createElement("div");
    _toastEl.className = "signal-toast";
    _toastEl.innerHTML = `
        <button class="signal-toast-close" aria-label="关闭">×</button>
        <div class="signal-toast-header">
            <span class="signal-toast-badge">📡 SIGNAL</span>
            <span class="signal-toast-ticker">${p.ticker}</span>
        </div>
        <div class="signal-toast-type">${typeLabel} · DTE ${p.dte}d</div>
        <div class="signal-toast-reason">${p.reason}</div>
        <button class="signal-toast-cta" id="btnSignalCTA">⚡ 立即前往组装</button>
    `;

    document.body.appendChild(_toastEl);

    // Animate in
    requestAnimationFrame(() => _toastEl.classList.add("signal-toast--visible"));

    // Close button
    _toastEl.querySelector(".signal-toast-close").addEventListener("click", dismissSignalToast);

    // CTA: 注入状态 → 路由到 Studio
    _toastEl.querySelector("#btnSignalCTA").addEventListener("click", () => {
        // 1. 切换全局标的
        window.setGlobalTicker?.(p.ticker);

        // 2. 暂存信号上下文 (Studio onShow 将消费)
        setState("pendingSignal", p);

        // 3. 路由到策略工作室
        window.navigateTo?.("signal");

        // 4. 关闭 Toast
        dismissSignalToast();

        console.log("[SignalToast] → Studio with payload:", p);
    });
}

/**
 * 关闭信号 Toast
 */
export function dismissSignalToast() {
    if (!_toastEl) return;
    _toastEl.classList.remove("signal-toast--visible");
    setTimeout(() => {
        _toastEl?.remove();
        _toastEl = null;
    }, 300);
}

/**
 * 控制台模拟触发器
 * @param {Object} [overrides] — 覆盖默认 payload 的任意字段
 */
export function triggerMockSignal(overrides = {}) {
    const payload = { ...DEFAULT_SIGNAL, ...overrides };
    console.log("[SignalToast] 🔔 Mock signal triggered:", payload);
    showSignalToast(payload);
    return payload;
}

// 暴露到 window (控制台测试)
window.triggerMockSignal = triggerMockSignal;
window.showSignalToast = showSignalToast;
