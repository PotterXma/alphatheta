-- ═══════════════════════════════════════════════════════════════════════════
-- AlphaTheta v2 — 核心数据库 DDL (PostgreSQL 15+)
-- 版本: 001_core_schema
-- 设计原则:
--   1. 不可变账本 (Immutable Ledger): orders/order_legs 表禁止物理删除
--   2. 悲观锁并发控制: 资金/持仓变更使用 SELECT ... FOR UPDATE
--   3. 多租户隔离: 所有业务表通过 user_id FK 隔离, 联合索引强制
--   4. 时间戳统一 TIMESTAMPTZ: 避免跨时区导致期权到期日计算错误
--   5. 金额精度 DECIMAL(12,4): 满足期权合约的 $0.01 最小变动单位
-- ═══════════════════════════════════════════════════════════════════════════

-- 启用 UUID 生成器
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- ════════════════════════════════════════════════════════════════════
-- 模块 1: 租户鉴权与凭证安全 (Identity & Security)
-- ════════════════════════════════════════════════════════════════════

-- 账户类型枚举：模拟盘 / 实盘
CREATE TYPE account_type AS ENUM ('PAPER', 'LIVE');

CREATE TABLE users (
    user_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username      VARCHAR(64)   NOT NULL UNIQUE,
    email         VARCHAR(255)  NOT NULL UNIQUE,
    password_hash VARCHAR(255)  NOT NULL,           -- bcrypt/argon2 哈希, 绝不可明文
    account_type  account_type  NOT NULL DEFAULT 'PAPER',

    -- 资金核心字段 — 悲观锁的锁定目标
    cash_balance  DECIMAL(14,4) NOT NULL DEFAULT 100000.0000,  -- 初始 Paper 资金
    margin_used   DECIMAL(14,4) NOT NULL DEFAULT 0.0000,       -- 已用保证金

    is_active     BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ   NOT NULL DEFAULT now(),

    -- 安全约束: 余额不可为负 (防超卖核心)
    CONSTRAINT chk_cash_non_negative CHECK (cash_balance >= 0),
    CONSTRAINT chk_margin_non_negative CHECK (margin_used >= 0)
);

-- 高频查询: 按 email 或 username 登录
CREATE INDEX idx_users_email ON users (email);


