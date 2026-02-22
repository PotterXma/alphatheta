// ================================================================
// AlphaTheta v7.0 – Dashboard 图表模块 (Interactive)
// TradingView Lightweight Charts + 标的切换 + 周期切换
//
// 交互:
//   1. 点击 VIX/SPY/QQQ 卡片 → 切换 K 线标的
//   2. 点击 1D/1W/1M 按钮 → 切换时间粒度
//      1D = 5分钟蜡烛 (盘中), 1W = 1小时蜡烛, 1M = 日线蜡烛
// ================================================================

// ── 全局状态 ──
let currentTicker = "SPY";
let currentPeriod = "1D";

// ── 模块级引用 (避免重复创建) ──
let _klineChart = null;
let _equityChart = null;
let _candleSeries = null;
let _smaSeries = null;
let _resizeCleanup = null;

// ── 深色主题配置 ─────────────────────────────────────────────────

const CHART_THEME = {
    bg: "transparent",
    text: "rgba(255, 255, 255, 0.25)",
    grid: "rgba(255, 255, 255, 0.04)",
    gridBorder: "rgba(255, 255, 255, 0.06)",
    crosshair: "rgba(6, 182, 212, 0.3)",
    crosshairLabel: "#1e293b",
    bullCandle: "#06b6d4",
    bearCandle: "#ef4444",
    bullWick: "rgba(6, 182, 212, 0.5)",
    bearWick: "rgba(239, 68, 68, 0.5)",
    smaLine: "rgba(251, 191, 36, 0.65)",
    equityLine: "#10b981",
    equityTop: "rgba(16, 185, 129, 0.35)",
    equityBottom: "rgba(16, 185, 129, 0.02)",
};

// ── 通用图表配置 ─────────────────────────────────────────────────

function _makeChartOptions(containerEl) {
    return {
        width: containerEl.clientWidth,
        height: containerEl.clientHeight || 320,
        layout: {
            background: { type: "solid", color: CHART_THEME.bg },
            textColor: CHART_THEME.text,
            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
            fontSize: 10,
        },
        grid: {
            vertLines: { color: CHART_THEME.grid },
            horzLines: { color: CHART_THEME.grid },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
            vertLine: {
                color: CHART_THEME.crosshair,
                labelBackgroundColor: CHART_THEME.crosshairLabel,
            },
            horzLine: {
                color: CHART_THEME.crosshair,
                labelBackgroundColor: CHART_THEME.crosshairLabel,
            },
        },
        rightPriceScale: {
            borderColor: CHART_THEME.gridBorder,
            scaleMargins: { top: 0.06, bottom: 0.06 },
        },
        timeScale: {
            borderColor: CHART_THEME.gridBorder,
            timeVisible: currentPeriod === "1D", // 日内显示时间
        },
        handleScroll: { mouseWheel: true, pressedMouseMove: true },
        handleScale: { axisPressedMouseMove: true, mouseWheel: true },
    };
}

// ── 数据获取 ─────────────────────────────────────────────────────

/**
 * 从后端 API 获取真实 K 线数据
 * 如果 API 不可用, 降级到 mock 数据
 */
