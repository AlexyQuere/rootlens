from __future__ import annotations

import argparse
import os

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from rootlens.observability.opensearch import (
    OpenSearchClient,
)


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--service",
        default="checkout",
    )

    parser.add_argument(
        "--trace-id",
        default=None,
    )

    parser.add_argument(
        "--minutes",
        type=int,
        default=30,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=20,
    )

    parser.add_argument(
        "--time-field",
        choices=(
            "observedTimestamp",
            "@timestamp",
        ),
        default=(
            "observedTimestamp"
        ),
    )

    args = parser.parse_args()

    base_url = os.getenv(
        "ROOTLENS_OPENSEARCH_URL",
        "http://localhost:9200",
    )

    client = OpenSearchClient(
        base_url
    )

    end = datetime.now(
        timezone.utc
    )

    start = (
        end
        - timedelta(
            minutes=args.minutes
        )
    )

    result = client.search_logs(
        start=start,
        end=end,

        service_name=(
            None
            if args.trace_id
            else args.service
        ),

        trace_id=args.trace_id,

        limit=args.limit,

        time_field=(
            args.time_field
        ),
    )

    print(
        f"OpenSearch: {base_url}"
    )

    print(
        f"Window: "
        f"{start.isoformat()} "
        f"-> {end.isoformat()}"
    )

    print(
        f"Query time field: "
        f"{result.query.time_field}"
    )

    print(
        f"Total hits: "
        f"{result.total_hits}"
    )

    print(
        f"Returned: "
        f"{len(result.logs)}"
    )

    print(
        f"Took: "
        f"{result.took_ms} ms"
    )

    print()

    for log in result.logs:
        print(
            f"event="
            f"{log.event_timestamp_raw or '-'}"
        )

        print(
            f"observed="
            f"{log.observed_timestamp_raw or '-'}"
        )

        print(
            f"  "
            f"{(log.service_name or '-'):18} "
            f"{(log.severity_text or '-'):12} "
            f"{log.body_text or repr(log.body)}"
        )

        print(
            "  "
            f"trace={log.trace_id or '-'} "
            f"span={log.span_id or '-'}"
        )

        delta = (
            log.observed_minus_event_ms
        )

        if delta is not None:
            print(
                "  "
                "observed_minus_event_ms="
                f"{delta:.3f}"
            )

        print()


if __name__ == "__main__":
    main()