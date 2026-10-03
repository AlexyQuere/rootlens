from __future__ import annotations

import time

from dataclasses import (
    fields,
    is_dataclass,
)
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import Any, Mapping

from rootlens.observability.evidence import (
    MetricEvidence,
    TimeWindow,
)
from rootlens.observability.jaeger import (
    JaegerClient,
)
from rootlens.observability.log_evidence import (
    LogEvidence,
)
from rootlens.observability.metrics import (
    MetricsTool,
)
from rootlens.observability.opensearch import (
    OpenSearchClient,
)
from rootlens.observability.otlp_trace import (
    parse_otlp_traces,
)
from rootlens.observability.prometheus import (
    PrometheusClient,
)


CHECKOUT_OPERATION = (
    "oteldemo.CheckoutService/PlaceOrder"
)

PAYMENT_OPERATION = (
    "oteldemo.PaymentService/Charge"
)



class PinnedPrometheusClient:
    """
    Adapter that pins Prometheus instant queries
    to one explicit evaluation timestamp.

    This lets RootLens wait for telemetry ingestion
    after an incident window without moving the
    analytical metric window.
    """

    def __init__(
        self,
        client: PrometheusClient,
        *,
        evaluation_time: datetime,
    ) -> None:
        if (
            evaluation_time.tzinfo
            is None
            or evaluation_time.utcoffset()
            is None
        ):
            raise ValueError(
                "evaluation_time must be "
                "timezone-aware."
            )

        self.client = client
        self.evaluation_time = (
            evaluation_time
        )

    def query(
        self,
        promql: str,
        *,
        time=None,
    ):
        effective_time = (
            self.evaluation_time
            if time is None
            else time
        )

        return self.client.query(
            promql,
            time=effective_time,
        )


def utc_now() -> datetime:
    return datetime.now(
        timezone.utc
    )


def wait_until(
    end: datetime,
    *,
    progress_every_seconds: int = 60,
) -> None:
    last_bucket = None

    while True:
        remaining = (
            end - utc_now()
        ).total_seconds()

        if remaining <= 0:
            return

        bucket = int(
            remaining
            // progress_every_seconds
        )

        if bucket != last_bucket:
            print(
                f"  {remaining:6.1f} s "
                "remaining"
            )

            last_bucket = bucket

        time.sleep(
            min(
                remaining,
                5.0,
            )
        )


def collect_metric_snapshot(
    *,
    prometheus_client: PrometheusClient,
    start: datetime,
    end: datetime,
) -> dict[
    str,
    MetricEvidence,
]:
    window = TimeWindow(
        start=start,
        end=end,
    )

    pinned_client = (
        PinnedPrometheusClient(
            prometheus_client,
            evaluation_time=end,
        )
    )

    tool = MetricsTool(
        pinned_client
    )

    metrics: dict[
        str,
        MetricEvidence,
    ] = {}

    metrics[
        "checkout_request_count"
    ] = tool.request_count(
        family="rpc_server",
        service="checkout",
        window=window,
        operation=CHECKOUT_OPERATION,
    )

    metrics[
        "checkout_request_rate"
    ] = tool.request_rate(
        family="rpc_server",
        service="checkout",
        window=window,
        operation=CHECKOUT_OPERATION,
    )

    metrics[
        "checkout_error_rate"
    ] = tool.error_rate(
        family="rpc_server",
        service="checkout",
        window=window,
        operation=CHECKOUT_OPERATION,
    )

    metrics[
        "checkout_p50"
    ] = tool.latency_quantile(
        family="rpc_server",
        service="checkout",
        window=window,
        operation=CHECKOUT_OPERATION,
        quantile=0.50,
    )

    metrics[
        "checkout_p95"
    ] = tool.latency_quantile(
        family="rpc_server",
        service="checkout",
        window=window,
        operation=CHECKOUT_OPERATION,
        quantile=0.95,
    )

    metrics[
        "checkout_p99"
    ] = tool.latency_quantile(
        family="rpc_server",
        service="checkout",
        window=window,
        operation=CHECKOUT_OPERATION,
        quantile=0.99,
    )

    metrics[
        "checkout_payment_request_count"
    ] = tool.request_count(
        family="rpc_client",
        service="checkout",
        window=window,
        operation=PAYMENT_OPERATION,
    )

    metrics[
        "checkout_payment_request_rate"
    ] = tool.request_rate(
        family="rpc_client",
        service="checkout",
        window=window,
        operation=PAYMENT_OPERATION,
    )

    metrics[
        "checkout_payment_error_rate"
    ] = tool.error_rate(
        family="rpc_client",
        service="checkout",
        window=window,
        operation=PAYMENT_OPERATION,
    )


    metrics[
        "frontend_http_error_rate"
    ] = tool.error_rate(
        family="http_server",
        service="frontend",
        window=window,
    )

    return metrics


