"""Admin, Audit & Reporting API Router"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_redis
from app.schemas.admin import (
    ApiKeyCreate,
    ApiKeyResponse,
    DailyReport,
    HealthCheck,
    KillSwitchStatus,
    KillSwitchToggle,
    LogEntry,
)
from app.services.admin import AdminService

router = APIRouter()


@router.post("/api-keys", response_model=dict)
async def create_api_key(req: ApiKeyCreate, db: AsyncSession = Depends(get_db)):
    svc = AdminService(db)
    key = await svc.create_api_key(req)
    return {"id": str(key.id), "provider": key.provider, "status": "created"}


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(db: AsyncSession = Depends(get_db)):
    svc = AdminService(db)
    return await svc.list_api_keys()


@router.post("/kill-switch", response_model=KillSwitchStatus)
async def toggle_kill_switch(
    toggle: KillSwitchToggle,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    svc = AdminService(db, redis)
    return await svc.toggle_kill_switch(toggle)


@router.get("/kill-switch", response_model=KillSwitchStatus)
async def get_kill_switch(db: AsyncSession = Depends(get_db)):
    svc = AdminService(db)
    return await svc.get_kill_switch_status()


@router.get("/logs", response_model=list[LogEntry])
async def get_logs(limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)):
    svc = AdminService(db)
    return await svc.get_logs(limit, offset)


@router.get("/reports/daily", response_model=DailyReport)
async def get_daily_report(date: str = "2026-02-20", db: AsyncSession = Depends(get_db)):
    svc = AdminService(db)
    return await svc.generate_daily_report(date)


@router.get("/health", response_model=HealthCheck)
async def health_check():
    """全面健康检查 — PG, Redis, Broker, NTP"""
    from app.config import get_settings
    settings = get_settings()
    # TODO: 实际 ping 各子系统
    return HealthCheck(
        status="healthy",
        env_mode=settings.env_mode.value,
    )


@router.get("/visitor-stats")
async def visitor_stats(redis=Depends(get_redis)):
    """
    访客 IP 统计 — 从 Redis 读取

    返回: 独立 IP 列表 + 总请求数 + 每日 UV + 路径热度 + 地理位置
    """
    import time
    import re

    # 1. 所有 IP (按最后访问时间倒序)
    ip_scores = await redis.zrevrangebyscore(
        "alphatheta:visitors:ips", "+inf", "-inf", withscores=True
    )

    private_pattern = re.compile(
        r'^(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.|127\.|::1|fc|fd)'
    )

    ips = []
    external_ip_list = []
    for ip, ts in ip_scores:
        entry = {
            "ip": ip,
            "last_seen": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)),
            "timestamp": ts,
            "is_private": bool(private_pattern.match(ip)),
            "geo": None,
        }
        ips.append(entry)
        if not entry["is_private"]:
            external_ip_list.append(ip)

    # 2. 批量查询外网 IP 地理位置 (带 Redis 缓存)
    if external_ip_list:
        geo_map = await _batch_geolocate(redis, external_ip_list)
        for entry in ips:
            if entry["ip"] in geo_map:
                entry["geo"] = geo_map[entry["ip"]]

    # 3. 总请求数
    total_hits = int(await redis.get("alphatheta:visitors:hits") or 0)

    # 4. 今日 UV
    today = time.strftime("%Y-%m-%d")
    today_uv = await redis.pfcount(f"alphatheta:visitors:daily:{today}")

    # 5. 最近 7 天 UV
    daily_uv = {}
    for i in range(7):
        day = time.strftime("%Y-%m-%d", time.localtime(time.time() - i * 86400))
        uv = await redis.pfcount(f"alphatheta:visitors:daily:{day}")
        daily_uv[day] = uv

    # 6. 路径热度 Top 20
    paths_raw = await redis.hgetall("alphatheta:visitors:paths") or {}
    paths = sorted(
        [{"path": k, "hits": int(v)} for k, v in paths_raw.items()],
        key=lambda x: x["hits"],
        reverse=True,
    )[:20]

    external_ips = [ip for ip in ips if not ip["is_private"]]

    return {
        "total_unique_ips": len(ips),
        "total_hits": total_hits,
        "today_uv": today_uv,
        "daily_uv": daily_uv,
        "external_ip_count": len(external_ips),
        "ips": ips,
        "external_ips": external_ips,
        "top_paths": paths,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


async def _batch_geolocate(redis, ip_list: list[str]) -> dict:
    """
    批量 IP 地理位置查询 — ip-api.com (免费, 45 req/min)

    策略:
    1. 先查 Redis 缓存 (TTL=7天)
    2. 未命中的批量请求 ip-api.com batch API
    3. 结果写回 Redis 缓存
    """
    import json
    import httpx
    import logging

    logger = logging.getLogger("alphatheta.geo")
    geo_map = {}
    uncached = []

    # 1. 查缓存
    for ip in ip_list:
        cached = await redis.get(f"alphatheta:geo:{ip}")
        if cached:
            try:
                geo_map[ip] = json.loads(cached)
            except Exception:
                uncached.append(ip)
        else:
            uncached.append(ip)

    if not uncached:
        return geo_map

    # 2. 批量查询 ip-api.com (最多 100 个/批)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # ip-api.com batch endpoint (POST, max 100)
            batch = [{"query": ip} for ip in uncached[:100]]
            resp = await client.post(
                "http://ip-api.com/batch?fields=query,status,country,regionName,city,isp,org",
                json=batch,
            )
            if resp.status_code == 200:
                results = resp.json()
                for item in results:
                    if item.get("status") == "success":
                        ip = item["query"]
                        geo = {
                            "country": item.get("country", ""),
                            "region": item.get("regionName", ""),
                            "city": item.get("city", ""),
                            "isp": item.get("isp", ""),
                            "org": item.get("org", ""),
                        }
                        geo_map[ip] = geo
                        # 缓存 7 天
                        await redis.setex(
                            f"alphatheta:geo:{ip}",
                            7 * 86400,
                            json.dumps(geo, ensure_ascii=False),
                        )
    except Exception as e:
        logger.warning(f"Geo lookup failed (non-fatal): {e}")

    return geo_map

