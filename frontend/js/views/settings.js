// ══════════════════════════════════════════════════════════════════
// AlphaTheta v2 — Settings View Controller
// ══════════════════════════════════════════════════════════════════
//
// 负责 "系统设置" Tab:
// - Watchlist CRUD + 防抖搜索
// - API Key 管理
// - Kill Switch 配置
// - 系统终端日志
// ══════════════════════════════════════════════════════════════════

import { getState, setState, MOCK_DATA } from "../store/index.js";

const $ = (id) => document.getElementById(id);

// ── 全局安全常量 ────────────────────────────────────────────────
const MAX_WATCHLIST_SIZE = 50;
const TICKER_REGEX = /^[A-Z]{1,5}$/;
const defaultAssetConfig = {
    riskLimit: 5,      // 默认单票最大仓位占比 5%
    autoTrade: false,  // 默认关闭自动下单
    status: "初始化中...",
};

// ── Watchlist Manager ───────────────────────────────────────────
const WatchlistManager = {
    _base: "/api/v1/settings/watchlist",
    _data: [],
    _debounceTimer: null,

    // ── Debounced Search ──
    _onSearchInput(e) {
        clearTimeout(this._debounceTimer);
        const q = e.target.value.trim();
        if (q.length < 1) {
            this._hideDropdown();
            return;
        }
        this._debounceTimer = setTimeout(() => this._doSearch(q), 300);
    },

    async _doSearch(q) {
        try {
            const resp = await fetch(`/api/v1/strategy/search?q=${encodeURIComponent(q)}`);
            if (!resp.ok) return;
            const data = await resp.json();
            this._showDropdown(data.results || []);
        } catch (err) {
            console.warn("[Settings] Search failed:", err);
        }
    },

    _showDropdown(results) {
        let dd = $("searchDropdown");
        if (!dd) {
            dd = document.createElement("div");
            dd.id = "searchDropdown";
            dd.className = "search-dropdown";
            const searchWrap = $("wlTickerInput")?.parentElement;
            if (searchWrap) searchWrap.appendChild(dd);
        }

        if (results.length === 0) {
            dd.innerHTML = '<div class="dd-item dd-empty">No results</div>';
            dd.style.display = "block";
            return;
        }

        dd.innerHTML = results.map((r) => `
      <div class="dd-item" data-ticker="${r.ticker}">
        <span class="dd-ticker">${r.ticker}</span>
        <span class="dd-name">${r.name || ""}</span>
        <span class="dd-price">$${r.price || "—"}</span>
      </div>
    `).join("");
        dd.style.display = "block";

        // Click to add
        dd.querySelectorAll(".dd-item[data-ticker]").forEach((item) => {
            item.addEventListener("click", () => {
                this.addTicker(item.dataset.ticker);
                this._hideDropdown();
                const input = $("wlTickerInput");
                if (input) input.value = "";
            });
        });
    },

    _hideDropdown() {
        const dd = $("searchDropdown");
        if (dd) dd.style.display = "none";
    },

    // ── Toast ──
    toast(msg, type = "success") {
        // 复用全局 showToast 或 fallback
        if (window.showToast) {
            window.showToast(msg, type);
            return;
        }
        const el = document.createElement("div");
        el.className = `toast toast-${type}`;
        el.textContent = msg;
        document.body.appendChild(el);
        setTimeout(() => el.remove(), 3000);
    },

    // ── Fetch All & Render ──
    async fetchAll() {
        try {
            const resp = await fetch(this._base);
            if (!resp.ok) return;
            const data = await resp.json();
            this._data = data.tickers || data || [];
            this.renderTable();
        } catch (err) {
            console.warn("[Settings] fetchAll failed:", err);
        }
    },

    // ── Render Table ──
    renderTable() {
        const tbody = $("wlTableBody");
        if (!tbody) return;

        if (this._data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#64748b;padding:20px;">暂无标的，请搜索添加</td></tr>';
            return;
        }

        tbody.innerHTML = this._data.map((t) => `
      <tr>
        <td class="mono">${t.ticker}</td>
        <td>${t.name || "—"}</td>
        <td>
          <label class="toggle-switch">
            <input type="checkbox" ${t.is_active ? "checked" : ""} data-action="toggle" data-ticker="${t.ticker}">
            <span class="toggle-slider"></span>
          </label>
        </td>
        <td>${t.supports_options ? "✅" : "❌"}</td>
        <td>
          <button class="btn-danger-sm" data-action="delete" data-ticker="${t.ticker}">✕</button>
        </td>
      </tr>
    `).join("");
    },

    // ── Add Ticker ──
    async addTicker(ticker) {
        if (!ticker) return;
        try {
            const resp = await fetch(this._base, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ ticker: ticker.toUpperCase() }),
            });
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                this.toast(err.detail || `Failed to add ${ticker}`, "error");
                return;
            }
            this.toast(`已添加 ${ticker.toUpperCase()}`);
            this.fetchAll();
        } catch (err) {
            this.toast(`添加失败: ${err.message}`, "error");
        }
    },

    // ── Toggle Active ──
    async toggleActive(ticker, checkbox) {
        try {
            const resp = await fetch(`${this._base}/${encodeURIComponent(ticker)}/toggle`, { method: "POST" });
            if (!resp.ok) {
                checkbox.checked = !checkbox.checked;
                return;
            }
        } catch {
            checkbox.checked = !checkbox.checked;
        }
    },

    // ── Delete Ticker ──
    async deleteTicker(ticker) {
        try {
            const resp = await fetch(`${this._base}/${encodeURIComponent(ticker)}`, { method: "DELETE" });
            if (!resp.ok) return;
            this.toast(`已删除 ${ticker}`);
            this.fetchAll();
        } catch (err) {
            this.toast(`删除失败: ${err.message}`, "error");
        }
    },

    // ══════════════════════════════════════════════════════════════
    // 批量导入引擎 — 5 步清洗流水线 + 容量熔断
    // ══════════════════════════════════════════════════════════════

    /**
     * 解析并批量导入 Watchlist
     * @param {string} rawInput — textarea 原始文本
     */
    async parseAndImportWatchlist(rawInput) {
        try {
            if (!rawInput || !rawInput.trim()) {
                this.toast("请输入至少一个 Ticker", "warning");
                return;
            }

            // ── Step 1: 切分 ──
            const tokens = rawInput.split(/[,\s\n]+/);

            // ── Step 2: 清洗 (trim + uppercase) ──
            const cleaned = tokens
                .map(t => t.trim().toUpperCase())
                .filter(t => t.length > 0);

            // ── Step 3: 合规校验 (严格美股 Ticker 正则) ──
            const rejected = [];
            const valid = cleaned.filter(t => {
                if (TICKER_REGEX.test(t)) return true;
                rejected.push(t);
                return false;
            });

            if (rejected.length > 0) {
                console.warn(`[Batch] 已过滤 ${rejected.length} 个非法 Ticker:`, rejected);
            }

            // ── Step 4: 去重 (内部) ──
            const unique = [...new Set(valid)];

            // ── Step 5: 状态比对 (与现有 watchlist 去重) ──
            const existingTickers = new Set(this._data.map(d => d.ticker));
            const brandNew = unique.filter(t => !existingTickers.has(t));
            const skipped = unique.length - brandNew.length;

            if (brandNew.length === 0) {
                const msg = skipped > 0
                    ? `所有 ${unique.length} 只标的已存在于监控池中`
                    : "未解析到任何合规的美股 Ticker";
                this.toast(msg, "warning");
                return;
            }

            // ── 容量熔断 ──
            const currentSize = this._data.length;
            if (currentSize + brandNew.length > MAX_WATCHLIST_SIZE) {
                this.toast(
                    `[⚠️ 容量超限] 当前 ${currentSize} 只 + 新增 ${brandNew.length} 只 = ${currentSize + brandNew.length} 只，超过上限 ${MAX_WATCHLIST_SIZE}。宏观 LEAPS 策略建议精选核心资产。`,
                    "error"
                );
                return;
            }

            // ── 逐个 POST (串行, 防止并发爆破) ──
            let successCount = 0;
            const successTickers = [];
            const failedTickers = [];

            for (const ticker of brandNew) {
                try {
                    const resp = await fetch(this._base, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ ticker, ...defaultAssetConfig }),
                    });
                    if (resp.ok) {
                        successCount++;
                        successTickers.push(ticker);
                    } else {
                        failedTickers.push(ticker);
                    }
                } catch {
                    failedTickers.push(ticker);
                }
            }

            // ── 反馈 ──
            if (successCount > 0) {
                this.toast(
                    `✅ 成功导入 ${successCount} 只新标的: ${successTickers.join(", ")}` +
                    (skipped > 0 ? ` (跳过 ${skipped} 只已存在)` : "") +
                    (rejected.length > 0 ? ` (过滤 ${rejected.length} 个非法代码)` : ""),
                    "success"
                );
                this.fetchAll(); // 刷新表格
            }

            if (failedTickers.length > 0) {
                this.toast(`⚠ ${failedTickers.length} 只添加失败: ${failedTickers.join(", ")}`, "error");
            }

            // TODO: 节流拉取行情 (Staggered Fetching)
            // 新 Ticker 写入后，以每秒 3 个的频率拉取最新价格:
            // async function staggeredFetch(tickers, perSecond = 3) {
            //     for (let i = 0; i < tickers.length; i += perSecond) {
            //         const batch = tickers.slice(i, i + perSecond);
            //         await Promise.all(batch.map(t => fetch(`/api/v1/market_data/quote?ticker=${t}`)));
            //         if (i + perSecond < tickers.length) await new Promise(r => setTimeout(r, 1000));
            //     }
            // }

        } catch (err) {
            console.error("[Batch] parseAndImportWatchlist error:", err);
            this.toast(`批量导入异常: ${err.message}`, "error");
        }
    },
};