def collect_trace_payload(
    *,
    jaeger_client: JaegerClient,
    start: datetime,
    end: datetime,
    trace_limit: int,
) -> dict[str, Any]:
    payload = (
        jaeger_client.find_traces(
            service_name="checkout",
            start=start,
            end=end,
            num_traces=trace_limit,
            operation_name=(
                CHECKOUT_OPERATION
            ),
        )
    )

    traces = (
        parse_otlp_traces(
            payload
        )
    )

    if len(
        traces
    ) >= trace_limit:
        raise RuntimeError(
            "Trace result reached the "
            f"configured limit "
            f"({trace_limit}). "
            "The window may be truncated. "
            "Increase --trace-limit."
        )

    trace_ids = tuple(
        sorted(
            trace.trace_id
            for trace in traces
        )
    )

    return {
        "service_name":
            "checkout",

        "operation_name":
            CHECKOUT_OPERATION,

        "start":
            start.isoformat(),

        "end":
            end.isoformat(),

        "trace_limit":
            trace_limit,

        "trace_count":
            len(traces),

        "trace_ids":
            list(trace_ids),

        "resource_spans":
            _jsonable(
                payload.resource_spans
            ),
    }


def collect_logs_for_traces(
    *,
    opensearch_client:
        OpenSearchClient,
    trace_ids: tuple[str, ...],
    analytical_start: datetime,
    analytical_end: datetime,
    query_margin_seconds: int,
    limit_per_trace: int,
) -> dict[str, Any]:
    discovery_start = (
        analytical_start
        - timedelta(
            seconds=(
                query_margin_seconds
            )
        )
    )

    discovery_end = (
        analytical_end
        + timedelta(
            seconds=(
                query_margin_seconds
            )
        )
    )

    trace_results = []

    total_logs = 0

    for index, trace_id in enumerate(
        trace_ids,
        start=1,
    ):
        print(
            "  logs "
            f"[{index}/{len(trace_ids)}] "
            f"{trace_id}"
        )

        result = (
            opensearch_client
            .search_logs(
                start=(
                    discovery_start
                ),

                end=(
                    discovery_end
                ),

                trace_id=trace_id,

                limit=(
                    limit_per_trace
                ),

                time_field=(
                    "observedTimestamp"
                ),
            )
        )

        logs = tuple(
            result.logs
        )

        total_hits = int(
            result.total_hits
        )

        if total_hits > len(
            logs
        ):
            raise RuntimeError(
                "OpenSearch result was "
                "truncated for "
                f"trace_id={trace_id}: "
                f"total_hits="
                f"{total_hits}, "
                f"returned="
                f"{len(logs)}. "
                "Increase "
                "--log-limit-per-trace."
            )

        total_logs += len(
            logs
        )

        trace_results.append(
            {
                "trace_id":
                    trace_id,

                "total_hits":
                    total_hits,

                "returned_logs":
                    len(logs),

                "query":
                    _jsonable(
                        result.query
                    ),

                "logs": [
                    serialize_log(
                        log
                    )
                    for log
                    in logs
                ],
            }
        )

    return {
        "discovery_time_field":
            "observedTimestamp",

        "analytical_start":
            analytical_start
            .isoformat(),

        "analytical_end":
            analytical_end
            .isoformat(),

        "discovery_start":
            discovery_start
            .isoformat(),

        "discovery_end":
            discovery_end
            .isoformat(),

        "query_margin_seconds":
            query_margin_seconds,

        "trace_count":
            len(trace_ids),

        "total_logs":
            total_logs,

        "traces":
            trace_results,
    }


