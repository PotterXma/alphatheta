// ══════════════════════════════════════════════════════════════════
// AlphaTheta v2 — Signal Stream Service
// ══════════════════════════════════════════════════════════════════
//
// WebSocket 信号流 + 自动重连 + REST 补偿
//
// 使用:
//   import { signalStream } from './signal-stream.js';
//   signalStream.onSignal(signals => { ... });
//   signalStream.connect();
// ══════════════════════════════════════════════════════════════════

const WS_URL = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/feed?channels=signals`;
const REST_URL = "/api/v1/dashboard/scan";
const MAX_RETRY_MS = 30_000;

class SignalStream {
    constructor() {
        /** @type {WebSocket|null} */
        this._ws = null;
        /** @type {Function[]} */
        this._listeners = [];
        this._retryMs = 1000;
        this._retryTimer = null;
        this._alive = false;       // 是否主动连接中
        this._connected = false;
    }

    // ── Public API ──────────────────────────────────────────────

    /**
     * 注册信号回调
     * @param {(signals: Array) => void} cb
     */
    onSignal(cb) {
        this._listeners.push(cb);
    }

    /** 建立连接 + 首次 REST 快照 */
    connect() {
        this._alive = true;
        this._retryMs = 1000;
        this._openWs();
        this._restCompensate();   // 初始快照
    }

    /** 主动断开 */
    disconnect() {
        this._alive = false;
        clearTimeout(this._retryTimer);
        if (this._ws) {
            this._ws.close(1000, "user disconnect");
            this._ws = null;
        }
        this._connected = false;
    }

    /** @returns {boolean} */
    get isConnected() { return this._connected; }

    // ── WebSocket 生命周期 ──────────────────────────────────────

    _openWs() {
        if (!this._alive) return;
        try {
            this._ws = new WebSocket(WS_URL);
        } catch {
            this._scheduleRetry();
            return;
        }

        this._ws.onopen = () => {
            console.info("[SignalStream] WS connected");
            this._connected = true;
            this._retryMs = 1000;      // reset backoff
            this._restCompensate();    // 重连补偿
        };

        this._ws.onmessage = (evt) => {
            try {
                const msg = JSON.parse(evt.data);
                // 心跳回复
                if (msg.type === "ping") {
                    this._ws.send(JSON.stringify({ type: "pong" }));
                    return;
                }
                // 信号频道数据
                if (msg.channel === "signals" && msg.data) {
                    const signals = Array.isArray(msg.data) ? msg.data : [msg.data];
                    this._emit(signals);
                }
            } catch (e) {
                console.warn("[SignalStream] parse error:", e);
            }
        };

        this._ws.onclose = (evt) => {
            console.warn("[SignalStream] WS closed:", evt.code, evt.reason);
            this._connected = false;
            this._scheduleRetry();
        };

        this._ws.onerror = () => {
            // onclose 会紧跟触发，重连在 onclose 中处理
        };
    }

    // ── Exponential Backoff ────────────────────────────────────

    _scheduleRetry() {
        if (!this._alive) return;
        console.info(`[SignalStream] retry in ${this._retryMs}ms`);
        this._retryTimer = setTimeout(() => {
            this._openWs();
        }, this._retryMs);
        this._retryMs = Math.min(this._retryMs * 2, MAX_RETRY_MS);
    }

    // ── REST 补偿 ─────────────────────────────────────────────

    async _restCompensate() {
        try {
            const resp = await fetch(REST_URL);
            if (!resp.ok) return;
            const data = await resp.json();
            const signals = (data.signals || [])
                .filter(s => s.action_type !== "error")
                .slice(0, 3);
            if (signals.length > 0) {
                this._emit(signals);
            }
        } catch (e) {
            console.warn("[SignalStream] REST compensate failed:", e);
        }
    }

    // ── 分发 ──────────────────────────────────────────────────

    _emit(signals) {
        for (const cb of this._listeners) {
            try { cb(signals); } catch (e) { console.error("[SignalStream] listener error:", e); }
        }
    }
}

export const signalStream = new SignalStream();
