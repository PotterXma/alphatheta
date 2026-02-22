## Why

系统设置页面缺乏核心票池的可视化管理界面。当前 watchlist 通过后端硬编码 `_WATCHLIST_POOL = ["SPY", "QQQ", ...]` 或 in-memory dict 管理，运维无法在前端增删改查标的。策略引擎的轮询范围、期权链扫描范围都从此表读取，因此需要一个高效、防误操作的 CRUD 模块。

## What Changes

- **新增前端模块**: 在系统设置页开发「核心票池管理」面板，包含极速添加栏 (Quick Add Bar)、玻璃态监控阵列 (Data Table)、Toggle 启停开关、内联流动性阈值编辑、删除操作
- **完善后端 API**: 补充 `PUT /watchlist/{ticker}` (更新字段) 和 `PUT /watchlist/{ticker}/toggle` (启停切换)，从 in-memory dict 迁移至 DB (`watchlist_tickers` 表)
- **联动策略引擎**: `/dashboard/scan` 的 `_WATCHLIST_POOL` 从硬编码改为查 DB `watchlist_tickers` 表中 `is_active=True` 的记录

## Capabilities

### New Capabilities
- `watchlist-ui`: 前端票池管理面板的完整 CRUD 交互 (Quick Add、Toggle Switch、Inline Edit、Delete、Empty State、Loading/防连点)

### Modified Capabilities
- (无已有 spec 需修改)

## Impact

- **前端**: `index.html` (设置页 HTML 骨架)、`style.css` (玻璃态样式)、`app.js` (CRUD 逻辑模块)
- **后端**: `routers/settings.py` (补充 PUT 端点、迁移至 DB)、`models/watchlist.py` (已有模型，无需改动)
- **策略引擎**: `routers/dashboard.py` `_WATCHLIST_POOL` 改为 DB 查询
- **API 路由**: `POST /settings/watchlist`, `GET /settings/watchlist`, `PUT /settings/watchlist/{ticker}`, `PUT /settings/watchlist/{ticker}/toggle`, `DELETE /settings/watchlist/{ticker}`