def collect_phase(
    *,
    phase_name: str,

    window_seconds: int,

    ingestion_wait_seconds: int,

    trace_limit: int,

    log_query_margin_seconds: int,

    log_limit_per_trace: int,

    prometheus_client:
        PrometheusClient,

    jaeger_client:
        JaegerClient,

    opensearch_client:
        OpenSearchClient,
) -> dict[str, Any]:
    start = utc_now()

    end = (
        start
        + timedelta(
            seconds=window_seconds
        )
    )

    print()
    print(
        "=" * 90
    )

    print(
        f"{phase_name.upper()} "
        "ANALYTICAL WINDOW"
    )

    print(
        "=" * 90
    )

    print(
        f"start: "
        f"{start.isoformat()}"
    )

    print(
        f"end:   "
        f"{end.isoformat()}"
    )

    print(
        f"window: "
        f"{window_seconds}s"
    )

    print()

    wait_until(
        end
    )

    window_finished_at = (
        utc_now()
    )

    print()
    print(
        "Analytical window closed."
    )

    print(
        "Waiting "
        f"{ingestion_wait_seconds}s "
        "for telemetry ingestion..."
    )

    time.sleep(
        ingestion_wait_seconds
    )

    acquisition_started_at = (
        utc_now()
    )

    print()
    print(
        "Capturing pinned metrics..."
    )

    metrics = (
        collect_metric_snapshot(
            prometheus_client=(
                prometheus_client
            ),

            start=start,
            end=end,
        )
    )

    print(
        "Capturing Checkout traces..."
    )

    trace_payload = (
        collect_trace_payload(
            jaeger_client=(
                jaeger_client
            ),

            start=start,
            end=end,

            trace_limit=(
                trace_limit
            ),
        )
    )

    trace_ids = tuple(
        trace_payload[
            "trace_ids"
        ]
    )

    print(
        f"Captured "
        f"{len(trace_ids)} traces."
    )

    print(
        "Capturing logs by exact "
        "trace ID..."
    )

    logs = (
        collect_logs_for_traces(
            opensearch_client=(
                opensearch_client
            ),

            trace_ids=(
                trace_ids
            ),

            analytical_start=start,

            analytical_end=end,

            query_margin_seconds=(
                log_query_margin_seconds
            ),

            limit_per_trace=(
                log_limit_per_trace
            ),
        )
    )

    acquisition_completed_at = (
        utc_now()
    )

    return {
        "phase":
            phase_name,

        "window": {
            "start":
                start.isoformat(),

            "end":
                end.isoformat(),

            "seconds":
                window_seconds,

            "window_finished_at":
                window_finished_at
                .isoformat(),
        },

        "acquisition": {
            "ingestion_wait_seconds":
                ingestion_wait_seconds,

            "started_at":
                acquisition_started_at
                .isoformat(),

            "completed_at":
                acquisition_completed_at
                .isoformat(),
        },

        "metrics": {
            key:
                serialize_metric(
                    evidence
                )
            for key, evidence
            in metrics.items()
        },

        "traces":
            trace_payload,

        "logs":
            logs,
    }


def serialize_metric(
    evidence: MetricEvidence,
) -> dict[str, Any]:
    return {
        "name":
            evidence.name,

        "statistic":
            evidence.statistic,

        "value":
            evidence.value,

        "unit":
            evidence.unit,

        "service":
            evidence.service,

        "window": {
            "start":
                evidence.window
                .start
                .isoformat(),

            "end":
                evidence.window
                .end
                .isoformat(),
        },

        "promql":
            evidence.promql,

        "source":
            evidence.source,

        "labels": (
            dict(
                evidence.labels
            )
            if evidence.labels
            is not None
            else None
        ),
    }


def serialize_log(
    log: LogEvidence,
) -> dict[str, Any]:
    return {
        "index":
            log.index,

        "document_id":
            log.document_id,

        "event_timestamp": (
            log.event_timestamp
            .isoformat()
            if log.event_timestamp
            is not None
            else None
        ),

        "event_timestamp_raw":
            log.event_timestamp_raw,

        "observed_timestamp": (
            log.observed_timestamp
            .isoformat()
            if log.observed_timestamp
            is not None
            else None
        ),

        "observed_timestamp_raw":
            log.observed_timestamp_raw,

        "observed_minus_event_ms":
            log.observed_minus_event_ms,

        "service_name":
            log.service_name,

        "severity_text":
            log.severity_text,

        "severity_number":
            log.severity_number,

        "body":
            _jsonable(
                log.body
            ),

        "trace_id":
            log.trace_id,

        "span_id":
            log.span_id,

        "attributes":
            _jsonable(
                log.attributes
            ),

        "resource":
            _jsonable(
                log.resource_attributes
            ),

        "instrumentation_scope":
            _jsonable(
                log.instrumentation_scope
            ),

        "raw_source":
            _jsonable(
                log.raw_source
            ),
    }


def _jsonable(
    value: Any,
) -> Any:
    if value is None:
        return None

    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ):
        return value

    if isinstance(
        value,
        datetime,
    ):
        return value.isoformat()

    if (
        is_dataclass(value)
        and not isinstance(
            value,
            type,
        )
    ):
        return {
            field.name: _jsonable(
                getattr(
                    value,
                    field.name,
                )
            )
            for field
            in fields(
                value
            )
        }

    if isinstance(
        value,
        Mapping,
    ):
        return {
            str(key): _jsonable(
                item
            )
            for key, item
            in value.items()
        }

    if isinstance(
        value,
        (
            tuple,
            list,
            set,
        ),
    ):
        return [
            _jsonable(
                item
            )
            for item
            in value
        ]

    return str(
        value
    )