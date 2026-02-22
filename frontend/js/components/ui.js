// ══════════════════════════════════════════════════════════════════
// AlphaTheta v2 — Shared UI Components
// ══════════════════════════════════════════════════════════════════
//
// 跨页面复用的 UI 组件:
// - showToast(message, type) — 全局消息提示
// - openModal(id, opts) / closeModal(id) — 暗黑玻璃态弹窗
// - setGlobalTicker(ticker) — 全局标的切换 + UI 联动
// ══════════════════════════════════════════════════════════════════

import { setState, getState } from "../store/index.js";

const $ = (id) => document.getElementById(id);

// ── Toast ───────────────────────────────────────────────────────

let _toastContainer = null;

/**
 * 全局消息提示
 * @param {string} message
 * @param {'success'|'error'|'warning'|'info'} [type='info']
 * @param {number} [duration=3000] — 自动消失毫秒数
 */
export function showToast(message, type = "info", duration = 3000) {
    // Lazy create container
    if (!_toastContainer) {
        _toastContainer = document.createElement("div");
        _toastContainer.id = "toastContainer";
        _toastContainer.style.cssText = `
      position: fixed; top: 20px; right: 20px; z-index: 10000;
      display: flex; flex-direction: column; gap: 8px;
      pointer-events: none;
    `;
        document.body.appendChild(_toastContainer);
    }

    const icons = { success: "✅", error: "❌", warning: "⚠️", info: "ℹ️" };
    const colors = {
        success: "rgba(34, 197, 94, 0.15)",
        error: "rgba(239, 68, 68, 0.15)",
        warning: "rgba(245, 158, 11, 0.15)",
        info: "rgba(0, 229, 255, 0.15)",
    };
    const borders = {
        success: "rgba(34, 197, 94, 0.3)",
        error: "rgba(239, 68, 68, 0.3)",
        warning: "rgba(245, 158, 11, 0.3)",
        info: "rgba(0, 229, 255, 0.3)",
    };

    const toast = document.createElement("div");
    toast.style.cssText = `
    background: ${colors[type] || colors.info};
    border: 1px solid ${borders[type] || borders.info};
    backdrop-filter: blur(12px);
    color: #e2e8f0; padding: 10px 16px; border-radius: 8px;
    font-size: 13px; pointer-events: auto; cursor: pointer;
    animation: toastSlideIn 0.3s ease-out;
    display: flex; align-items: center; gap: 8px;
    max-width: 360px;
  `;
    toast.innerHTML = `<span>${icons[type] || icons.info}</span><span>${message}</span>`;
    toast.addEventListener("click", () => toast.remove());

    _toastContainer.appendChild(toast);

    // Auto dismiss
    setTimeout(() => {
        toast.style.animation = "toastSlideOut 0.3s ease-in forwards";
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// Inject animation keyframes (once)
if (!document.getElementById("toastStyles")) {
    const style = document.createElement("style");
    style.id = "toastStyles";
    style.textContent = `
    @keyframes toastSlideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
    @keyframes toastSlideOut { from { transform: translateX(0); opacity: 1; } to { transform: translateX(100%); opacity: 0; } }
  `;
    document.head.appendChild(style);
}

// ── Modal ───────────────────────────────────────────────────────

const _modalCallbacks = new Map();

/**
 * 打开弹窗
 * @param {string} id — Modal overlay 的 DOM ID
 * @param {Object} [opts]
 * @param {Function} [opts.onClose] — 关闭回调
 */
export function openModal(id, opts = {}) {
    const overlay = $(id);
    if (!overlay) return;
    overlay.classList.add("active");

    if (opts.onClose) _modalCallbacks.set(id, opts.onClose);
}

/**
 * 关闭弹窗
 * @param {string} id
 */
export function closeModal(id) {
    const overlay = $(id);
    if (!overlay) return;
    overlay.classList.remove("active");

    const cb = _modalCallbacks.get(id);
    if (cb) {
        cb();
        _modalCallbacks.delete(id);
    }
}

// Global: click overlay to close, Escape to close
document.addEventListener("click", (e) => {
    if (e.target.classList.contains("modal-overlay") && e.target.classList.contains("active")) {
        closeModal(e.target.id);
    }
});

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
        document.querySelectorAll(".modal-overlay.active").forEach((overlay) => {
            closeModal(overlay.id);
        });
    }
});

// ── Global Ticker Switcher ──────────────────────────────────────

/**
 * 切换全局标的 — 触发所有订阅
 * @param {string} ticker
 */
export function setGlobalTicker(ticker) {
    if (!ticker) return;
    ticker = ticker.toUpperCase();
    setState("activeTicker", ticker);

    // UI 联动: 更新顶部显示
    const el = $("globalTickerDisplay");
    if (el) el.textContent = ticker;

    console.log(`[UI] Global ticker → ${ticker}`);
}

// 暴露到 window (legacy compat)
window.showToast = showToast;
window.openModal = openModal;
window.closeModal = closeModal;
window.setGlobalTicker = setGlobalTicker;

export default { showToast, openModal, closeModal, setGlobalTicker };
