"""
AlphaTheta v2 — 核心配置中心

设计原则:
1. 单 Settings 类管理全部环境变量，pydantic-settings 自动从 .env 加载
2. ENV_MODE (paper/live) 控制一切环境隔离: DB schema 前缀、broker 适配器路由
3. 免费数据源分层降级策略:
   - Tradier Sandbox → 免费期权链 + 纸面交易 (推荐，质量最高)
   - Finnhub        → 免费新闻/情绪 (前端跑马灯数据源)
   - Yahoo Finance  → 免费行情兜底 (无需 API Key，但有速率限制)
4. computed_field 动态生成 schema_prefix，确保 paper/live 数据完全隔离

免费资源申请指南:
───────────────────────────────────────────────────────────────────
数据源         费用      申请地址                                    用途
───────────────────────────────────────────────────────────────────
Tradier       $0       https://developer.tradier.com/             期权链/纸面交易
Finnhub       $0       https://finnhub.io/register                新闻/情绪/跑马灯
Yahoo Finance $0       无需注册 (通过 yfinance 库直接使用)         行情降级兜底
───────────────────────────────────────────────────────────────────
"""

from enum import StrEnum
from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvMode(StrEnum):
    """运行环境 — 决定 DB schema 前缀和 broker 路由"""
    PAPER = "paper"
    LIVE = "live"


