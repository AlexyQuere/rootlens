from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from rootlens.observability.jaeger import (
    JaegerClient,
)
import os

JAEGER_URL = os.getenv(
    "ROOTLENS_JAEGER_URL",
    "http://localhost:8080",
)


def iter_spans(
    resource_spans,
):

    for resource_span in (
        resource_spans
    ):

        for scope in (
            resource_span.get(
                "scopeSpans",
                [],
            )
        ):

            for span in (
                scope.get(
                    "spans",
                    [],
                )
            ):

                yield span


def main() -> None:

    client = JaegerClient(
        JAEGER_URL
    )

    services = (
        client.list_services()
    )

    print(
        f"Services: {len(services)}"
    )

    print(
        ", ".join(
            services
        )
    )

    now = datetime.now(
        timezone.utc
    )

    result = client.find_traces(
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

    spans = list(
        iter_spans(
            result.resource_spans
        )
    )

    trace_ids = sorted(
        {
            span.get(
                "traceId"
            )
            for span in spans
            if span.get(
                "traceId"
            )
        }
    )

    print()
    print(
        "ResourceSpans: "
        f"{len(result.resource_spans)}"
    )

    print(
        f"Spans: {len(spans)}"
    )

    print(
        "Unique trace IDs: "
        f"{len(trace_ids)}"
    )

    if not trace_ids:

        print(
            "No checkout traces found."
        )
        return

    trace_id = trace_ids[0]

    print()
    print(
        f"Fetching trace: "
        f"{trace_id}"
    )

    trace = client.get_trace(
        trace_id
    )

    full_spans = list(
        iter_spans(
            trace.resource_spans
        )
    )

    print(
        "Fetched ResourceSpans: "
        f"{len(trace.resource_spans)}"
    )

    print(
        "Fetched spans: "
        f"{len(full_spans)}"
    )


if __name__ == "__main__":
    main()