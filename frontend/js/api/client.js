// ══════════════════════════════════════════════════════════════════
// AlphaTheta v2 — Unified HTTP Client
// ══════════════════════════════════════════════════════════════════
//
// 封装原生 fetch，提供:
// 1. Base URL 自动拼接
// 2. AbortController + 可配置超时 (默认 15s)
// 3. Response 拦截: 4xx/5xx → 标准化 ApiError
// 4. 便捷方法: get(), post(), del()
//
// 防坑:
// - finally 块保证 clearTimeout，无泄漏
// - JSON 解析失败时抛出 ApiError 而非原生 SyntaxError
// - AbortError 与 ApiError 区分，上层可按类型分支处理
// ══════════════════════════════════════════════════════════════════

const DEFAULT_TIMEOUT_MS = 15000;

// ── ApiError ────────────────────────────────────────────────────

export class ApiError extends Error {
    /**
     * @param {string} message
     * @param {number} status — HTTP status code (0 if network error)
     * @param {string} statusText
     * @param {string} url
     */
    constructor(message, status = 0, statusText = "", url = "") {
        super(message);
        this.name = "ApiError";
        this.status = status;
        this.statusText = statusText;
        this.url = url;
    }
}

// ── Core Request ────────────────────────────────────────────────

/**
 * 统一 HTTP 请求
 * @param {string} method — GET / POST / DELETE / PUT / PATCH
 * @param {string} path — API 路径 (e.g. '/api/v1/dashboard/sync')
 * @param {Object} [opts] — 扩展选项
 * @param {*} [opts.body] — 请求体 (自动 JSON.stringify)
 * @param {number} [opts.timeout] — 超时毫秒数 (默认 15000)
 * @param {Object} [opts.headers] — 额外请求头
 * @param {AbortSignal} [opts.signal] — 外部 AbortSignal (优先级高于内部)
 * @returns {Promise<*>} — 解析后的 JSON 数据
 */
async function request(method, path, opts = {}) {
    const { body, timeout = DEFAULT_TIMEOUT_MS, headers = {}, signal } = opts;

    // ── AbortController + 超时 ──
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    // 如果外部传入 signal，链接到内部 controller
    if (signal) {
        signal.addEventListener("abort", () => controller.abort());
    }

    const url = path.startsWith("http") ? path : `${window.location.origin}${path}`;

    const fetchOpts = {
        method,
        signal: controller.signal,
        headers: {
            "Accept": "application/json",
            ...headers,
        },
    };

    // POST/PUT/PATCH: 自动 JSON 序列化
    if (body !== undefined) {
        fetchOpts.headers["Content-Type"] = "application/json";
        fetchOpts.body = JSON.stringify(body);
    }

    try {
        const response = await fetch(url, fetchOpts);

        // ── HTTP 状态墙 ──
        if (!response.ok) {
            let errorBody = "";
            try {
                errorBody = await response.text();
            } catch { /* ignore */ }

            throw new ApiError(
                `HTTP ${response.status}: ${response.statusText}${errorBody ? ` — ${errorBody.slice(0, 200)}` : ""}`,
                response.status,
                response.statusText,
                url,
            );
        }

        // ── JSON 解析 ──
        // 204 No Content → 返回 null
        if (response.status === 204) return null;

        try {
            return await response.json();
        } catch (parseErr) {
            throw new ApiError(
                `Invalid JSON response from ${path}`,
                response.status,
                "Parse Error",
                url,
            );
        }

    } catch (err) {
        // AbortError (超时) → 包装为 ApiError
        if (err.name === "AbortError") {
            throw new ApiError(
                `Request timeout (${timeout}ms): ${path}`,
                0,
                "Timeout",
                url,
            );
        }
        // 已经是 ApiError → 直接抛出
        if (err instanceof ApiError) throw err;

        // 网络错误等 → 包装
        throw new ApiError(
            `Network error: ${err.message}`,
            0,
            "NetworkError",
            url,
        );

    } finally {
        clearTimeout(timeoutId);
    }
}

// ── Convenience Methods ─────────────────────────────────────────

/**
 * GET 请求
 * @param {string} path
 * @param {Object} [opts]
 */
export function get(path, opts) {
    return request("GET", path, opts);
}

/**
 * POST 请求
 * @param {string} path
 * @param {*} data — 请求体 (JSON)
 * @param {Object} [opts]
 */
export function post(path, data, opts) {
    return request("POST", path, { ...opts, body: data });
}

/**
 * DELETE 请求
 * @param {string} path
 * @param {Object} [opts]
 */
export function del(path, opts) {
    return request("DELETE", path, opts);
}

/**
 * PUT 请求
 * @param {string} path
 * @param {*} data
 * @param {Object} [opts]
 */
export function put(path, data, opts) {
    return request("PUT", path, { ...opts, body: data });
}

export default { get, post, del, put, ApiError };
