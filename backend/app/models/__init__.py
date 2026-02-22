"""
模型注册表 — 集中导入所有 ORM 模型

⚠️ 重要: 每新增一个 ORM 模型文件, 必须在此处 import,
   否则 Base.metadata.create_all() 不会感知到该表。
"""

from app.models.base import Base  # noqa: F401

# ── 核心业务模型 ──
from app.models.user import User  # noqa: F401
from app.models.user_broker_credentials import UserBrokerCredentials  # noqa: F401
from app.models.order import Order  # noqa: F401
from app.models.order_leg import OrderLeg  # noqa: F401
from app.models.position import Position  # noqa: F401
from app.models.watchlist import UserWatchlist  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.transaction import TransactionLedger  # noqa: F401
from app.models.kill_switch import KillSwitchState  # noqa: F401
from app.models.api_key import ApiKey  # noqa: F401
from app.models.portfolio_snapshot import PortfolioSnapshot  # noqa: F401
from app.models.tick import TickData  # noqa: F401
