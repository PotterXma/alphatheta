#!/usr/bin/env python3
"""
AlphaTheta Scanner Daemon — 入口文件

独立 asyncio 进程, PM2/Docker 守护运行。
不依赖 FastAPI — 直接调用 services 层。

用法:
  python3 scanner_entry.py
  pm2 start ecosystem.config.js
  docker compose up -d scanner
"""

import asyncio
import sys

# 确保 app 模块可导入
sys.path.insert(0, ".")

from app.services.scanner_daemon import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Scanner Daemon 已停止 (Ctrl+C)")
    except Exception as e:
        print(f"🔥 Scanner Daemon 崩溃: {e}")
        sys.exit(1)