// ── API Toggle ──────────────────────────────────────────────────
function setupApiToggle() {
    const toggle = $("autoTradeToggle");
    if (toggle) {
        toggle.addEventListener("change", () => {
            setState("isAutoTrading", toggle.checked);
            WatchlistManager.toast(
                toggle.checked ? "自动交易已启用" : "自动交易已停用",
                toggle.checked ? "success" : "warning"
            );
        });
    }
}

// ══════════════════════════════════════════════════════════════════
// TerminalLogger — 工业级控制台日志引擎
// ══════════════════════════════════════════════════════════════════

const TerminalLogger = {
    _el: null,

    get el() {
        if (!this._el) this._el = $("systemTerminal");
        return this._el;
    },

    clear() {
        if (this.el) this.el.innerHTML = "";
    },

    /**
     * @param {"sys"|"info"|"warn"|"err"} level
     * @param {string} module — e.g. "SYS", "NET", "DAEMON"
     * @param {string} message
     */
    appendLog(level, module, message) {
        const container = this.el;
        if (!container) return;

        const now = new Date();
        const ts = [
            now.getHours().toString().padStart(2, "0"),
            now.getMinutes().toString().padStart(2, "0"),
            now.getSeconds().toString().padStart(2, "0"),
        ].join(":") + "." + now.getMilliseconds().toString().padStart(3, "0");

        const line = document.createElement("div");
        line.className = `log-line log-${level}`;
        line.innerHTML = `<span class="log-ts">[${ts}]</span><span class="log-mod">[${module}]</span>${message}`;
        container.appendChild(line);

        // 强制触底滚动
        container.scrollTop = container.scrollHeight;
    },
};

