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


JAEGER_URL = os.getenv(
    "ROOTLENS_JAEGER_URL",
    "http://localhost:8080",
)


def main() -> None:

    client = JaegerClient(
        JAEGER_URL
    )

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
        f"Parsed traces: "
        f"{len(traces)}"
    )

    for trace in traces:

        print()
        print(
            f"Trace: {trace.trace_id}"
        )

        print(
            f"  spans: "
            f"{len(trace.spans)}"
        )

        print(
            f"  services: "
            f"{len(trace.services)}"
        )

        print(
            f"  envelope_duration_ms: "
            f"{trace.envelope_duration_ms:.3f}"
        )

        print(
            f"  temporal violations: "
            f"{trace.integrity.temporal_violation_count}"
        )

        print(
            f"  max temporal skew_ms: "
            f"{trace.integrity.max_temporal_skew_ms:.3f}"
        )

        print(
            f"  roots: "
            f"{len(trace.root_spans)}"
        )

        print(
            f"  orphans: "
            f"{len(trace.orphan_spans)}"
        )

        print(
            f"  error spans: "
            f"{len(trace.error_spans)}"
        )

        print(
            "  service names: "
            + ", ".join(
                trace.services
            )
        )

    if not traces:
        return

    trace = traces[0]

    print()
    print("=" * 80)
    print(
        "FIRST TRACE — FIRST 20 SPANS"
    )
    print("=" * 80)

    for span in trace.spans[
        :20
    ]:

        print(
            f"{span.service_name or '<unknown>':<18} "
            f"{span.kind.name:<10} "
            f"{span.status_code.name:<6} "
            f"{span.duration_ms:>9.3f} ms  "
            f"{span.operation_name}"
        )


if __name__ == "__main__":
    main()