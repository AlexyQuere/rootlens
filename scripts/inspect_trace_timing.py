from __future__ import annotations

import os

from collections import defaultdict
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


def describe_span(
    span,
) -> str:

    return (
        f"{span.service_name or '<unknown>':<18} "
        f"{span.kind.name:<10} "
        f"{span.status_code.name:<6} "
        f"{span.duration_ms:>12.3f} ms  "
        f"{span.operation_name}"
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

    if not traces:
        print(
            "No traces found."
        )
        return

    trace = max(
        traces,
        key=lambda item:
            item.duration_ms,
    )

    print(
        "=" * 100
    )

    print(
        f"TRACE {trace.trace_id}"
    )

    print(
        "=" * 100
    )

    print()
    print(
        f"spans: {len(trace.spans)}"
    )

    print(
        f"services: {len(trace.services)}"
    )

    print(
        f"roots: {len(trace.root_spans)}"
    )

    print(
        f"orphans: {len(trace.orphan_spans)}"
    )

    print(
        f"envelope duration: "
        f"{trace.duration_ms:.3f} ms"
    )

    print()

    print(
        "trace envelope start:"
    )

    print(
        datetime.fromtimestamp(
            trace.start_time_unix_nano
            / 1_000_000_000,
            tz=timezone.utc,
        ).isoformat()
    )

    print(
        "trace envelope end:"
    )

    print(
        datetime.fromtimestamp(
            trace.end_time_unix_nano
            / 1_000_000_000,
            tz=timezone.utc,
        ).isoformat()
    )

    print()
    print(
        "=" * 100
    )

    print(
        "ROOT SPANS"
    )

    print(
        "=" * 100
    )

    for span in trace.root_spans:

        print()
        print(
            describe_span(
                span
            )
        )

        print(
            "  start:",
            span.start_time.isoformat(),
        )

        print(
            "  end:  ",
            span.end_time.isoformat(),
        )

        print(
            "  span_id:",
            span.span_id,
        )

    print()
    print(
        "=" * 100
    )

    print(
        "10 EARLIEST SPANS"
    )

    print(
        "=" * 100
    )

    earliest = sorted(
        trace.spans,
        key=lambda span:
            span.start_time_unix_nano,
    )[:10]

    for span in earliest:

        print()
        print(
            describe_span(
                span
            )
        )

        print(
            "  start:",
            span.start_time.isoformat(),
        )

        print(
            "  end:  ",
            span.end_time.isoformat(),
        )

        print(
            "  span_id:",
            span.span_id,
        )

        print(
            "  parent:",
            span.parent_span_id,
        )

    print()
    print(
        "=" * 100
    )

    print(
        "10 LATEST SPANS"
    )

    print(
        "=" * 100
    )

    latest = sorted(
        trace.spans,
        key=lambda span:
            span.end_time_unix_nano,
        reverse=True,
    )[:10]

    for span in latest:

        print()
        print(
            describe_span(
                span
            )
        )

        print(
            "  start:",
            span.start_time.isoformat(),
        )

        print(
            "  end:  ",
            span.end_time.isoformat(),
        )

        print(
            "  span_id:",
            span.span_id,
        )

        print(
            "  parent:",
            span.parent_span_id,
        )

    print()
    print(
        "=" * 100
    )

    print(
        "10 LONGEST SPANS"
    )

    print(
        "=" * 100
    )

    longest = sorted(
        trace.spans,
        key=lambda span:
            span.duration_ms,
        reverse=True,
    )[:10]

    for span in longest:

        print()
        print(
            describe_span(
                span
            )
        )

        print(
            "  start:",
            span.start_time.isoformat(),
        )

        print(
            "  end:  ",
            span.end_time.isoformat(),
        )

    print()
    print(
        "=" * 100
    )

    print(
        "SERVICE TIME WINDOWS"
    )

    print(
        "=" * 100
    )

    by_service = defaultdict(
        list
    )

    for span in trace.spans:

        by_service[
            span.service_name
            or "<unknown>"
        ].append(
            span
        )

    for service in sorted(
        by_service
    ):

        spans = (
            by_service[
                service
            ]
        )

        start = min(
            span.start_time_unix_nano
            for span in spans
        )

        end = max(
            span.end_time_unix_nano
            for span in spans
        )

        duration_ms = (
            end - start
        ) / 1_000_000

        start_dt = (
            datetime.fromtimestamp(
                start / 1_000_000_000,
                tz=timezone.utc,
            )
        )

        end_dt = (
            datetime.fromtimestamp(
                end / 1_000_000_000,
                tz=timezone.utc,
            )
        )

        print()

        print(
            service
        )

        print(
            f"  spans: "
            f"{len(spans)}"
        )

        print(
            f"  first: "
            f"{start_dt.isoformat()}"
        )

        print(
            f"  last:  "
            f"{end_dt.isoformat()}"
        )

        print(
            f"  envelope: "
            f"{duration_ms:.3f} ms"
        )

    print()
    print(
        "=" * 100
    )

    print(
        "PARENT / CHILD TEMPORAL VIOLATIONS"
    )

    print(
        "=" * 100
    )

    by_id = {
        span.span_id:
            span
        for span in trace.spans
    }

    violations = []

    for child in trace.spans:

        if (
            child.parent_span_id
            is None
        ):
            continue

        parent = by_id.get(
            child.parent_span_id
        )

        if parent is None:
            continue

        starts_before_parent = (
            child.start_time_unix_nano
            < parent.start_time_unix_nano
        )

        ends_after_parent = (
            child.end_time_unix_nano
            > parent.end_time_unix_nano
        )

        if (
            starts_before_parent
            or ends_after_parent
        ):
            violations.append(
                (
                    parent,
                    child,
                    starts_before_parent,
                    ends_after_parent,
                )
            )

    print(
        f"violations: "
        f"{len(violations)}"
    )

    for (
        parent,
        child,
        starts_before,
        ends_after,
    ) in violations[
        :20
    ]:

        print()
        print(
            "PARENT:",
            describe_span(
                parent
            ),
        )

        print(
            "CHILD: ",
            describe_span(
                child
            ),
        )

        print(
            "  starts before parent:",
            starts_before,
        )

        print(
            "  ends after parent:",
            ends_after,
        )


if __name__ == "__main__":
    main()