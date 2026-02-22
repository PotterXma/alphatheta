## 1. Backend — DB 迁移 + CRUD 端点

- [x] 1.1 在 `settings.py` 中引入 `async_session` 和 `WatchlistTicker` model，将 `_watchlist` in-memory dict 替换为 DB 查询
- [x] 1.2 重写 `GET /settings/watchlist` — 查询 `watchlist_tickers` 表全量记录，返回 `{ tickers, total, active }` 格式
- [x] 1.3 重写 `POST /settings/watchlist` — 插入新记录到 DB，重复 ticker 则 re-activate；用 `yf.Ticker(ticker).options` 校验 `supports_options`
- [x] 1.4 新增 `PUT /settings/watchlist/{ticker}` — 更新 `min_liquidity_score` 等字段
- [x] 1.5 新增 `PUT /settings/watchlist/{ticker}/toggle` — 翻转 `is_active` 布尔值
- [x] 1.6 重写 `DELETE /settings/watchlist/{ticker}` — 硬删除记录（或软删除标记 `is_active=false`）

## 2. Backend — 策略引擎联动

- [x] 2.1 在 `dashboard.py` 中新增 `_get_active_tickers()` 异步函数，从 DB 查询 `is_active=True` 的 ticker 列表
- [x] 2.2 将 `scan_watchlist()` 中的 `_WATCHLIST_POOL` 硬编码替换为 `await _get_active_tickers()`
- [x] 2.3 将 `dashboard_sync()` 中的默认 ticker "SPY" 改为从 DB 读取第一个 active ticker（fallback 仍为 SPY）

## 3. Frontend — HTML 骨架

- [x] 3.1 在 `index.html` 的设置页区域添加「核心票池管理」面板 HTML：Quick Add Bar + Data Table 容器 + Empty State 占位
- [x] 3.2 添加 Toast 通知容器（如果尚未存在）

## 4. Frontend — CSS 玻璃态样式

- [x] 4.1 添加 Quick Add Bar 样式：输入框 + 按钮横向布局，`backdrop-filter: blur(12px)`，主色 `#06b6d4`
- [x] 4.2 添加 Data Table 行样式：深色半透明背景 `rgba(255,255,255,0.05)`，hover 高亮
- [x] 4.3 添加 Toggle Switch 纯 CSS 组件：`#06b6d4` 激活态，`#374151` 关闭态，平滑过渡动画
- [x] 4.4 添加 Inline Edit 样式：hover 边框提示，click 切换为 `<input>`，blur 恢复
- [x] 4.5 添加 OPT 微型徽章样式：绿色半透明背景 + 发光
- [x] 4.6 添加 Ticker 名称文字微发光效果
- [x] 4.7 添加删除按钮红色 trash icon 样式 + 行淡出动画

## 5. Frontend — JavaScript CRUD 逻辑

- [x] 5.1 封装 `WatchlistManager` 命名空间：`fetchAll()`, `addTicker()`, `toggleActive()`, `updateScore()`, `deleteTicker()`, `renderTable()`
- [x] 5.2 实现 `fetchAll()` — 调用 GET 端点，渲染 Data Table
- [x] 5.3 实现 `addTicker()` — 输入校验 + POST + 动态插入行 + Toast 反馈
- [x] 5.4 实现 `toggleActive()` — PUT toggle + 开关 UI 状态更新 + 防连点 disabled
- [x] 5.5 实现 `updateScore()` — inline 编辑 click/blur/Enter/Escape 交互 + PUT 更新
- [x] 5.6 实现 `deleteTicker()` — confirm 弹窗 + DELETE + 行淡出动画
- [x] 5.7 实现 Empty State 条件渲染逻辑
- [x] 5.8 在设置页初始化时调用 `WatchlistManager.fetchAll()`

## 6. 验证

- [x] 6.1 Docker rebuild 后确认 API 5 个端点全部正常响应
- [x] 6.2 浏览器验证：添加 / Toggle / 编辑分数 / 删除全流程
- [x] 6.3 验证容器重启后数据持久化
- [x] 6.4 验证 `/dashboard/scan` 使用 DB 活跃列表而非硬编码
