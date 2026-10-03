from __future__ import annotations

import argparse
import json
import os

from collections.abc import Mapping
from dataclasses import asdict
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from typing import Any

from rootlens.evaluation.log_incident import (
    observe_trace_logs,
)

from rootlens.observability.log_investigation import (
    LogInvestigationTool,
)

from rootlens.observability.opensearch import (
    OpenSearchClient,
)


def parse_time(
    value: str,
) -> datetime:
    parsed = datetime.fromisoformat(
        value.replace(
            "Z",
            "+00:00",
        )
    )

    if (
        parsed.tzinfo is None
        or parsed.utcoffset() is None
    ):
        raise ValueError(
            "Timestamp must be timezone-aware."
        )

    return parsed


def thaw(
    value: Any,
) -> Any:
    if isinstance(
        value,
        Mapping,
    ):
        return {
            str(key): thaw(item)
            for key, item
            in value.items()
        }

    if isinstance(
        value,
        tuple,
    ):
        return [
            thaw(item)
            for item in value
        ]

    if isinstance(
        value,
        list,
    ):
        return [
            thaw(item)
            for item in value
        ]

    return value


def serialize_log(
    log,
) -> dict[str, Any]:
    return {
        "index":
            log.index,

        "document_id":
            log.document_id,

        "event_timestamp":
            log.event_timestamp_raw,

        "observed_timestamp":
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
            thaw(
                log.body
            ),

        "trace_id":
            log.trace_id,

        "span_id":
            log.span_id,

        "attributes":
            thaw(
                log.attributes
            ),

        "resource":
            thaw(
                log.resource_attributes
            ),

        "instrumentation_scope":
            thaw(
                log.instrumentation_scope
            ),

        "raw_source":
            thaw(
                log.raw_source
            ),
    }


def serialize_query(
    query,
) -> dict[str, Any]:
    return {
        "index_pattern":
            query.index_pattern,

        "start":
            query.start.isoformat(),

        "end":
            query.end.isoformat(),

        "service_name":
            query.service_name,

        "trace_id":
            query.trace_id,

        "span_id":
            query.span_id,

        "severity_text":
            query.severity_text,

        "limit":
            query.limit,

        "time_field":
            query.time_field,

        "request_body":
            thaw(
                query.request_body
            ),

        "source":
            query.source,
    }


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--trace-id",
        required=True,
    )

    parser.add_argument(
        "--start",
        required=True,
    )

    parser.add_argument(
        "--end",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
    )

    args = parser.parse_args()

    start = parse_time(
        args.start
    )

    end = parse_time(
        args.end
    )

    if end <= start:
        raise ValueError(
            "end must be after start."
        )

    base_url = os.getenv(
        "ROOTLENS_OPENSEARCH_URL",
        "http://localhost:9200",
    )

    client = OpenSearchClient(
        base_url
    )

    tool = LogInvestigationTool()

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

    if result.timed_out:
        raise RuntimeError(
            "OpenSearch query timed out."
        )

    if (
        result.total_hits
        != len(
            result.logs
        )
    ):
        raise RuntimeError(
            "Log query was truncated: "
            f"total_hits={result.total_hits}, "
            f"returned={len(result.logs)}."
        )

    observation = observe_trace_logs(
        args.trace_id,
        result.logs,
        tool=tool,
    )

    duplicates = (
        tool.find_possible_duplicates(
            result.logs
        )
    )

    timestamp_differences = (
        tool
        .largest_timestamp_differences(
            result.logs,
            limit=10,
        )
    )

    output = {
        "experiment":
            "015C.4C",

        "case":
            "paymentUnreachable_post_restart",

        "captured_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "trace_id":
            args.trace_id,

        "opensearch_url":
            base_url,

        "query":
            serialize_query(
                result.query
            ),

        "total_hits":
            result.total_hits,

        "returned_logs":
            len(
                result.logs
            ),

        "took_ms":
            result.took_ms,

        "observation":
            asdict(
                observation
            ),

        "possible_duplicate_groups": [
            {
                "count":
                    group.count,

                "service_name":
                    group.signature
                    .service_name,

                "trace_id":
                    group.signature
                    .trace_id,

                "span_id":
                    group.signature
                    .span_id,

                "event_timestamp":
                    group.signature
                    .event_timestamp_raw,

                "severity_text":
                    group.signature
                    .severity_text,

                "body_key":
                    group.signature
                    .body_key,

                "document_ids": [
                    log.document_id
                    for log
                    in group.logs
                ],
            }
            for group
            in duplicates
        ],

        "largest_timestamp_differences": [
            {
                "service_name":
                    item.service_name,

                "trace_id":
                    item.trace_id,

                "span_id":
                    item.span_id,

                "event_timestamp":
                    item.event_timestamp
                    .isoformat(),

                "observed_timestamp":
                    item.observed_timestamp
                    .isoformat(),

                "observed_minus_event_ms":
                    item
                    .observed_minus_event_ms,

                "index":
                    item.index,

                "document_id":
                    item.document_id,
            }
            for item
            in timestamp_differences
        ],

        "logs": [
            serialize_log(
                log
            )
            for log
            in result.logs
        ],
    }

    output_path = Path(
        args.output
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        "=" * 90
    )

    print(
        "TRACE LOG CAPTURE"
    )

    print(
        "=" * 90
    )

    print(
        f"trace_id: "
        f"{args.trace_id}"
    )

    print(
        f"total_hits: "
        f"{result.total_hits}"
    )

    print(
        f"returned_logs: "
        f"{len(result.logs)}"
    )

    print()

    print(
        "SERVICES"
    )

    summary = tool.summarize(
        result.logs
    )

    for (
        service,
        count,
    ) in summary.service_counts:
        print(
            f"  {service:<22}"
            f"{count}"
        )

    print()

    print(
        "RAW ERROR-LIKE LOGS"
    )

    for severity in (
        "ERROR",
        "Error",
        "error",
    ):
        for log in tool.find_logs(
            result.logs,
            severity_text=severity,
        ):
            print(
                f"  {log.service_name}: "
                f"{log.body_text}"
            )

    print()

    print(
        f"Frozen artifact: "
        f"{output_path}"
    )


if __name__ == "__main__":
    main()