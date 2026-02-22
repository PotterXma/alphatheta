## Why

将 config.py 从基础环境变量升级为完整的数据源管理中心，集成 3 个免费数据源（Tradier 沙盒、Finnhub 新闻、Yahoo Finance 兜底），并利用 Pydantic v2 computed_field 实现环境感知的动态配置。

## What Changes

- **Rewrite** `app/config.py`: 5 个 computed_field (schema_prefix, tradier_active_token, tradier_base_url, has_tradier, has_finnhub)
- **Rewrite** `.env.example`: 包含全部新变量 + 免费资源申请指南

## Capabilities

### Modified Capabilities
- `market-calendar-service`: 行情降级策略 (Tradier → yfinance)
- `admin-audit-reporting`: 新闻跑马灯数据源 (Finnhub)

## Impact

- `app/config.py` — 全量重写
- `.env.example` — 全量重写
