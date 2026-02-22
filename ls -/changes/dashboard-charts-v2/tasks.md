## 1. Chart Module (`renderCharts.js`)

- [x] 1.1 `initDashboardCharts()` 入口函数 — CDN guard + DOM guard + destroy 旧实例
- [x] 1.2 `generateMockKlineData(days)` — OHLC 生成器 (跳过周末, 微弱上涨趋势)
- [x] 1.3 `generateMockEquityData(points)` — 净值曲线生成器 (稳定增长 + 随机波动)
- [x] 1.4 `CHART_THEME` 配置对象 — #06b6d4 涨, #ef4444 跌, #10b981 净值
- [x] 1.5 `_makeChartOptions()` — 通用图表配置 (透明背景, JetBrains Mono, 极弱网格)
- [x] 1.6 Chart A: Candlestick + SMA200 (amber dashed LineSeries)
- [x] 1.7 Chart B: Area Series (emerald → transparent 渐变)
- [x] 1.8 ResizeObserver + window.resize 双重响应式
- [x] 1.9 `_destroyCharts()` — 清理函数 (防止 DOM 叠加)

## 2. HTML Updates

- [x] 2.1 容器 ID 改为 `kline-chart-container` 和 `equity-chart-container`
- [x] 2.2 CDN 固定版本 `lightweight-charts@4.2.0` (v5 有 breaking changes)
- [x] 2.3 加入 `<script src="renderCharts.js">` (位于 CDN 和 app.js 之间)

## 3. JS Cleanup

- [x] 3.1 从 `app.js` 移除 180 行内联图表代码
- [x] 3.2 `renderDashboard()` 末尾委托调用 `initDashboardCharts()`