class Settings(BaseSettings):
    """
    AlphaTheta v2 全局配置

    优先级: 环境变量 > .env 文件 > 默认值
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,       # ENV_MODE 和 env_mode 都可以
        extra="ignore",             # 忽略 .env 中未声明的变量
    )

    # ════════════════════════════════════════════════
    # 环境隔离
    # ════════════════════════════════════════════════

    env_mode: EnvMode = Field(
        default=EnvMode.PAPER,
        description=(
            "运行模式: paper (模拟盘) 或 live (实盘)。"
            "影响 DB schema 前缀、broker 适配器选择、kill switch 隔离。"
            "默认 paper — 生产部署时通过环境变量显式设为 live"
        ),
    )

    # ════════════════════════════════════════════════
    # 基础设施 — PostgreSQL + Redis
    # ════════════════════════════════════════════════

    database_url: str = Field(
        default="postgresql+asyncpg://alpha:alpha@localhost:5432/alphatheta",
        description=(
            "PostgreSQL 连接 URL (异步驱动 asyncpg)。"
            "TimescaleDB 使用同一实例，通过 hypertable 区分时序表。"
            "schema 前缀由 env_mode 自动生成"
        ),
    )

    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description=(
            "Redis 连接 URL。用于: "
            "1) 幂等缓存 (Idempotency-Key, TTL=24h) "
            "2) Kill Switch 状态 (双写 PG+Redis) "
            "3) 行情缓存 (Quote, TTL=30s)"
        ),
    )

    # ════════════════════════════════════════════════
    # 券商 — Tradier (免费沙盒)
    # ════════════════════════════════════════════════
    #
    # Tradier 开发者沙盒完全免费，提供:
    # - 延迟期权链数据 (15分钟延迟但结构完整)
    # - 纸面交易 API (模拟下单/成交/持仓)
    # - 历史行情数据
    #
    # 申请步骤:
    # 1. 访问 https://developer.tradier.com/
    # 2. 注册免费账号 → 获得 Sandbox API Token
    # 3. 将 Token 填入 TRADIER_SANDBOX_TOKEN
    #
    # Paper 模式使用 sandbox.tradier.com
    # Live 模式使用 api.tradier.com (需额外申请实盘权限)

    tradier_sandbox_token: str = Field(
        default="",
        description="Tradier Sandbox API Token (免费)。留空则回退到 yfinance",
    )
    tradier_live_token: str = Field(
        default="",
        description="Tradier 实盘 API Token (需付费账号)。仅 ENV_MODE=live 时使用",
    )
    tradier_account_id: str = Field(
        default="",
        description="Tradier 账户 ID。在 Dashboard 的 Account 页面获取",
    )

    # ════════════════════════════════════════════════
    # 新闻/情绪 — Finnhub (免费跑马灯数据源)
    # ════════════════════════════════════════════════
    #
    # Finnhub 免费版提供:
    # - 美股实时新闻 (60 req/min)
    # - 市场情绪分析
    # - 公司基本面数据
    # - WebSocket 实时报价 (有限额)
    #
    # 申请步骤:
    # 1. 访问 https://finnhub.io/register
    # 2. 注册免费账号 → 获得 API Key
    # 3. 将 Key 填入 FINNHUB_API_KEY
    #
    # 前端跑马灯调用: GET https://finnhub.io/api/v1/news?category=general
    # 个股新闻: GET https://finnhub.io/api/v1/company-news?symbol=SPY

    finnhub_api_key: str = Field(
        default="",
        description=(
            "Finnhub API Key (免费)。"
            "用于前端跑马灯新闻和市场情绪数据。"
            "留空则跑马灯使用静态 fallback 数据"
        ),
    )
    finnhub_base_url: str = Field(
        default="https://finnhub.io/api/v1",
        description="Finnhub API 基础 URL",
    )

    # ════════════════════════════════════════════════
    # 行情降级兜底 — Yahoo Finance (无需 API Key)
    # ════════════════════════════════════════════════
    #
    # yfinance 是一个免费的 Python 库，直接爬取 Yahoo Finance 数据:
    # - 无需注册或 API Key
    # - 支持股票/期权/ETF 实时行情
    # - 有 IP 速率限制 (约 2000 req/hour)
    # - 数据延迟约 15 分钟
    #
    # 用法: pip install yfinance
    #   import yfinance as yf
    #   spy = yf.Ticker("SPY")
    #   spy.options  # 可用到期日列表
    #   spy.option_chain("2025-04-18")  # 期权链
    #
    # 降级策略:
    # 1. Tradier Token 可用 → 优先使用 Tradier
    # 2. Tradier Token 为空 → 回退到 yfinance
    # 3. yfinance 也失败 → 使用本地缓存做最后兜底

    use_yfinance_fallback: bool = Field(
        default=True,
        description=(
            "是否启用 Yahoo Finance 作为行情降级兜底。"
            "当 Tradier Token 为空或 API 超时时自动降级。"
            "建议保持 True，除非你在生产环境有更好的付费数据源"
        ),
    )

    # ════════════════════════════════════════════════
    # 安全 — 加密与认证
    # ════════════════════════════════════════════════

    encryption_key: str = Field(
        default="CHANGE_ME_32_BYTE_FERNET_KEY_BASE64",
        description=(
            "Fernet 对称加密密钥 (base64 编码, 32 bytes)。"
            "用于加密存储在 PG 中的 API Keys。"
            "生成方式: python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        ),
    )

    jwt_secret_key: str = Field(
        default="CHANGE_ME_JWT_SECRET_KEY",
        description=(
            "JWT 签名密钥 (至少 32 字节随机字符串)。"
            "用于 HS256 签名 access/refresh token。"
            "生成方式: python3 -c 'import secrets; print(secrets.token_urlsafe(32))'"
        ),
    )

    @property
    def fernet_key(self) -> str:
        """encryption_key 的别名 — crypto_vault.py 使用此名称"""
        return self.encryption_key

    # ════════════════════════════════════════════════
    # NTP — 时钟同步 (交易系统对时间精度要求高)
    # ════════════════════════════════════════════════

    ntp_server: str = Field(
        default="time.google.com",
        description="NTP 服务器地址。用于校准本地时钟与市场时间的偏差",
    )
    max_clock_drift_seconds: float = Field(
        default=5.0,
        ge=0.1,
        description="最大允许时钟漂移 (秒)。超过此值的请求将被 Kill Switch 拦截",
    )

    # ════════════════════════════════════════════════
    # CORS — 前端跨域
    # ════════════════════════════════════════════════

    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173,http://127.0.0.1:5500",
        description="允许的 CORS 来源，逗号分隔。生产环境应严格限制",
    )

    # ════════════════════════════════════════════════
    # 可观测性 — OpenTelemetry + Prometheus
    # ════════════════════════════════════════════════

    otel_service_name: str = Field(
        default="alphatheta-backend",
        description="OpenTelemetry 服务名称，用于 Jaeger/Zipkin 中识别",
    )
    otel_exporter_otlp_endpoint: str = Field(
        default="http://localhost:4317",
        description="OTLP gRPC 端点地址",
    )
    prometheus_enabled: bool = Field(
        default=True,
        description="是否启用 /metrics Prometheus 端点",
    )

    # ════════════════════════════════════════════════
    # 日志
    # ════════════════════════════════════════════════

    log_level: str = Field(
        default="INFO",
        pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="日志级别",
    )

    # ════════════════════════════════════════════════
    # 计算属性 — 基于 env_mode 动态生成
    # ════════════════════════════════════════════════

    @computed_field
    @property
    def schema_prefix(self) -> str:
        """
        数据库 Schema 前缀 — 实现 paper/live 数据完全隔离

        paper 模式: 所有表在 paper_ schema 下 (如 paper_orders, paper_positions)
        live 模式:  所有表在 live_ schema 下 (如 live_orders, live_positions)

        这样同一个 PG 实例可以同时服务 paper 和 live，互不干扰
        """
        return f"{self.env_mode.value}_"

    @computed_field
    @property
    def tradier_active_token(self) -> str:
        """
        根据 env_mode 自动选择 Tradier Token

        paper → tradier_sandbox_token (sandbox.tradier.com)
        live  → tradier_live_token    (api.tradier.com)
        """
        if self.env_mode == EnvMode.LIVE:
            return self.tradier_live_token
        return self.tradier_sandbox_token

    @computed_field
    @property
    def tradier_base_url(self) -> str:
        """Tradier API 基础 URL — sandbox vs production"""
        if self.env_mode == EnvMode.LIVE:
            return "https://api.tradier.com/v1"
        return "https://sandbox.tradier.com/v1"

    @computed_field
    @property
    def has_tradier(self) -> bool:
        """Tradier Token 是否可用 — 决定是否降级到 yfinance"""
        return bool(self.tradier_active_token)

    @computed_field
    @property
    def has_finnhub(self) -> bool:
        """Finnhub API Key 是否可用 — 决定跑马灯是否有实时新闻"""
        return bool(self.finnhub_api_key)

    @property
    def cors_origin_list(self) -> list[str]:
        """将逗号分隔的 CORS 字符串转为列表"""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """
    全局 Settings 单例 — 使用 lru_cache 确保只实例化一次

    其他模块统一通过此函数获取配置:
        from app.config import get_settings
        settings = get_settings()
    """
    return Settings()
