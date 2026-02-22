## 1. Dockerfile (`backend/Dockerfile`)

- [x] 1.1 Multi-stage build: builder (gcc+libpq-dev) → runtime (libpq5+curl)
- [x] 1.2 `PYTHONDONTWRITEBYTECODE=1` + `PYTHONUNBUFFERED=1`
- [x] 1.3 非 root 用户 appuser:1001 (groupadd + useradd)
- [x] 1.4 `USER appuser` 切换 + `COPY --chown=appuser:appgroup`
- [x] 1.5 HEALTHCHECK with `--start-period=10s`
- [x] 1.6 uvicorn: `--limit-concurrency 100` + `--timeout-keep-alive 30`
- [x] 1.7 APT cache 清理 (`rm -rf /var/lib/apt/lists/*`)

## 2. docker-compose.yml (`backend/docker-compose.yml`)

- [x] 2.1 `api` service: build context, env_file, depends_on healthy
- [x] 2.2 `db` service: timescale/timescaledb-ha:pg14 + pg_isready healthcheck
- [x] 2.3 `redis` service: redis:7-alpine + `--appendonly yes` + redis-cli ping
- [x] 2.4 Named volumes: pgdata + redisdata
- [x] 2.5 Custom bridge network: alphatheta_net
- [x] 2.6 Resource limits (memory caps per service)
- [x] 2.7 DATABASE_URL / REDIS_URL override (localhost → service name)

## 3. .env.example (`backend/.env.example`)

- [x] 3.1 ENV_MODE=paper
- [x] 3.2 DATABASE_URL (asyncpg) + REDIS_URL
- [x] 3.3 TRADIER_SANDBOX_TOKEN + TRADIER_LIVE_TOKEN + TRADIER_ACCOUNT_ID
- [x] 3.4 FINNHUB_API_KEY
- [x] 3.5 ENCRYPTION_KEY (Fernet) + JWT_SECRET_KEY
- [x] 3.6 NTP_SERVER + MAX_CLOCK_DRIFT_SECONDS
- [x] 3.7 OTEL + Prometheus + LOG_LEVEL
