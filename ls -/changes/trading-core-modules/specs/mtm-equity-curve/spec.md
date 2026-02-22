## Capability: mtm-equity-curve
盯市净值曲线 API + PortfolioSnapshot 模型 + ECharts 可视化

### Requirement: MTM-01 — PortfolioSnapshot 模型
- 表名: `portfolio_snapshots`
- 字段: id, snapshot_date (DATE, UNIQUE), cash_balance, positions_value, total_equity, position_count, created_at
- `total_equity` = `cash_balance` + `positions_value`
- 后台跑批每日写入一条快照 (EOD)

### Requirement: MTM-02 — `GET /api/v1/portfolio/equity-curve` API
- **Query Params**: `days` (默认 90, 最大 365)
- **Response**:
  ```json
  {
    "curve": [
      {
        "date": "2026-02-01",
        "total_equity": 105230.50,
        "cash_balance": 82100.00,
        "positions_value": 23130.50,
        "cash_ratio": 78.02
      }
    ],
    "summary": {
      "start_equity": 100000.00,
      "end_equity": 105230.50,
      "total_return_pct": 5.23,
      "max_drawdown_pct": -2.10,
      "sharpe_ratio": 1.45
    }
  }
  ```
- 从 `portfolio_snapshots` 表查询，按 `snapshot_date` 升序
- `cash_ratio` = (cash_balance / total_equity) × 100
- `summary` 需计算: 总收益率, 最大回撤, 夏普比

### Requirement: MTM-03 — ECharts 科技感折线图
- 折线颜色: `#06b6d4` (cyan)
- 折线样式: `smooth: true`, `lineStyle: { shadowBlur: 10, shadowColor: 'rgba(6,182,212,0.5)' }`
- 填充区域: `areaStyle` 从 cyan 到透明的渐变
- 背景: transparent
- Tooltip 展示: 日期, Total Equity, 现金占比 (%), 浮动市值
- 容器 ID: `equity-curve-chart`

#### Scenario: 正常渲染
- DB 中有 90 天快照数据
- API 返回 90 条 curve 记录 + summary
- ECharts 渲染平滑发光折线
- hover 某点 → tooltip 显示 "2026-02-15: $105,230 | 现金 78% | 浮动 $23,130"

#### Scenario: 空数据
- portfolio_snapshots 表为空
- API 返回 `{ "curve": [], "summary": null }`
- 前端显示 "暂无数据，等待首次跑批完成"