-- 券商 API 凭证表
-- ⚠️ 安全警告: api_secret_encrypted 和 webhook_tokens_encrypted
--    必须由后端使用 AES-256-GCM 或 Fernet 加密后写入,
--    绝不可以明文存储。数据库层面无法强制加密, 但此命名约定
--    是对开发者的强制提醒。
CREATE TABLE user_broker_credentials (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                   UUID NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    broker_name               VARCHAR(64)  NOT NULL DEFAULT 'tastytrade',   -- 券商标识
    api_key                   VARCHAR(512),                                 -- 公钥 (可明文)
    api_secret_encrypted      VARCHAR(1024),                                -- 🔐 AES-256 加密后的私钥
    webhook_tokens_encrypted  JSONB DEFAULT '{}',                           -- 🔐 加密后的推送令牌 (ServerChan, Bark等)

    created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ════════════════════════════════════════════════════════════════════
-- 模块 2: 个性化票池风控 (Watchlist & Risk)
-- ════════════════════════════════════════════════════════════════════

CREATE TABLE user_watchlists (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    ticker              VARCHAR(10) NOT NULL,                            -- 美股 Ticker, 如 AAPL
    risk_limit_pct      DECIMAL(5,2) NOT NULL DEFAULT 5.00,             -- 单票最大仓位占比 (%)
    auto_trade_enabled  BOOLEAN NOT NULL DEFAULT FALSE,                 -- 自动下单开关 (默认关, 需人工确认)
    option_enabled      BOOLEAN NOT NULL DEFAULT TRUE,                  -- 是否启用期权扫描
    liquidity_threshold DECIMAL(8,2) NOT NULL DEFAULT 100.00,           -- 最低流动性阈值 (日均成交量)

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- 联合唯一约束: 同一用户不可重复添加同一标的
    CONSTRAINT uq_user_ticker UNIQUE (user_id, ticker),

    -- 风控约束: risk_limit 在 0.1% ~ 100% 之间
    CONSTRAINT chk_risk_limit CHECK (risk_limit_pct > 0 AND risk_limit_pct <= 100)
);

-- 高频查询: 某用户的完整票池
CREATE INDEX idx_watchlist_user ON user_watchlists (user_id);


-- ════════════════════════════════════════════════════════════════════
-- 模块 3: 期权交易核心账本 (Trading Ledger)
--
-- 设计模式: Master-Detail (主-从)
--   orders_master = 策略级别 (如一笔 Iron Condor)
--   order_legs    = 期权腿级别 (4条腿各自的strike/action/premium)
--
-- ⚠️ 不可变账本原则:
--   这两张表禁止物理 DELETE。取消操作通过将 status 设为 'CANCELED' 实现。
--   所有修改通过 UPDATE status 字段追踪, 审计轨迹由 updated_at + trigger 记录。
-- ════════════════════════════════════════════════════════════════════

-- 订单状态枚举
CREATE TYPE order_status AS ENUM (
    'PENDING',      -- 待提交
    'SUBMITTED',    -- 已提交至券商
    'PARTIAL',      -- 部分成交
    'FILLED',       -- 全部成交
    'CANCELED',     -- 已取消 (软删除)
    'REJECTED',     -- 被拒绝
    'EXPIRED'       -- 过期未成交
);

-- 买卖方向枚举
CREATE TYPE trade_action AS ENUM ('BUY', 'SELL');

-- 期权类型枚举
CREATE TYPE option_right AS ENUM ('CALL', 'PUT');

-- 主订单表 (策略级)
CREATE TABLE orders_master (
    order_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,  -- RESTRICT: 有订单的用户不可删除
    strategy_name  VARCHAR(64)   NOT NULL,            -- 策略标识, 如 'PMCC', 'Iron_Condor', 'Naked_Put'
    status         order_status  NOT NULL DEFAULT 'PENDING',
    net_premium    DECIMAL(12,4) NOT NULL DEFAULT 0,  -- 整体策略净权利金 (正=收取, 负=支付)
    total_cost     DECIMAL(12,4) NOT NULL DEFAULT 0,  -- 总成本 (用于计算资金占用)
    notes          TEXT,                               -- 交易备注 (信号来源、策略依据等)

    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    filled_at      TIMESTAMPTZ,                       -- 全部成交时间
    canceled_at    TIMESTAMPTZ                        -- 取消时间 (软删除时间戳)
);

-- 高频查询: 某用户的全部订单 + 按状态筛选
CREATE INDEX idx_orders_user ON orders_master (user_id);
CREATE INDEX idx_orders_status ON orders_master (user_id, status);
CREATE INDEX idx_orders_created ON orders_master (created_at DESC);


-- 订单腿表 (期权合约级)
CREATE TABLE order_legs (
    leg_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id        UUID NOT NULL REFERENCES orders_master(order_id) ON DELETE RESTRICT,
    leg_index       SMALLINT NOT NULL DEFAULT 1,                     -- 腿序号 (1,2,3,4)

    -- ⚠️ OCC 标准化合约代码 — 期权行业的"身份证"
    -- 格式: "AAPL  270115C00250000" (标的6字符+到期日6位+C/P+行权价8位)
    occ_symbol      VARCHAR(32) NOT NULL,

    action          trade_action   NOT NULL,                         -- BUY 或 SELL
    right_type      option_right   NOT NULL,                         -- CALL 或 PUT
    underlying      VARCHAR(10)    NOT NULL,                         -- 标的 Ticker
    strike_price    DECIMAL(12,4)  NOT NULL,                         -- 行权价
    expiration_date DATE           NOT NULL,                         -- 到期日 (DATE, 非 TIMESTAMP)
    quantity        INT            NOT NULL DEFAULT 1,               -- 合约数量
    limit_price     DECIMAL(12,4),                                   -- 限价单价格
    filled_price    DECIMAL(12,4),                                   -- 实际成交价
    filled_quantity INT            DEFAULT 0,                        -- 实际成交数量

    -- 开仓时的 Greeks 快照 — 用于后续 P&L 归因分析
    entry_greeks    JSONB DEFAULT '{}'::JSONB,
    -- 预期格式: {"delta": -0.35, "gamma": 0.02, "theta": -0.15, "vega": 0.08, "iv": 0.28}

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- 数据完整性
    CONSTRAINT chk_quantity_positive CHECK (quantity > 0),
    CONSTRAINT chk_strike_positive CHECK (strike_price > 0)
);

-- 高频查询: 查某订单的所有腿 / 按 OCC 查历史
CREATE INDEX idx_legs_order ON order_legs (order_id);
CREATE INDEX idx_legs_occ ON order_legs (occ_symbol);
CREATE INDEX idx_legs_underlying ON order_legs (underlying, expiration_date);


-- ════════════════════════════════════════════════════════════════════
-- 模块 4: 活跃持仓状态机 (Positions)
--
-- ⚠️ 不可变原则: 本表绝不使用 DELETE 操作。
--    平仓逻辑: 提交反向订单 → 系统自动将 net_quantity 归零。
--    net_quantity = 0 表示已平仓, 保留历史记录用于审计与 P&L 计算。
--    正数 = 多头 (Long), 负数 = 空头 (Short/Written)
-- ════════════════════════════════════════════════════════════════════

CREATE TABLE user_positions (
    position_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    occ_symbol     VARCHAR(32) NOT NULL,                              -- OCC 合约代码
    underlying     VARCHAR(10) NOT NULL,                              -- 标的 Ticker (冗余, 方便查询)
    right_type     option_right,                                      -- CALL/PUT (NULL = 股票持仓)
    strike_price   DECIMAL(12,4),
    expiration_date DATE,

    -- 持仓核心字段 — 悲观锁的锁定目标
    net_quantity   INT NOT NULL DEFAULT 0,                            -- 正=多头, 负=空头, 0=已平仓
    average_cost   DECIMAL(12,4) NOT NULL DEFAULT 0,                  -- 加权平均成本
    realized_pnl   DECIMAL(14,4) NOT NULL DEFAULT 0,                  -- 已实现盈亏

    -- 关联开仓订单 (可追溯)
    opening_order_id UUID REFERENCES orders_master(order_id),

    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- 联合唯一: 同一用户同一合约只有一条持仓记录
    CONSTRAINT uq_user_position UNIQUE (user_id, occ_symbol)
);

-- 高频查询: 某用户的活跃持仓 (net_quantity != 0)
CREATE INDEX idx_positions_active ON user_positions (user_id) WHERE net_quantity != 0;
-- 按标的查询用户持仓
CREATE INDEX idx_positions_underlying ON user_positions (user_id, underlying);


-- ════════════════════════════════════════════════════════════════════
-- 模块 5: 审计日志 (Audit Trail)
-- 记录所有关键操作的不可变日志
-- ════════════════════════════════════════════════════════════════════

CREATE TABLE audit_log (
    id          BIGSERIAL PRIMARY KEY,                                -- 自增 ID, 保证写入顺序
    user_id     UUID NOT NULL REFERENCES users(user_id),
    action      VARCHAR(64)  NOT NULL,                                -- 操作类型: ORDER_PLACED, POSITION_OPENED, FUND_DEDUCTED...
    entity_type VARCHAR(32)  NOT NULL,                                -- 实体类型: ORDER, POSITION, WATCHLIST...
    entity_id   UUID,                                                 -- 被操作实体的 ID
    payload     JSONB DEFAULT '{}',                                   -- 操作详情 (变更前后快照)
    ip_address  INET,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 审计查询: 按用户 + 时间倒序
CREATE INDEX idx_audit_user_time ON audit_log (user_id, created_at DESC);


-- ════════════════════════════════════════════════════════════════════
-- 自动更新 updated_at 触发器
-- ════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为所有核心表注册触发器
DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN
        SELECT unnest(ARRAY[
            'users', 'user_broker_credentials', 'user_watchlists',
            'orders_master', 'order_legs', 'user_positions'
        ])
    LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_%s_updated_at
             BEFORE UPDATE ON %I
             FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at()',
            tbl, tbl
        );
    END LOOP;
END;
$$ LANGUAGE plpgsql;


-- ════════════════════════════════════════════════════════════════════
-- 附录: 悲观锁并发控制伪代码
--
-- 以下展示在"扣减资金 + 创建订单 + 更新持仓"这个原子操作中,
-- 如何使用 SELECT ... FOR UPDATE 实现行级悲观锁,
-- 防止多引擎并发场景下的资金超卖。
-- ════════════════════════════════════════════════════════════════════

/*
BEGIN;

  -- Step 1: 锁定用户资金行 (其他事务对同一 user 的扣款会被阻塞等待)
  SELECT cash_balance, margin_used
  FROM users
  WHERE user_id = $1
  FOR UPDATE;

  -- Step 2: 业务校验 — 资金是否充足
  IF cash_balance < required_capital THEN
      RAISE EXCEPTION '资金不足: 可用 %, 需要 %', cash_balance, required_capital;
  END IF;

  -- Step 3: 原子扣款
  UPDATE users
  SET cash_balance = cash_balance - required_capital,
      margin_used  = margin_used  + margin_requirement
  WHERE user_id = $1;

  -- Step 4: 写入订单 (不可变账本)
  INSERT INTO orders_master (user_id, strategy_name, net_premium, total_cost)
  VALUES ($1, 'Naked_Put', premium_received, required_capital)
  RETURNING order_id INTO v_order_id;

  -- Step 5: 写入订单腿
  INSERT INTO order_legs (order_id, occ_symbol, action, right_type, ...)
  VALUES (v_order_id, 'AAPL  270115P00190000', 'SELL', 'PUT', ...);

  -- Step 6: 锁定持仓行并更新 (upsert pattern)
  INSERT INTO user_positions (user_id, occ_symbol, net_quantity, average_cost, ...)
  VALUES ($1, 'AAPL  270115P00190000', -1, premium_received, ...)
  ON CONFLICT (user_id, occ_symbol)
  DO UPDATE SET
      net_quantity = user_positions.net_quantity + EXCLUDED.net_quantity,
      average_cost = (  -- 加权平均成本公式
          user_positions.average_cost * ABS(user_positions.net_quantity)
          + EXCLUDED.average_cost * ABS(EXCLUDED.net_quantity)
      ) / NULLIF(ABS(user_positions.net_quantity + EXCLUDED.net_quantity), 0),
      updated_at = now();

  -- Step 7: 审计日志
  INSERT INTO audit_log (user_id, action, entity_type, entity_id, payload)
  VALUES ($1, 'ORDER_PLACED', 'ORDER', v_order_id, jsonb_build_object(
      'strategy', 'Naked_Put',
      'capital_deducted', required_capital,
      'premium_received', premium_received
  ));

COMMIT;
*/

-- ════════════════════════════════════════════════════════════════════
-- 初始化完成
-- ════════════════════════════════════════════════════════════════════
