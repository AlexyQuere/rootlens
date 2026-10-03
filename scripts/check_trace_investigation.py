from __future__ import annotations

import os

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from rootlens.observability.jaeger import (
    JaegerClient,
)

from rootlens.observability.otlp_trace import (
    parse_otlp_traces,
)

from rootlens.observability.trace_investigation import (
    TraceInvestigationTool,
)


JAEGER_URL = os.getenv(
    "ROOTLENS_JAEGER_URL",
    "http://localhost:8080",
)


def main() -> None:

    client = JaegerClient(
        JAEGER_URL
    )

    tool = TraceInvestigationTool()

    now = datetime.now(
        timezone.utc
    )

    payload = client.find_traces(
        service_name="checkout",
        start=(
            now
            - timedelta(
                minutes=15
            )
        ),
        end=now,
        num_traces=5,
    )

    traces = parse_otlp_traces(
        payload
    )

    print(
        f"Traces: {len(traces)}"
    )

    for trace in traces:

        summary = tool.summarize(
            trace
        )

        pairs = (
            tool.find_client_server_pairs(
                trace
            )
        )

        unmatched = (
            tool.find_unmatched_client_spans(
                trace
            )
        )

        slow = tool.find_slow_spans(
            trace,
            limit=5,
        )

        print()
        print("=" * 90)

        print(
            f"TRACE {trace.trace_id}"
        )

        print("=" * 90)

        print(
            f"spans: "
            f"{summary.span_count}"
        )

        print(
            f"services: "
            f"{len(summary.services)}"
        )

        print(
            f"errors: "
            f"{summary.error_span_count}"
        )

        print(
            f"roots: "
            f"{summary.root_count}"
        )

        print(
            f"orphans: "
            f"{summary.orphan_count}"
        )

        print(
            "root duration_ms: "
            f"{summary.single_root_duration_ms}"
        )

        print(
            "envelope duration_ms: "
            f"{summary.envelope_duration_ms:.3f}"
        )

        print(
            "temporal violations: "
            f"{summary.temporal_violation_count}"
        )

        print(
            "max temporal skew_ms: "
            f"{summary.max_temporal_skew_ms:.3f}"
        )

        print(
            "root interval violations: "
            f"{trace.integrity.root_interval_violation_count}"
        )

        print(
            "max root interval skew_ms: "
            f"{trace.integrity.max_root_interval_skew_ms:.3f}"
        )

        print(
            f"client/server pairs: "
            f"{len(pairs)}"
        )

        print(
            f"unmatched clients: "
            f"{len(unmatched)}"
        )

        print()
        print(
            "TOP 5 LONGEST SPANS"
        )

        for span in slow:

            print(
                f"  "
                f"{span.service_name or '<unknown>':<18} "
                f"{span.kind.name:<8} "
                f"{span.status_code.name:<6} "
                f"{span.duration_ms:>9.3f} ms  "
                f"{span.operation_name}"
            )

        print()
        print(
            "UNMATCHED CLIENT SPANS"
        )

        for span in unmatched:

            print(
                f"  "
                f"{span.service_name or '<unknown>':<18} "
                f"{span.duration_ms:>9.3f} ms  "
                f"{span.operation_name}"
            )


if __name__ == "__main__":
    main() 