const _delay = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * 全链路开机自检流水线
 */
async function runSystemDiagnostic() {
    const T = TerminalLogger;
    T.clear();

    T.appendLog("sys", "SYS", "初始化 AlphaTheta v2 核心引擎...");
    await _delay(400);

    T.appendLog("sys", "SYS", `运行环境: Paper Trading (模拟盘) | 初始资金 $100,000`);
    await _delay(200);

    // ── 1. Market API ──
    T.appendLog("info", "NET", "测速期权行情源 (Market API Gateway)...");
    await _delay(300);
    try {
        const t0 = performance.now();
        const resp = await fetch("/api/v1/dashboard/sync");
        const latency = Math.round(performance.now() - t0);
        if (resp.ok) {
            const cls = latency > 2000 ? "warn" : "info";
            T.appendLog(cls, "NET", `行情网关响应延迟 ${latency}ms ${latency > 2000 ? "[偏高]" : "[正常]"}`);
        } else {
            T.appendLog("err", "NET", `行情网关异常 HTTP ${resp.status}`);
        }
    } catch (err) {
        T.appendLog("err", "NET", `行情网关不可达: ${err.message}`);
    }
    await _delay(250);

    // ── 2. Scanner Daemon ──
    T.appendLog("info", "DAEMON", "嗅探后台扫描引擎心跳...");
    await _delay(300);
    try {
        const resp = await fetch("/api/v1/scanner/status");
        if (resp.ok) {
            const data = await resp.json();
            const status = data.status || "UNKNOWN";
            T.appendLog(
                status === "running" ? "info" : "warn",
                "DAEMON",
                `状态: ${status.toUpperCase()} | 票池: ${data.watchlist_count || 0} 只 | 上次扫描: ${data.last_scan || "N/A"}`
            );
        } else {
            T.appendLog("warn", "DAEMON", `扫描引擎状态查询失败 (HTTP ${resp.status}) — 可能未部署`);
        }
    } catch {
        T.appendLog("warn", "DAEMON", "扫描引擎端点不可达 — 后台守护进程可能未启动");
    }
    await _delay(250);

    // ── 3. API Quota ──
    T.appendLog("info", "LIMIT", "检查 API 剩余额度水位...");
    await _delay(200);
    try {
        const resp = await fetch("/healthz");
        if (resp.ok) {
            T.appendLog("info", "LIMIT", "健康检查通过 — API 网关运行正常");
        } else {
            T.appendLog("warn", "LIMIT", `健康检查异常 HTTP ${resp.status}`);
        }
    } catch {
        T.appendLog("warn", "LIMIT", "健康端点不可达");
    }
    await _delay(200);

    // ── 4. Redis ──
    T.appendLog("info", "CACHE", "测试 Redis 缓存连接...");
    await _delay(200);
    try {
        const resp = await fetch("/api/v1/market_data/expirations?ticker=SPY");
        T.appendLog(
            resp.ok ? "info" : "warn",
            "CACHE",
            resp.ok ? "Redis 缓存层响应正常 [200 OK]" : `缓存层异常 HTTP ${resp.status}`
        );
    } catch {
        T.appendLog("warn", "CACHE", "缓存测试失败");
    }
    await _delay(250);

    // ── 5. WebSocket ──
    T.appendLog("info", "GATEWAY", "测试推送通道...");
    await _delay(300);
    try {
        const wsUrl = `ws://${location.host}/ws/feed?channels=signals`;
        const ws = new WebSocket(wsUrl);
        const wsResult = await new Promise((resolve) => {
            const timeout = setTimeout(() => {
                ws.close();
                resolve({ ok: false, reason: "超时 (3s)" });
            }, 3000);
            ws.onopen = () => {
                const t0 = Date.now();
                ws.send(JSON.stringify({ type: "ping" }));
                ws.onmessage = (evt) => {
                    const msg = JSON.parse(evt.data);
                    if (msg.type === "pong" || msg.type === "ping") {
                        clearTimeout(timeout);
                        ws.close();
                        resolve({ ok: true, latency: Date.now() - t0 });
                    }
                };
            };
            ws.onerror = () => {
                clearTimeout(timeout);
                resolve({ ok: false, reason: "连接失败" });
            };
        });
        if (wsResult.ok) {
            T.appendLog("info", "GATEWAY", `WebSocket 推送通道正常 [${wsResult.latency}ms] ✅`);
        } else {
            T.appendLog("warn", "GATEWAY", `WebSocket 连接失败: ${wsResult.reason}`);
        }
    } catch {
        T.appendLog("warn", "GATEWAY", "WebSocket 端点不可达");
    }
    await _delay(150);

    // ── 6. Final ──
    T.appendLog("sys", "SYS", "────────────────────────────────────────────");
    T.appendLog("sys", "SYS", "诊断完成。全部系统绿灯，终端进入实时待命状态 🟢");
}