async function fetchChartData(ticker, period) {
    try {
        const resp = await fetch(`/api/v1/market/chart/${encodeURIComponent(ticker)}?period=${period}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        if (data.candles && data.candles.length > 0) {
            return data;
        }
        throw new Error("Empty candle data");
    } catch (err) {
        console.warn(`[Charts] API fetch failed for ${ticker}/${period}, using mock:`, err.message);
        return generateMockKlineData(45);
    }
}

/**
 * 生成 Mock K 线数据 (降级兜底)
 */
function generateMockKlineData(days = 30) {
    const candles = [];
    const sma = [];
    const closePrices = [];
    const basePrices = { SPY: 685, QQQ: 605, "^VIX": 19 };
    let price = basePrices[currentTicker] || 500;
    const baseDate = new Date("2026-01-05");

    for (let i = 0, added = 0; added < days; i++) {
        const d = new Date(baseDate);
        d.setDate(d.getDate() + i);
        if (d.getDay() === 0 || d.getDay() === 6) continue;

        const open = price + (Math.random() - 0.48) * 4;
        const close = open + (Math.random() - 0.43) * 6;
        const high = Math.max(open, close) + Math.random() * 2.5;
        const low = Math.min(open, close) - Math.random() * 2.5;
        price = close;
        closePrices.push(close);

        const time = d.toISOString().split("T")[0];
        candles.push({
            time,
            open: +open.toFixed(2),
            high: +high.toFixed(2),
            low: +low.toFixed(2),
            close: +close.toFixed(2),
        });

        if (closePrices.length >= 5) {
            const window = closePrices.slice(-10);
            const avg = window.reduce((a, b) => a + b, 0) / window.length;
            sma.push({ time, value: +avg.toFixed(2) });
        }
        added++;
    }
    return { candles, sma };
}

// ── 核心更新函数 ─────────────────────────────────────────────────

/**
 * 更新主 K 线图 — 读取 currentTicker + currentPeriod, 拉取数据并渲染
 * 不销毁图表实例, 仅替换 series 数据 (高效)
 */
async function updateMainChart() {
    if (!_candleSeries || !_smaSeries) return;

    // 更新标题
    const titleEl = document.getElementById("chartTitle");
    const label = currentTicker === "^VIX" ? "VIX" : currentTicker;
    const smaLabel = currentPeriod === "1D" ? "SMA10" : currentPeriod === "1W" ? "SMA10" : "SMA20";
    if (titleEl) {
        titleEl.textContent = `${label} — K 线 + ${smaLabel} (${currentPeriod})`;
    }

    // 拉取数据
    const { candles, sma } = await fetchChartData(currentTicker, currentPeriod);

    // 高效更新: setData 替换全部数据 (比 remove + recreate 快)
    _candleSeries.setData(candles);
    _smaSeries.setData(sma);

    // 更新 timeScale 时间可见性 (1D 显示时间, 1W/1M 只显示日期)
    _klineChart.applyOptions({
        timeScale: { timeVisible: currentPeriod === "1D" },
    });

    _klineChart.timeScale().fitContent();
}

// ── 事件绑定 ─────────────────────────────────────────────────────

/**
 * 绑定卡片点击 + 周期按钮切换事件
 * 使用事件代理而非逐个绑定 — 更高效
 */
function setupChartInteractions() {
    // ── 1. 标的切换: 点击 radar-card → 切换 K 线标的 ──
    const radarCards = document.querySelectorAll(".radar-card[data-ticker]");
    radarCards.forEach((card) => {
        card.addEventListener("click", () => {
            const ticker = card.dataset.ticker;
            if (ticker === currentTicker) return; // 已选中, 不重复

            // 更新 active 状态
            radarCards.forEach((c) => c.classList.remove("active"));
            card.classList.add("active");

            currentTicker = ticker;
            updateMainChart();
        });
    });

    // ── 2. 周期切换: 点击 tf-btn → 切换时间维度 ──
    const tfBtns = document.querySelectorAll(".tf-btn[data-tf]");
    tfBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
            const period = btn.dataset.tf;
            if (period === currentPeriod) return;

            tfBtns.forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");

            currentPeriod = period;
            updateMainChart();
        });
    });
}

// ── Equity Curve 数据生成 ────────────────────────────────────────

function generateMockEquityData(points = 30) {
    const data = [];
    let nav = 100000;
    const baseDate = new Date("2026-01-05");

    for (let i = 0; i < points; i++) {
        const d = new Date(baseDate);
        d.setDate(d.getDate() + i * 7);
        nav *= 1 + (Math.random() * 0.025 - 0.005);
        data.push({
            time: d.toISOString().split("T")[0],
            value: +nav.toFixed(2),
        });
    }
    return data;
}

// ── 初始化入口 ──────────────────────────────────────────────────

function initDashboardCharts() {
    if (typeof LightweightCharts === "undefined") {
        console.warn("[Charts] LightweightCharts CDN not loaded, skipping.");
        return;
    }

    const klineEl = document.getElementById("kline-chart-container");
    const equityEl = document.getElementById("equity-chart-container");
    if (!klineEl || !equityEl) return;

    // 清理旧实例
    _destroyCharts();

    // ════════════════════════════════════════════
    // 图表 A: K 线 + SMA (左侧)
    // ════════════════════════════════════════════

    _klineChart = LightweightCharts.createChart(klineEl, _makeChartOptions(klineEl));

    _candleSeries = _klineChart.addCandlestickSeries({
        upColor: CHART_THEME.bullCandle,
        downColor: CHART_THEME.bearCandle,
        borderUpColor: CHART_THEME.bullCandle,
        borderDownColor: CHART_THEME.bearCandle,
        wickUpColor: CHART_THEME.bullWick,
        wickDownColor: CHART_THEME.bearWick,
    });

    _smaSeries = _klineChart.addLineSeries({
        color: CHART_THEME.smaLine,
        lineWidth: 1.5,
        lineStyle: 2,
        crosshairMarkerVisible: false,
        priceLineVisible: false,
        lastValueVisible: true,
    });

    // 首次加载 — 用真实数据
    updateMainChart();

    // ════════════════════════════════════════════
    // 图表 B: Portfolio Equity Curve (右侧)
    // $100k 空仓初始状态 — 水平基准线
    // K 线图 (图表 A) 保持实时行情, 不参与重置
    // ════════════════════════════════════════════

    _equityChart = LightweightCharts.createChart(equityEl, _makeChartOptions(equityEl));

    const today = new Date().toISOString().split("T")[0];
    const areaSeries = _equityChart.addAreaSeries({
        topColor: CHART_THEME.equityTop,
        bottomColor: CHART_THEME.equityBottom,
        lineColor: CHART_THEME.equityLine,
        lineWidth: 2,
        crosshairMarkerBackgroundColor: CHART_THEME.equityLine,
        crosshairMarkerBorderColor: "rgba(16, 185, 129, 0.4)",
        crosshairMarkerRadius: 4,
        priceLineVisible: true,
        priceLineColor: "rgba(6, 182, 212, 0.4)",
        priceLineStyle: 2, // dashed
    });
    // 空仓: 单点 $100k
    areaSeries.setData([{ time: today, value: 100000 }]);
    _equityChart.timeScale().fitContent();

    // 显示当前净值
    const navEl = document.getElementById("equityCurrentValue");
    if (navEl) {
        navEl.textContent = "$100,000.00";
    }

    // ── 响应式重绘 ──
    const observer = new ResizeObserver((entries) => {
        for (const entry of entries) {
            const { width, height } = entry.contentRect;
            if (entry.target === klineEl && _klineChart) {
                _klineChart.applyOptions({ width, height: height || 320 });
            }
            if (entry.target === equityEl && _equityChart) {
                _equityChart.applyOptions({ width, height: height || 320 });
            }
        }
    });
    observer.observe(klineEl);
    observer.observe(equityEl);

    const onResize = () => {
        if (_klineChart) _klineChart.applyOptions({ width: klineEl.clientWidth });
        if (_equityChart) _equityChart.applyOptions({ width: equityEl.clientWidth });
    };
    window.addEventListener("resize", onResize);

    _resizeCleanup = () => {
        observer.disconnect();
        window.removeEventListener("resize", onResize);
    };

    // 绑定交互事件 (只绑定一次)
    setupChartInteractions();
}

function _destroyCharts() {
    if (_resizeCleanup) {
        _resizeCleanup();
        _resizeCleanup = null;
    }
    if (_klineChart) {
        _klineChart.remove();
        _klineChart = null;
    }
    if (_equityChart) {
        _equityChart.remove();
        _equityChart = null;
    }
    _candleSeries = null;
    _smaSeries = null;
}
