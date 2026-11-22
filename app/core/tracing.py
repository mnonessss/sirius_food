"""Экспорт трейсов OpenTelemetry в Jaeger по OTLP/HTTP."""
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.config import settings

_configured = False


def setup_tracing(service_name: str) -> None:
    """Включает экспорт span'ов. Повторный вызов в том же процессе ничего не меняет."""
    global _configured
    if _configured:
        return

    endpoint = settings.OTEL_EXPORTER_OTLP_ENDPOINT.rstrip("/")
    if not endpoint.endswith("/v1/traces"):
        endpoint = f"{endpoint}/v1/traces"

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=endpoint),
            schedule_delay_millis=500,
        )
    )
    trace.set_tracer_provider(provider)
    _configured = True