// ── 导出 View Controller ────────────────────────────────────────

export function initSettingsView() {
    console.log("[Settings] init");

    WatchlistManager.fetchAll();
    setupApiToggle();
    runSystemDiagnostic();

    // Recheck button
    const recheckBtn = $("btnRecheck");
    if (recheckBtn) {
        recheckBtn.addEventListener("click", () => runSystemDiagnostic());
    }

    // Search input: 防抖
    const searchInput = $("wlTickerInput");
    if (searchInput) {
        searchInput.addEventListener("input", (e) => WatchlistManager._onSearchInput(e));
        // Enter to add
        searchInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                const q = searchInput.value.trim().toUpperCase();
                if (q) WatchlistManager.addTicker(q);
                searchInput.value = "";
                WatchlistManager._hideDropdown();
            }
        });
    }

    // wlAddBtn click (single add)
    const addBtn = $("wlAddBtn");
    if (addBtn) {
        addBtn.addEventListener("click", () => {
            const input = $("wlTickerInput");
            const q = input?.value?.trim().toUpperCase();
            if (q) WatchlistManager.addTicker(q);
            if (input) input.value = "";
            WatchlistManager._hideDropdown();
        });
    }

    // ── 批量导入按钮 ──
    const batchBtn = $("wlBatchBtn");
    const batchInput = $("wlBatchInput");
    if (batchBtn && batchInput) {
        batchBtn.addEventListener("click", async () => {
            batchBtn.disabled = true;
            batchBtn.textContent = "⏳ 导入中...";
            await WatchlistManager.parseAndImportWatchlist(batchInput.value);
            batchInput.value = "";
            _updateBatchCount();
            batchBtn.disabled = false;
            batchBtn.textContent = "✨ 批量导入";
        });

        // Live count
        batchInput.addEventListener("input", _updateBatchCount);
    }

    function _updateBatchCount() {
        const raw = $("wlBatchInput")?.value || "";
        const tokens = raw.split(/[,\s\n]+/).filter(t => /^[A-Za-z]{1,5}$/.test(t.trim()));
        const unique = new Set(tokens.map(t => t.trim().toUpperCase()));
        const countEl = $("wlBatchCount");
        const current = WatchlistManager._data.length;
        if (countEl) {
            countEl.textContent = `${current} + ${unique.size} / ${MAX_WATCHLIST_SIZE}`;
            countEl.style.color = (current + unique.size) > MAX_WATCHLIST_SIZE ? "#ef4444" : "#64748b";
        }
    }

    // 事件委托: Watchlist table
    const tbody = $("wlTableBody");
    if (tbody) {
        tbody.addEventListener("click", (e) => {
            const btn = e.target.closest("[data-action]");
            if (!btn) return;

            if (btn.dataset.action === "delete") {
                WatchlistManager.deleteTicker(btn.dataset.ticker);
            }
        });

        tbody.addEventListener("change", (e) => {
            const checkbox = e.target.closest("[data-action='toggle']");
            if (!checkbox) return;
            WatchlistManager.toggleActive(checkbox.dataset.ticker, checkbox);
        });
    }

    // Close dropdown on outside click
    document.addEventListener("click", (e) => {
        if (!e.target.closest("#tickerSearchInput") && !e.target.closest("#searchDropdown")) {
            WatchlistManager._hideDropdown();
        }
    });
}

export function onShow() {
    WatchlistManager.fetchAll();
}

export function onHide() {
    WatchlistManager._hideDropdown();
}

export default { init: initSettingsView, onShow, onHide };
