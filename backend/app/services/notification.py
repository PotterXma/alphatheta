"""
AlphaTheta Scanner — 多路消息网关

三通道异步非阻塞推送:
  1. broadcastToWeb()  — WebSocket (python-socketio)
  2. sendEmail()       — SMTP (aiosmtplib)
  3. sendWeChat()      — Server酱/PushPlus Webhook

每个通道独立 try-except — 单通道故障不影响其他通道。
"""

import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger("alphatheta.scanner.notify")


# ── 信号数据结构 ─────────────────────────────────────────────────

@dataclass
class ScannerSignal:
    """扫描引擎产出的标准信号格式"""
    ticker: str
    price: float
    rsi: float
    ivr: float
    direction: str  # "bullish" | "bearish"
    leaps_expiration: str  # ISO date
    leaps_dte: int
    call_strike: float
    call_ask: float
    strategy: str  # "leaps_deep_itm_call" etc.

    def to_title(self) -> str:
        """微信/邮件标题"""
        emoji = "📈" if self.direction == "bullish" else "📉"
        return f"{emoji} {self.ticker} LEAPS 建仓信号"

    def to_brief(self) -> str:
        """精简消息 (微信)"""
        return (
            f"🎯 **{self.ticker} LEAPS 建仓信号**\n\n"
            f"- 现价: ${self.price:.2f}\n"
            f"- RSI-14: {self.rsi:.1f} | IVR: {self.ivr:.1f}\n"
            f"- LEAPS 到期: {self.leaps_expiration} ({self.leaps_dte}d)\n"
            f"- Deep ITM Call: ${self.call_strike} @ ${self.call_ask:.2f}\n"
            f"- 策略: {self.strategy}\n"
        )

    def to_html(self) -> str:
        """HTML 邮件正文"""
        return f"""
        <div style="font-family:system-ui;max-width:600px;margin:0 auto;padding:20px;">
            <h2 style="color:#06b6d4;">🎯 {self.ticker} LEAPS 建仓信号</h2>
            <table style="width:100%;border-collapse:collapse;margin:16px 0;">
                <tr><td style="padding:8px;border-bottom:1px solid #334155;color:#94a3b8;">现价</td>
                    <td style="padding:8px;border-bottom:1px solid #334155;font-weight:bold;">${self.price:.2f}</td></tr>
                <tr><td style="padding:8px;border-bottom:1px solid #334155;color:#94a3b8;">RSI-14</td>
                    <td style="padding:8px;border-bottom:1px solid #334155;">{self.rsi:.1f}</td></tr>
                <tr><td style="padding:8px;border-bottom:1px solid #334155;color:#94a3b8;">IV Rank</td>
                    <td style="padding:8px;border-bottom:1px solid #334155;">{self.ivr:.1f}</td></tr>
                <tr><td style="padding:8px;border-bottom:1px solid #334155;color:#94a3b8;">LEAPS 到期</td>
                    <td style="padding:8px;border-bottom:1px solid #334155;">{self.leaps_expiration} ({self.leaps_dte}d)</td></tr>
                <tr><td style="padding:8px;border-bottom:1px solid #334155;color:#94a3b8;">Deep ITM Call</td>
                    <td style="padding:8px;border-bottom:1px solid #334155;font-weight:bold;">${self.call_strike} @ ${self.call_ask:.2f}</td></tr>
                <tr><td style="padding:8px;color:#94a3b8;">策略</td>
                    <td style="padding:8px;font-weight:bold;color:#06b6d4;">{self.strategy}</td></tr>
            </table>
            <p style="color:#64748b;font-size:12px;">AlphaTheta Scanner Daemon — 自动生成</p>
        </div>
        """

    def to_dict(self) -> dict[str, Any]:
        """WebSocket JSON payload"""
        return {
            "type": "scanner_signal",
            "ticker": self.ticker,
            "price": self.price,
            "rsi": self.rsi,
            "ivr": self.ivr,
            "direction": self.direction,
            "leaps_expiration": self.leaps_expiration,
            "leaps_dte": self.leaps_dte,
            "call_strike": self.call_strike,
            "call_ask": self.call_ask,
            "strategy": self.strategy,
        }


# ── 通知管理器 ─────────────────────────────────────────────────

