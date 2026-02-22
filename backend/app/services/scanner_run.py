"""
Scanner Daemon 独立入口

运行:
  python3 -m app.services.scanner_run
  或
  docker compose up scanner

设计:
  - 独立进程, 不依赖 FastAPI/Uvicorn
  - 仅需 DB + Redis 连接
  - 通过 Redis pub/sub channel: "alphatheta:signals" 广播信号
  - 定期心跳写入 Redis key: "scanner:heartbeat"
"""

import asyncio
import logging
import sys

# 确保项目根在 sys.path
sys.path.insert(0, "/app")


async def main():
    """Scanner Daemon 主入口"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger("alphatheta.scanner")

    logger.info("═" * 60)
    logger.info("  AlphaTheta Scanner Daemon v2.0")
    logger.info("  独立进程模式 — Redis pub/sub 广播信号")
    logger.info("═" * 60)

    # 延迟导入 (确保 settings 先加载)
    from app.services.scanner_daemon import scanner_loop
    await scanner_loop()


if __name__ == "__main__":
    asyncio.run(main())
