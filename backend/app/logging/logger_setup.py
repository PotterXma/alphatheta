"""
AlphaTheta v2 — Structured Logging Hub (logger_setup.py)

金融级日志中枢:
- Console: 人类可读彩色输出 + [trace_id]
- File: 纯 JSON 轮转输出 (00:00 / 30 days / zip)
- 脱敏: password/secret/token/api_key/Authorization → ***[MASKED]***
- 桥接: 标准 logging → loguru 自动重定向

Usage:
    from app.logging.logger_setup import logger, setup_logging
    setup_logging()
    logger.info("Hello", extra_field="value")
"""

from __future__ import annotations

import json
import logging
import re
import sys
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from loguru import logger as _loguru_logger

# ── 重导出 ─────────────────────────────────────────────────────────
logger = _loguru_logger

# ── Trace ID Context Var (供中间件和 Daemon 共用) ──────────────────
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="no-trace")

# ── 脱敏配置 ──────────────────────────────────────────────────────
SENSITIVE_KEYS = frozenset({
    "password", "secret", "token", "api_key", "apikey",
    "authorization", "access_token", "refresh_token",
    "private_key", "client_secret",
})

_MASK = "***[MASKED]***"

# 正则: Bearer xxx, api_key=xxx, token=xxx, password=xxx 等
_SENSITIVE_PATTERN = re.compile(
    r"(Bearer\s+)\S+"            # Bearer token
    r"|(api_key|token|password|secret|authorization|access_token|refresh_token)"
    r"[\s]*[=:]\s*\S+",
    re.IGNORECASE,
)


# ══════════════════════════════════════════════════════════════════
# 脱敏引擎
# ══════════════════════════════════════════════════════════════════

def _sanitize_value(key: str, value: Any) -> Any:
    """对敏感 key 的值进行脱敏。"""
    if isinstance(value, str) and key.lower() in SENSITIVE_KEYS:
        return _MASK
    if isinstance(value, dict):
        return _sanitize_dict(value)
    return value


def _sanitize_dict(d: dict) -> dict:
    """递归脱敏字典中的敏感字段。"""
    sanitized = {}
    for k, v in d.items():
        if k.lower() in SENSITIVE_KEYS:
            sanitized[k] = _MASK
        elif isinstance(v, dict):
            sanitized[k] = _sanitize_dict(v)
        else:
            sanitized[k] = v
    return sanitized


def _sanitize_message(msg: str) -> str:
    """正则脱敏 message 中的敏感模式。"""
    def _replacer(m: re.Match) -> str:
        text = m.group(0)
        if text.lower().startswith("bearer"):
            return "Bearer " + _MASK
        # key=value or key: value
        sep_idx = max(text.find("="), text.find(":"))
        if sep_idx >= 0:
            key_part = text[:sep_idx + 1]
            return key_part + " " + _MASK
        return _MASK

    return _SENSITIVE_PATTERN.sub(_replacer, msg)


def _patcher(record: dict) -> None:
    """loguru patcher: 注入 trace_id + 脱敏 extra 和 message。"""
    # 注入 trace_id
    record["extra"]["trace_id"] = trace_id_var.get("no-trace")

    # 脱敏 extra
    record["extra"] = _sanitize_dict(record["extra"])

    # 脱敏 message
    if isinstance(record["message"], str):
        record["message"] = _sanitize_message(record["message"])


# ══════════════════════════════════════════════════════════════════
# JSON Serializer (File sink)
# ══════════════════════════════════════════════════════════════════

def _json_serializer(message) -> str:
    """将 loguru record 序列化为单行 JSON。"""
    # loguru format callable 可能收到 Message 对象或 dict
    record = message.record if hasattr(message, "record") else message

    # 构建标准化 JSON 结构
    log_entry = {
        "timestamp": record["time"].strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
        "level": record["level"].name,
        "message": record["message"],
        "trace_id": record["extra"].get("trace_id", "no-trace"),
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
        "process": record["process"].id,
    }
    # 附加用户 extra (排除 trace_id 避免重复)
    user_extra = {
        k: v for k, v in record["extra"].items()
        if k != "trace_id"
    }
    if user_extra:
        log_entry["extra"] = user_extra

    # 异常信息
    if record["exception"] is not None:
        log_entry["exception"] = {
            "type": str(record["exception"].type.__name__) if record["exception"].type else None,
            "value": str(record["exception"].value) if record["exception"].value else None,
        }

    return json.dumps(log_entry, ensure_ascii=False, default=str) + "\n"


# ══════════════════════════════════════════════════════════════════
# InterceptHandler: 标准 logging → loguru 桥接
# ══════════════════════════════════════════════════════════════════

class InterceptHandler(logging.Handler):
    """将标准 logging 调用重定向到 loguru。"""

    def emit(self, record: logging.LogRecord) -> None:
        # 获取 loguru 对应的 level
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 找到实际的调用栈帧
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


# ══════════════════════════════════════════════════════════════════
# Console 格式
# ══════════════════════════════════════════════════════════════════

CONSOLE_FORMAT = (
    "<green>{time:HH:mm:ss.SSS}</green> "
    "<level>{level: <8}</level> "
    "<cyan>[{extra[trace_id]}]</cyan> "
    "<white>{module}</white>:<white>{function}</white> — "
    "<level>{message}</level>"
)


# ══════════════════════════════════════════════════════════════════
# 公共 API
# ══════════════════════════════════════════════════════════════════

def setup_logging(
    *,
    log_dir: str | Path = "logs",
    console_level: str = "DEBUG",
    file_level: str = "INFO",
    json_filename: str = "alphatheta.log",
    rotation: str = "00:00",
    retention: str = "30 days",
    compression: str = "zip",
) -> None:
    """
    初始化日志系统。应在 FastAPI lifespan startup 或 Daemon 启动时调用一次。

    Args:
        log_dir: 日志文件目录
        console_level: Console sink 日志级别
        file_level: File sink 日志级别
        json_filename: JSON 日志文件名
        rotation: 轮转策略
        retention: 保留策略
        compression: 压缩格式
    """
    # 清除默认 sink
    logger.remove()

    # 注册 patcher (trace_id 注入 + 脱敏)
    logger.configure(patcher=_patcher)

    # Sink 1: Console — 人类可读彩色
    logger.add(
        sys.stderr,
        format=CONSOLE_FORMAT,
        level=console_level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # Sink 2: File — JSON 机器可读 + 轮转
    log_path = Path(log_dir)
    try:
        log_path.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # Docker 容器内可能无权创建目录，回退到 /tmp
        log_path = Path("/tmp/alphatheta-logs")
        log_path.mkdir(parents=True, exist_ok=True)
        logger.warning("⚠️ Cannot create log dir '{}', falling back to '{}'", log_dir, log_path)

    logger.add(
        str(log_path / json_filename),
        format="{message}",
        level=file_level,
        rotation=rotation,
        retention=retention,
        compression=compression,
        serialize=True,      # loguru 内置 JSON 序列化
        backtrace=True,
        diagnose=False,      # 生产环境不暴露变量值
        enqueue=True,        # 异步写入，不阻塞主线程
    )

    # 桥接标准 logging → loguru
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # 抑制第三方库的噪音日志
    for lib in ("uvicorn", "uvicorn.access", "uvicorn.error",
                "sqlalchemy.engine", "httpx", "httpcore",
                "apscheduler", "asyncio"):
        logging.getLogger(lib).handlers = [InterceptHandler()]
        logging.getLogger(lib).setLevel(logging.WARNING)

    logger.info("📋 Logging system initialized | console={} file={}", console_level, file_level)
