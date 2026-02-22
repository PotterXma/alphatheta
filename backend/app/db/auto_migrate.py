"""
数据库自动迁移引擎

启动时自动执行:
1. CREATE TABLE IF NOT EXISTS — 新表自动创建
2. ALTER TABLE ADD COLUMN — 新字段自动添加
3. ALTER TABLE ALTER COLUMN TYPE — 字段类型不匹配时自动修正 (dev mode only)

⚠️ 安全策略:
- 只做 ADD / ALTER, 绝不做 DROP COLUMN (防数据丢失)
- 生产环境建议关闭 auto_alter_type, 使用 Alembic 正式迁移
"""

import logging
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger("alphatheta.db.migrate")


# ── SQLAlchemy 类型 → PG 类型的映射 (用于对比) ──
_TYPE_MAP: dict[str, str] = {
    "VARCHAR": "character varying",
    "INTEGER": "integer",
    "BIGINT": "bigint",
    "SMALLINT": "smallint",
    "BOOLEAN": "boolean",
    "FLOAT": "double precision",
    "DOUBLE_PRECISION": "double precision",
    "NUMERIC": "numeric",
    "TEXT": "text",
    "DATE": "date",
    "TIMESTAMP": "timestamp without time zone",
    "DATETIME": "timestamp with time zone",
    "UUID": "uuid",
    "JSON": "json",
    "JSONB": "jsonb",
    "INET": "inet",
}


def _sa_type_to_pg(sa_type: Any) -> str:
    """将 SQLAlchemy 列类型转换为 PostgreSQL 类型名"""
    type_name = type(sa_type).__name__.upper()

    # 特殊处理 Enum
    if type_name == "ENUM":
        return "USER-DEFINED"

    # 特殊处理 DateTime with timezone
    if type_name == "DATETIME" and getattr(sa_type, "timezone", False):
        return "timestamp with time zone"

    # NUMERIC with precision
    if type_name == "NUMERIC":
        p = getattr(sa_type, "precision", None)
        s = getattr(sa_type, "scale", None)
        if p and s:
            return f"numeric({p},{s})"
        return "numeric"

    return _TYPE_MAP.get(type_name, type_name.lower())


