"""Prometheus Metrics 端点"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter, Response

router = APIRouter()

# ── Counters ──
RISK_REJECTIONS = Counter(
    "risk_rejections_total",
    "Total risk rejections",
    ["rule"],
)
ORDERS_SUBMITTED = Counter(
    "orders_submitted_total",
    "Total orders submitted",
    ["status"],
)
KILL_SWITCH_ACTIVATIONS = Counter(
    "kill_switch_activations_total",
    "Total kill switch activations",
)
RECONCILIATION_MISMATCHES = Counter(
    "reconciliation_mismatches_total",
    "Total reconciliation mismatches found",
)

# ── Histograms ──
API_LATENCY = Histogram(
    "api_request_duration_seconds",
    "API request duration",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)
BROKER_LATENCY = Histogram(
    "broker_api_latency_seconds",
    "Broker API call duration",
    ["operation"],
)

# ── Gauges ──
WS_CONNECTIONS = Gauge(
    "ws_active_connections",
    "Active WebSocket connections",
)


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
