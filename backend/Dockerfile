# ════════════════════════════════════════════════════════════════
# AlphaTheta v2 — 生产级 Dockerfile
#
# 安全策略:
#   1. 基于 python:3.12-slim 精简基础镜像 (~120MB vs ~900MB full)
#   2. 非 root 用户 (appuser:1001) 运行 — 交易系统绝不允许 root 权限
#   3. 编译依赖仅在 build 阶段安装, 运行阶段精简
#   4. 多阶段构建: builder → runtime, 最终镜像不含 gcc/pip cache
#
# 构建:
#   docker build -t alphatheta-api .
#   docker build -t alphatheta-api --build-arg ENV=production .
# ════════════════════════════════════════════════════════════════

# ── Stage 1: Builder (编译依赖, 安装 Python 包) ──
FROM python:3.12-slim AS builder

# 防止 .pyc 文件和缓冲, 加速 I/O 日志输出
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# 安装编译依赖 (gcc 用于编译 C 扩展如 asyncpg, libpq-dev 用于 psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件, 利用 Docker layer cache
# (只要 pyproject.toml 不变, 后续代码改动不触发依赖重新安装)
COPY pyproject.toml ./
RUN pip install --prefix=/install --no-warn-script-location . 2>/dev/null \
    || pip install --prefix=/install --no-warn-script-location -e .


# ── Stage 2: Runtime (精简运行时镜像) ──
FROM python:3.12-slim AS runtime

# Python 运行时环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # 告诉 Python 在 /install 下查找已安装的包
    PYTHONPATH="/app:${PYTHONPATH}"

WORKDIR /app

# 安装运行时必需的系统库 (libpq = asyncpg 的运行时依赖, curl = healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── 安全: 创建非 root 用户 ──
# 交易系统安全铁律: 绝不以 root 运行
# UID=1001 避免与宿主机系统用户冲突
# --no-log-init 防止在某些系统上创建巨大的 lastlog 文件
RUN groupadd --gid 1001 appgroup \
    && useradd --uid 1001 --gid appgroup --shell /bin/false --no-log-init appuser

# 从 builder 阶段复制已编译的 Python 包
COPY --from=builder /install /usr/local

# 复制应用代码
COPY --chown=appuser:appgroup . .

# 切换到非 root 用户
USER appuser

# 健康检查探针 — K8s / docker-compose 依赖此端点判断服务可用性
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
    CMD curl -f http://localhost:8000/healthz || exit 1

EXPOSE 8000

# 启动 uvicorn — 使用 --workers 2 实现并发 (生产环境建议 4 或 CPU 核数)
# --limit-concurrency 100 防止过载, --timeout-keep-alive 30 复用长连接
CMD ["uvicorn", "app.main:app", \
    "--host", "0.0.0.0", \
    "--port", "8000", \
    "--workers", "2", \
    "--limit-concurrency", "100", \
    "--timeout-keep-alive", "30", \
    "--access-log"]