async def ensure_tables(engine: AsyncEngine, *, auto_alter: bool = True) -> None:
    """
    启动时自动同步 ORM 模型到数据库

    流程:
    1. 对比 Base.metadata 中定义的表 vs 数据库中已存在的表
    2. 缺失的表 → CREATE TABLE
    3. 已存在的表 → 逐列对比, 缺失的列 → ALTER TABLE ADD COLUMN
    4. (dev mode) 类型不匹配的列 → ALTER TABLE ALTER COLUMN TYPE
    """
    from app.models.base import Base
    # 确保所有模型已注册到 Base.metadata
    import app.models  # noqa: F401 — 触发 __init__.py 中的全量 import

    # ── Step 1: 创建所有缺失的表 (独立事务) ──
    # 多 worker 环境下可能出现竞争 (第二个 worker 重复创建类型)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Base.metadata.create_all() — 表结构同步完成")
    except Exception as e:
        if "duplicate key" in str(e) or "already exists" in str(e):
            logger.info("ℹ️ 表已由其他 worker 创建, 跳过 create_all")
        else:
            raise

    if not auto_alter:
        return

    # ── Step 2: 逐列对比 (独立事务, 不受 Step 1 失败影响) ──
    async with engine.begin() as conn:
        def _sync_columns(sync_conn):
            """同步连接下的列对比与修正 (run_sync callback)"""
            insp = inspect(sync_conn)
            existing_tables = set(insp.get_table_names())

            for table in Base.metadata.sorted_tables:
                if table.name not in existing_tables:
                    continue  # 新表已由 create_all 创建

                # 获取数据库中现有的列信息
                db_columns = {
                    col["name"]: col for col in insp.get_columns(table.name)
                }

                for column in table.columns:
                    col_name = column.name

                    if col_name not in db_columns:
                        # ── 缺失列: ALTER TABLE ADD COLUMN ──
                        col_type = column.type.compile(
                            dialect=sync_conn.dialect
                        )

                        # 智能 NOT NULL 处理:
                        # 对已有数据的表, NOT NULL 列若无 DEFAULT 则先加为 NULL
                        has_default = (
                            column.server_default is not None
                            or column.nullable
                        )
                        nullable = "NULL" if (column.nullable or not has_default) else "NOT NULL"

                        # 构建 DEFAULT 子句
                        default_clause = ""
                        if column.server_default is not None:
                            default_val = column.server_default.arg
                            if callable(default_val):
                                default_val = default_val(None)
                            default_clause = f" DEFAULT {default_val}"
                        elif column.nullable:
                            default_clause = " DEFAULT NULL"

                        ddl = (
                            f"ALTER TABLE {table.name} "
                            f"ADD COLUMN {col_name} {col_type}"
                            f"{default_clause} {nullable}"
                        )
                        logger.warning(f"🔧 添加缺失字段: {ddl}")

                        # SAVEPOINT: 每个 ALTER 独立, 失败不影响后续
                        nested = sync_conn.begin_nested()
                        try:
                            sync_conn.execute(text(ddl))
                            nested.commit()
                        except Exception as e:
                            nested.rollback()
                            logger.error(
                                f"❌ 添加字段失败 {table.name}.{col_name}: {e}"
                            )

                    else:
                        # ── 已有列: 检查类型是否匹配 ──
                        db_col = db_columns[col_name]
                        db_type = str(db_col["type"]).lower()
                        expected_type = _sa_type_to_pg(column.type).lower()

                        # 粗略比较 (忽略精度差异的宽松模式)
                        if not _types_compatible(db_type, expected_type):
                            col_type_compiled = column.type.compile(
                                dialect=sync_conn.dialect
                            )
                            ddl = (
                                f"ALTER TABLE {table.name} "
                                f"ALTER COLUMN {col_name} "
                                f"TYPE {col_type_compiled} "
                                f"USING {col_name}::{col_type_compiled}"
                            )
                            logger.warning(
                                f"🔧 类型修正: {table.name}.{col_name} "
                                f"({db_type} → {expected_type}): {ddl}"
                            )

                            nested = sync_conn.begin_nested()
                            try:
                                sync_conn.execute(text(ddl))
                                nested.commit()
                            except Exception as e:
                                nested.rollback()
                                logger.error(
                                    f"❌ 类型修正失败 "
                                    f"{table.name}.{col_name}: {e}"
                                )

        await conn.run_sync(_sync_columns)
        logger.info("✅ 字段级别同步完成")


def _types_compatible(db_type: str, expected_type: str) -> bool:
    """
    宽松的类型兼容性检查

    允许的等价关系:
    - "character varying" ≈ "varchar"
    - "double precision" ≈ "float"
    - "timestamp with time zone" ≈ "timestamptz"
    - "user-defined" (PG enum) 跳过检查
    """
    if db_type == expected_type:
        return True

    # Enum 类型跳过
    if "user-defined" in db_type or "user-defined" in expected_type:
        return True

    # 标准化别名
    aliases = {
        "character varying": "varchar",
        "double precision": "float",
        "timestamp with time zone": "timestamptz",
        "timestamp without time zone": "timestamp",
        "bigint": "bigint",
        "integer": "integer",
        "smallint": "smallint",
        "boolean": "boolean",
    }

    norm_db = aliases.get(db_type, db_type)
    norm_exp = aliases.get(expected_type, expected_type)

    # 忽略 VARCHAR 长度差异 (varchar(64) ≈ varchar(255))
    if norm_db.startswith("varchar") and norm_exp.startswith("varchar"):
        return True

    # 忽略 NUMERIC 精度差异
    if norm_db.startswith("numeric") and norm_exp.startswith("numeric"):
        return True

    return norm_db == norm_exp
