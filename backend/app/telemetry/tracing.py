"""OpenTelemetry 分布式追踪初始化"""

import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger("alphatheta.telemetry")


def init_tracing(app, service_name: str, otlp_endpoint: str):
    """初始化 OpenTelemetry: FastAPI + httpx + SQLAlchemy auto-instrument"""
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    # 仅在显式配置了有效 OTLP 端点时才启用 span 导出
    # 空字符串或 "none" 表示跳过 — 避免无 collector 时大量 ERROR 日志
    if otlp_endpoint and otlp_endpoint.lower() not in ("", "none", "disabled"):
        try:
            exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info(f"OTLP exporter → {otlp_endpoint}")
        except Exception as e:
            logger.warning(f"OTLP exporter init failed (non-fatal): {e}")
    else:
        logger.info("OTLP exporter disabled (no endpoint configured)")

    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)

    # 尝试 instrument 其他库
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        HTTPXClientInstrumentor().instrument()
    except Exception:
        pass

    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        SQLAlchemyInstrumentor().instrument()
    except Exception:
        pass

    logger.info(f"OpenTelemetry initialized: service={service_name}")

    return trace.get_tracer(service_name)
