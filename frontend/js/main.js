// ══════════════════════════════════════════════════════════════════
// AlphaTheta v2 — Main Entry (ESM Router + View Lifecycle)
// ══════════════════════════════════════════════════════════════════
//
// 入口文件: 管理侧边栏 Tab 路由、视图生命周期 (lazy init + onShow/onHide)。
//
// 防坑:
// 1. ECharts 在 display:none 容器中 init() 后宽度 = 0px
//    → onShow() 中使用 requestAnimationFrame(() => chart.resize())
// 2. 每个 view 的 init() 只调用一次 (lazy init)
//    → _initialized Set 追踪，避免重复绑定事件
// 3. hash 路由支持刷新保持当前 Tab
// ══════════════════════════════════════════════════════════════════

import { setState, getState, subscribe, t, MOCK_DATA } from "./store/index.js";
import "./components/ui.js"; // 全局 Toast/Modal/setGlobalTicker (自注册到 window)
import "./components/signal-toast.js"; // Signal Toast + triggerMockSignal (自注册到 window)

// ── View Registry ───────────────────────────────────────────────
// 每个 view module 需导出 { init(), onShow(), onHide() }
// Phase 3 实施后逐个取消注释并 import 真实模块

const views = new Map();
const _initialized = new Set();

/** 当前活跃 Tab ID */
let _currentView = null;

/**
 * 注册一个视图模块
 * @param {string} id — Tab ID (e.g. 'dashboard')
 * @param {Object} module — { init(), onShow(), onHide() }
 */
export function registerView(id, module) {
    views.set(id, module);
}

// ── View Imports ────────────────────────────────────────────────
import dashboardView from "./views/dashboard.js";
import studioView from "./views/strategy_studio.js";

import portfolioView from "./views/portfolio.js";
import settingsView from "./views/settings.js";

// ── 注册真实 view 模块 ──────────────────────────────────────────
const VIEWS = ["dashboard", "signal", "lifecycle", "settings"];

registerView("dashboard", dashboardView);
registerView("signal", studioView);
registerView("lifecycle", portfolioView);
registerView("settings", settingsView);

// ── Tab Router ──────────────────────────────────────────────────

/**
 * 导航到指定 Tab
 * @param {string} viewId
 */
export function navigateTo(viewId) {
    if (!VIEWS.includes(viewId)) viewId = "dashboard";

    // ── 1. onHide 当前 view ──
    if (_currentView && _currentView !== viewId) {
        const oldView = views.get(_currentView);
        if (oldView?.onHide) {
            try {
                oldView.onHide();
            } catch (e) {
                console.error(`[Main] onHide error for "${_currentView}":`, e);
            }
        }
    }

    _currentView = viewId;
    setState("activeTab", viewId);

    // ── 2. 切换 DOM display ──
    VIEWS.forEach((v) => {
        const el = document.getElementById(`view-${v}`);
        if (el) el.classList.toggle("hidden", v !== viewId);
    });

    // ── 3. 更新 sidebar active ──
    document.querySelectorAll(".sidebar-item").forEach((item) => {
        item.classList.toggle("active", item.dataset.view === viewId);
    });

    // ── 4. URL hash ──
    location.hash = viewId;

    // ── 5. Lazy init + onShow ──
    const view = views.get(viewId);
    if (view) {
        // 首次显示: init()
        if (!_initialized.has(viewId)) {
            try {
                view.init();
                _initialized.add(viewId);
            } catch (e) {
                console.error(`[Main] init error for "${viewId}":`, e);
            }
        }

        // 每次显示: onShow() (含 ECharts resize)
        try {
            view.onShow();
        } catch (e) {
            console.error(`[Main] onShow error for "${viewId}":`, e);
        }
    }
}

// ── DOM Helper ──────────────────────────────────────────────────

function $(id) {
    return document.getElementById(id);
}

function pad(n) {
    return String(n).padStart(2, "0");
}

// ── Clock ───────────────────────────────────────────────────────

function updateClock() {
    const el = $("navClock");
    if (!el) return;
    const now = new Date();
    el.textContent = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(
        now.getDate()
    )} ${pad(now.getHours())}:${pad(now.getMinutes())}`;
}

// ── i18n Apply ──────────────────────────────────────────────────

function applyI18n() {
    document.querySelectorAll("[data-i18n]").forEach((el) => {
        const key = el.getAttribute("data-i18n");
        const val = t(key);
        if (typeof val === "string") el.textContent = val;
    });
}

// ── Bootstrap ───────────────────────────────────────────────────

function boot() {
    console.log("[Main] ⚡ AlphaTheta v2 ESM booting...");

    // Clock
    updateClock();
    setInterval(updateClock, 30000);

    // i18n
    applyI18n();
    subscribe("lang", () => applyI18n());

    // Sidebar click → navigate
    document.querySelectorAll(".sidebar-item").forEach((item) => {
        item.addEventListener("click", () => navigateTo(item.dataset.view));
    });

    // Hash change
    window.addEventListener("hashchange", () => {
        const hash = location.hash.replace("#", "");
        if (hash && hash !== _currentView) navigateTo(hash);
    });

    // Window resize → resize all visible ECharts
    window.addEventListener("resize", () => {
        if (_currentView) {
            const section = document.getElementById(`view-${_currentView}`);
            if (section) {
                section.querySelectorAll("[_echarts_instance_]").forEach((el) => {
                    const chart = echarts.getInstanceByDom(el);
                    if (chart) chart.resize();
                });
            }
        }
    });

    // Initial route
    const hash = location.hash.replace("#", "");
    navigateTo(VIEWS.includes(hash) ? hash : "dashboard");

    console.log("[Main] ✅ Boot complete");
}

// ── DOMContentLoaded ────────────────────────────────────────────

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
} else {
    boot();
}

// ── Exports for legacy compat ───────────────────────────────────
// app.js 中全局函数在过渡期可通过 window 访问

window.navigateTo = navigateTo;
window.$ = $;
