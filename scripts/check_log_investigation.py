from __future__ import annotations

import argparse
import os

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from rootlens.observability.log_investigation import (
    LogInvestigationTool,
)

from rootlens.observability.opensearch import (
    OpenSearchClient,
)


def main() -> None:

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--trace-id",
        required=True,
    )

    parser.add_argument(
        "--minutes",
        type=int,
        default=180,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=200,
    )

    args = parser.parse_args()

    base_url = os.getenv(
        "ROOTLENS_OPENSEARCH_URL",
        "http://localhost:9200",
    )

    client = OpenSearchClient(
        base_url
    )

    tool = (
        LogInvestigationTool()
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

        trace_id=(
            args.trace_id
        ),

        limit=args.limit,

        time_field=(
            "observedTimestamp"
        ),
    )

    logs = result.logs

    summary = tool.summarize(
        logs
    )

    print(
        "=" * 90
    )

    print(
        "LOG INVESTIGATION"
    )

    print(
        "=" * 90
    )

    print(
        f"trace_id: "
        f"{args.trace_id}"
    )

    print(
        f"logs: "
        f"{summary.log_count}"
    )

    print(
        f"total hits: "
        f"{result.total_hits}"
    )

    print()

    print(
        "SERVICE COUNTS"
    )

    for (
        service,
        count,
    ) in summary.service_counts:

        print(
            f"  "
            f"{service:<22}"
            f"{count}"
        )

    print()

    print(
        "SEVERITY COUNTS"
    )

    for (
        severity,
        count,
    ) in summary.severity_counts:

        print(
            f"  "
            f"{severity:<22}"
            f"{count}"
        )

    print()

    duplicates = (
        tool
        .find_possible_duplicates(
            logs
        )
    )

    print(
        "POSSIBLE DUPLICATE GROUPS"
    )

    print(
        f"  groups: "
        f"{len(duplicates)}"
    )

    for group in duplicates:

        signature = (
            group.signature
        )

        print(
            "  "
            f"{signature.service_name} "
            f"count={group.count} "
            f"span="
            f"{signature.span_id} "
            f"body="
            f"{signature.body_key}"
        )

    print()

    print(
        "LARGEST TIMESTAMP "
        "DIFFERENCES"
    )

    differences = (
        tool
        .largest_timestamp_differences(
            logs,
            limit=10,
        )
    )

    for item in differences:

        print(
            "  "
            f"{(item.service_name or '-'):20}"
            f"{item.observed_minus_event_ms:18.3f} ms "
            f"span="
            f"{item.span_id or '-'}"
        )

    print()

    print(
        "ERROR-LIKE RAW "
        "SEVERITIES"
    )

    for severity in (
        "ERROR",
        "error",
        "Error",
    ):

        matching = (
            tool.find_logs(
                logs,
                severity_text=severity,
            )
        )

        for log in matching:

            print(
                "  "
                f"{log.service_name}: "
                f"{log.body_text}"
            )


if __name__ == "__main__":
    main()