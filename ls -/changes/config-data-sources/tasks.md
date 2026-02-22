## 1. Config Settings

- [x] 1.1 `EnvMode(StrEnum)` — paper/live 二选一，默认 paper
- [x] 1.2 `database_url` — asyncpg 驱动 URL + schema 说明
- [x] 1.3 `redis_url` — 含用途注释 (幂等/kill switch/行情缓存)
- [x] 1.4 `SettingsConfigDict` — env_file=".env", case_sensitive=False, extra="ignore"

## 2. Free Data Sources

- [x] 2.1 `tradier_sandbox_token` — 免费沙盒 Token + 申请指南注释
- [x] 2.2 `tradier_live_token` — 实盘 Token (仅 live 模式)
- [x] 2.3 `tradier_account_id` — 账户 ID
- [x] 2.4 `finnhub_api_key` — 免费新闻跑马灯 + 申请指南注释
- [x] 2.5 `finnhub_base_url` — 可配置基础 URL
- [x] 2.6 `use_yfinance_fallback` — bool, 默认 True + 用法注释

## 3. Computed Fields

- [x] 3.1 `schema_prefix` — @computed_field, paper_ / live_ 前缀
- [x] 3.2 `tradier_active_token` — env_mode 路由选择对应 Token
- [x] 3.3 `tradier_base_url` — sandbox.tradier.com vs api.tradier.com
- [x] 3.4 `has_tradier` — bool, Token 是否可用
- [x] 3.5 `has_finnhub` — bool, Key 是否可用

## 4. Infrastructure Config

- [x] 4.1 `encryption_key` — Fernet 密钥 + 生成命令注释
- [x] 4.2 `ntp_server` + `max_clock_drift_seconds` — 时钟校准
- [x] 4.3 `cors_origins` + `cors_origin_list` property — 逗号分隔 → list
- [x] 4.4 `otel_service_name` + `otel_exporter_otlp_endpoint`
- [x] 4.5 `prometheus_enabled` — 可关闭 /metrics
- [x] 4.6 `log_level` — 正则校验 DEBUG/INFO/WARNING/ERROR/CRITICAL

## 5. .env.example

- [x] 5.1 更新 .env.example 包含所有新变量 + 中文申请指南注释