class NotificationManager:
    """
    多路消息网关 — 三通道异步并行推送

    配置通过环境变量:
      - SERVERCHAN_SENDKEY: Server酱 SendKey
      - PUSHPLUS_TOKEN: PushPlus Token (备选)
      - SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, NOTIFY_EMAIL_TO
      - WS_ENABLED: "1" 启用 WebSocket (需要 sio 实例)
    """

    def __init__(self, sio=None):
        """
        Args:
            sio: python-socketio AsyncServer 实例 (可选)
        """
        self.sio = sio

        # 微信通道
        self.serverchan_key = os.getenv("SERVERCHAN_SENDKEY", "")
        self.pushplus_token = os.getenv("PUSHPLUS_TOKEN", "")

        # Email 通道
        self.smtp_host = os.getenv("SMTP_HOST", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_pass = os.getenv("SMTP_PASS", "")
        self.email_to = os.getenv("NOTIFY_EMAIL_TO", "")

        # 通道状态
        self._log_channel_status()

    def _log_channel_status(self):
        """启动时记录各通道配置状态"""
        channels = []
        if self.serverchan_key:
            channels.append("WeChat(Server酱)")
        if self.pushplus_token:
            channels.append("WeChat(PushPlus)")
        if self.smtp_host and self.smtp_user:
            channels.append("Email")
        if self.sio:
            channels.append("WebSocket")
        logger.info(f"📡 通知网关初始化 | 活跃通道: {', '.join(channels) or '(无)'}")

    # ── 微信推送 (Server酱 / PushPlus) ───────────────────────────

    async def sendWeChat(self, signal: ScannerSignal) -> bool:
        """
        微信推送 — Server酱优先, PushPlus 备选

        Server酱: POST https://sctapi.ftqq.com/{SENDKEY}.send
        PushPlus: POST https://www.pushplus.plus/send
        """
        # 尝试 Server酱
        if self.serverchan_key:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        f"https://sctapi.ftqq.com/{self.serverchan_key}.send",
                        json={
                            "title": signal.to_title(),
                            "desp": signal.to_brief(),
                        },
                    )
                    data = resp.json()
                    if resp.status_code == 200 and data.get("code") == 0:
                        logger.info(f"✅ 微信推送成功 (Server酱): {signal.ticker}")
                        return True
                    else:
                        logger.warning(
                            f"⚠️ Server酱返回异常: {data.get('message', resp.status_code)}"
                        )
            except Exception as e:
                logger.error(f"❌ Server酱推送失败: {e}")

        # 回退到 PushPlus
        if self.pushplus_token:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        "https://www.pushplus.plus/send",
                        json={
                            "token": self.pushplus_token,
                            "title": signal.to_title(),
                            "content": signal.to_html(),
                            "template": "html",
                        },
                    )
                    if resp.status_code == 200:
                        logger.info(f"✅ 微信推送成功 (PushPlus): {signal.ticker}")
                        return True
            except Exception as e:
                logger.error(f"❌ PushPlus 推送失败: {e}")

        if not self.serverchan_key and not self.pushplus_token:
            logger.debug("微信通道未配置，跳过")

        return False

    # ── Email 推送 ───────────────────────────────────────────────

    async def sendEmail(self, signal: ScannerSignal) -> bool:
        """通过 SMTP 发送 HTML 格式信号研报"""
        if not self.smtp_host or not self.smtp_user:
            logger.debug("Email 通道未配置 (缺 SMTP_HOST/SMTP_USER)，跳过")
            return False

        try:
            import aiosmtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart("alternative")
            msg["From"] = self.smtp_user
            msg["To"] = self.email_to
            msg["Subject"] = signal.to_title()

            msg.attach(MIMEText(signal.to_brief(), "plain", "utf-8"))
            msg.attach(MIMEText(signal.to_html(), "html", "utf-8"))

            await aiosmtplib.send(
                msg,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_pass,
                use_tls=True,
            )
            logger.info(f"✅ Email 推送成功: {signal.ticker} → {self.email_to}")
            return True

        except ImportError:
            logger.warning("aiosmtplib 未安装，Email 通道不可用")
            return False
        except Exception as e:
            logger.error(f"❌ Email 推送失败: {e}")
            return False

    # ── WebSocket 推送 ───────────────────────────────────────────

    async def broadcastToWeb(self, signal: ScannerSignal) -> bool:
        """通过 python-socketio 推送到前端"""
        if not self.sio:
            logger.debug("WebSocket 通道未配置 (无 sio 实例)，跳过")
            return False

        try:
            await self.sio.emit("scanner_signal", signal.to_dict())
            logger.info(f"✅ WebSocket 推送成功: {signal.ticker}")
            return True
        except Exception as e:
            logger.error(f"❌ WebSocket 推送失败: {e}")
            return False

    # ── 广播 (并行三通道) ────────────────────────────────────────

    async def broadcast(self, signal: ScannerSignal) -> dict[str, bool]:
        """
        并行触发所有通道 — 各自 try-except 隔离

        Returns:
            {"wechat": True/False, "email": True/False, "ws": True/False}
        """
        import asyncio

        results = await asyncio.gather(
            self._safe_send("wechat", self.sendWeChat, signal),
            self._safe_send("email", self.sendEmail, signal),
            self._safe_send("ws", self.broadcastToWeb, signal),
            return_exceptions=True,
        )

        status = {}
        for name, result in zip(["wechat", "email", "ws"], results):
            if isinstance(result, Exception):
                logger.error(f"❌ 通道 {name} 异常: {result}")
                status[name] = False
            else:
                status[name] = result

        sent = sum(1 for v in status.values() if v)
        logger.info(f"📡 广播完成 [{signal.ticker}]: {sent}/3 通道成功 | {status}")
        return status

    async def _safe_send(self, name: str, fn, signal: ScannerSignal) -> bool:
        """安全包装单通道发送"""
        try:
            return await fn(signal)
        except Exception as e:
            logger.error(f"❌ {name} 通道未捕获异常: {e}")
            return False

    # ── 心跳推送 (仅微信) ────────────────────────────────────────

    async def send_heartbeat(self, watchlist_count: int, redis_ok: bool) -> bool:
        """
        每日开盘前心跳 — 推送到微信

        Args:
            watchlist_count: 监控池标的数量
            redis_ok: Redis 是否连通
        """
        import os

        redis_status = "✅ OK" if redis_ok else "❌ 断开"
        pid = os.getpid()

        message = (
            f"🟢 **AlphaTheta Scanner 心跳**\n\n"
            f"- PID: {pid}\n"
            f"- 监控池: {watchlist_count} 只标的\n"
            f"- Redis: {redis_status}\n"
            f"- 状态: 正常运行中\n"
        )

        if self.serverchan_key:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        f"https://sctapi.ftqq.com/{self.serverchan_key}.send",
                        json={"title": "🟢 AlphaTheta Scanner 心跳", "desp": message},
                    )
                    if resp.status_code == 200:
                        logger.info(f"💚 心跳推送成功 | 监控池: {watchlist_count} | Redis: {redis_status}")
                        return True
            except Exception as e:
                logger.error(f"心跳推送失败: {e}")

        logger.info(f"💚 心跳 (本地) | PID: {pid} | 监控池: {watchlist_count} | Redis: {redis_status}")
        return False
