## Context

AlphaTheta v2 的策略引擎轮询范围由 watchlist 决定。当前后端 `settings.py` 已有 GET/POST/DELETE 端点，但数据存储在 in-memory dict (`_watchlist`) 中，重启即丢失。`WatchlistTicker` SQLAlchemy model 已定义在 `models/watchlist.py`，但 router 未使用它。前端设置页无 watchlist CRUD 界面。

`dashboard.py` 中 `_WATCHLIST_POOL = ["SPY", "QQQ", ...]` 硬编码，需改为从 DB 读取。

## Goals / Non-Goals

**Goals:**
- 前端：在设置页新增「核心票池管理」面板，支持 CRUD + Toggle + Inline Edit
- 后端：5 个 RESTful 端点全部接 DB (`watchlist_tickers` 表)
- 联动：`/dashboard/scan` 的轮询池从 DB 动态读取

**Non-Goals:**
- 不做批量导入/导出 CSV
- 不做 websocket 实时推送 (仍用 polling)
- 不做 watchlist 分组/标签管理

## Decisions

### D1: 后端存储 — 迁移至 TimescaleDB

**选择**: 直接使用已有 `WatchlistTicker` model + TimescaleDB (PostgreSQL)
**替代方案**: 继续用 in-memory dict
**理由**: model 已定义完整 (`ticker` PK, `is_active`, `min_liquidity_score`, `supports_options`)。in-memory 重启丢失数据，不适合生产。

### D2: API 设计 — RESTful 5 端点

| Method | Path | 用途 |
|--------|------|------|
| `GET` | `/api/v1/settings/watchlist` | 获取全部（含 inactive） |
| `POST` | `/api/v1/settings/watchlist` | 新增标的 |
| `PUT` | `/api/v1/settings/watchlist/{ticker}` | 更新字段 (min_liquidity_score 等) |
| `PUT` | `/api/v1/settings/watchlist/{ticker}/toggle` | 切换 is_active |
| `DELETE` | `/api/v1/settings/watchlist/{ticker}` | 硬删除 |

**选择**: PUT toggle 单独端点
**替代方案**: 合并到 PUT 更新
**理由**: Toggle 是高频操作 (前端 Switch 一键触发)，单独端点更语义化，前端无需构造完整 payload

### D3: 前端架构 — 单一 JS 模块 + 内联编辑

**选择**: 在 `app.js` 中新增 `WatchlistManager` 命名空间，所有 CRUD 逻辑封装其中
**替代方案**: 新建独立 `watchlist.js` 文件
**理由**: 当前项目为 SPA 单文件结构 (index.html + app.js + style.css)，保持一致性

### D4: 玻璃态 UI 组件

- **Quick Add Bar**: `<input>` + `<button>` 横向布局，`backdrop-filter: blur(12px)`, 按钮使用系统主色 `#06b6d4`
- **Data Table**: 每行一个标的，深色半透明背景 `rgba(255,255,255,0.05)`
- **Toggle Switch**: 纯 CSS 实现 (无依赖)，`#06b6d4` 激活态, `#374151` 关闭态
- **Inline Edit**: 流动性分数 hover 显示编辑边框，click 变 `<input type="number">`，blur 触发 PUT
- **Delete**: 红色 trash icon，点击后 confirm 弹窗防误删

### D5: 策略引擎联动

`dashboard.py` 的 `_WATCHLIST_POOL` 改为:
```python
async def _get_active_tickers() -> list[str]:
    async with async_session() as session:
        result = await session.execute(
            select(WatchlistTicker.ticker)
            .where(WatchlistTicker.is_active == True)
        )
        return [r[0] for r in result.all()]
```

## Risks / Trade-offs

- **[Risk] yfinance 限速**: 池子越大轮询越多 → 可能触发 IP 限速 2000 req/hour
  → Mitigation: 前端添加时 toast 提示"建议池子 ≤ 15 只标的"
- **[Risk] 期权链不可用**: 新增的个股可能无 options chain
  → Mitigation: POST 时用 yfinance 验证 `yf.Ticker(ticker).options` 是否返回数据，设置 `supports_options` 字段
- **[Risk] 并发修改]: 多标签页同时编辑
  → Mitigation: V1 不做乐观锁，前端每次操作后 re-fetch 列表
