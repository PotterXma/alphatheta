"""
容灾报警通知中心 — 异步 Webhook 预警

设计要点:
1. send_critical_alert() 绝不允许抛异常到调用方 — 自身失败只写日志
2. 消息包含: 时间、Ticker、错误堆栈、服务器标识
3. 支持 Telegram / 企业微信 / 自定义 Webhook
4. 网络请求超时 5s, 失败重试 1 次
"""

import asyncio
import logging
import os
import traceback
from datetime import datetime, timezone

import httpx

logger = logging.getLogger("alphatheta.notifier")

# 从环境变量读取 Webhook URL
# 支持: Telegram Bot API, 企业微信, Slack, 通用 Webhook
WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "")
SERVER_ID = os.getenv("SERVER_ID", "alphatheta-prod-01")


class NotificationService:
    """
    容灾报警服务 — 确保关键异常实时通知到管理员

    关键设计原则:
    - 本模块的任何异常都不会传播到调用方
    - 使用 fire-and-forget 模式: 报警失败不影响主交易流程
    - 所有 HTTP 请求带 5s 超时, 最多重试 1 次
    """

    def __init__(self, webhook_url: str | None = None):
        self._webhook_url = webhook_url or WEBHOOK_URL
        self._client = httpx.AsyncClient(timeout=5.0)
        self._send_lock = asyncio.Lock()

    async def send_critical_alert(
        self,
        title: str,
        message: str,
        ticker: str | None = None,
        error_stack: str | None = None,
        severity: str = "CRITICAL",
    ) -> bool:
        """
        发送关键报警 — 容灾通知

        参数:
            title: 报警标题 (如 "Partial Fill Detected")
            message: 报警正文
            ticker: 受影响的标的代码
            error_stack: 错误堆栈 (可选)
            severity: 严重级别: CRITICAL / WARNING / INFO

        返回:
            bool — 是否发送成功 (失败只日志, 不抛异常)
        """
        try:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

            # ── 构建报警消息体 ──
            alert_body = (
                f"🚨 [{severity}] {title}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⏰ 时间: {now}\n"
                f"🖥 服务器: {SERVER_ID}\n"
            )
            if ticker:
                alert_body += f"📊 标的: {ticker}\n"
            alert_body += f"📝 详情: {message}\n"

            if error_stack:
                # 截断过长的堆栈 (Webhook 有字段长度限制)
                truncated = error_stack[:500]
                alert_body += f"\n🔍 堆栈:\n```\n{truncated}\n```"

            # ── 发送到 Webhook ──
            if not self._webhook_url:
                logger.warning(f"[Notifier] No WEBHOOK_URL configured, alert logged only: {title}")
                logger.error(alert_body)
                return False

            return await self._send_webhook(alert_body)

        except Exception as e:
            # ── 最终兜底: 本模块永不崩溃 ──
            logger.error(f"[Notifier] Alert send failed (swallowed): {e}")
            return False

    async def _send_webhook(self, text: str, retries: int = 1) -> bool:
        """
        发送 Webhook — 支持 Telegram / 企业微信 / Slack 格式

        自动检测 URL 类型:
        - api.telegram.org → Telegram Bot API
        - qyapi.weixin.qq.com → 企业微信
        - hooks.slack.com → Slack
        - 其他 → 通用 JSON POST
        """
        url = self._webhook_url

        for attempt in range(retries + 1):
            try:
                # ── 自动适配 Webhook 格式 ──
                if "api.telegram.org" in url:
                    # Telegram Bot: POST /sendMessage
                    # URL 格式: https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<ID>
                    payload = {"text": text, "parse_mode": "Markdown"}
                elif "qyapi.weixin.qq.com" in url:
                    # 企业微信 Webhook
                    payload = {
                        "msgtype": "text",
                        "text": {"content": text},
                    }
                elif "hooks.slack.com" in url:
                    # Slack Incoming Webhook
                    payload = {"text": text}
                else:
                    # 通用 Webhook
                    payload = {"title": "AlphaTheta Alert", "body": text}

                async with self._send_lock:
                    resp = await self._client.post(url, json=payload)

                if resp.status_code < 300:
                    logger.info(f"[Notifier] Alert sent successfully (attempt {attempt + 1})")
                    return True
                else:
                    logger.warning(f"[Notifier] Webhook returned {resp.status_code}, retrying...")

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                logger.warning(f"[Notifier] Webhook attempt {attempt + 1} failed: {e}")
                if attempt < retries:
                    await asyncio.sleep(1)  # 1s 后重试

        logger.error("[Notifier] All webhook attempts exhausted — alert lost")
        return False

    async def close(self):
        """清理 HTTP 客户端"""
        await self._client.aclose()


# ── 模块级单例 ──
_notifier: NotificationService | None = None


def get_notifier() -> NotificationService:
    """获取通知服务单例"""
    global _notifier
    if _notifier is None:
        _notifier = NotificationService()
    return _notifier
