from __future__ import annotations

import argparse
import json
import os

from dataclasses import (
    asdict,
)
from datetime import (
    datetime,
    timedelta,
)
from pathlib import Path
from types import MappingProxyType
from typing import Any

from rootlens.evaluation.log_incident import (
    compare_log_windows,
    observe_trace_logs,
    summarize_log_window,
)

from rootlens.observability.opensearch import (
    OpenSearchClient,
)


def parse_time(
    value: str,
) -> datetime:
    return datetime.fromisoformat(
        value.replace(
            "Z",
            "+00:00",
        )
    )


def thaw(
    value: Any,
) -> Any:
    if isinstance(
        value,
        MappingProxyType,
    ):
        return {
            key: thaw(item)
            for key, item
            in value.items()
        }

    if isinstance(
        value,
        dict,
    ):
        return {
            key: thaw(item)
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
                log
                .instrumentation_scope
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


def capture_window(
    *,
    client: OpenSearchClient,
    window: dict[str, Any],
    padding_seconds: int,
    limit_per_trace: int,
) -> dict[str, Any]:
    trace_ids = [
        item["trace_id"]
        for item
        in window[
            "raw_traces"
        ]
    ]

    original_start = parse_time(
        window["start"]
    )

    original_end = parse_time(
        window["end"]
    )

    query_start = (
        original_start
        - timedelta(
            seconds=(
                padding_seconds
            )
        )
    )

    query_end = (
        original_end
        + timedelta(
            seconds=(
                padding_seconds
            )
        )
    )

    observations = []
    frozen_traces = []

    for index, trace_id in enumerate(
        trace_ids,
        start=1,
    ):
        print(
            f"  [{index:02d}/"
            f"{len(trace_ids):02d}] "
            f"{trace_id}"
        )

        result = client.search_logs(
            start=query_start,
            end=query_end,

            trace_id=trace_id,

            limit=(
                limit_per_trace
            ),

            time_field=(
                "observedTimestamp"
            ),
        )

        if (
            result.total_hits
            > len(
                result.logs
            )
        ):
            raise RuntimeError(
                "Log query was truncated "
                f"for trace {trace_id}: "
                f"total_hits="
                f"{result.total_hits}, "
                f"returned="
                f"{len(result.logs)}."
            )

        observation = (
            observe_trace_logs(
                trace_id,
                result.logs,
            )
        )

        observations.append(
            observation
        )

        frozen_traces.append(
            {
                "trace_id":
                    trace_id,

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

                "timed_out":
                    result.timed_out,

                "observation":
                    asdict(
                        observation
                    ),

                "logs": [
                    serialize_log(
                        log
                    )
                    for log
                    in result.logs
                ],
            }
        )

    summary = (
        summarize_log_window(
            observations
        )
    )

    return {
        "original_start":
            original_start
            .isoformat(),

        "original_end":
            original_end
            .isoformat(),

        "query_start":
            query_start
            .isoformat(),

        "query_end":
            query_end
            .isoformat(),

        "padding_seconds":
            padding_seconds,

        "time_field":
            "observedTimestamp",

        "trace_count":
            len(
                trace_ids
            ),

        "summary":
            asdict(
                summary
            ),

        "observations": [
            asdict(
                observation
            )
            for observation
            in observations
        ],

        "traces":
            frozen_traces,

        "_observation_objects":
            observations,
    }


def printable_body(
    body_key: str,
    *,
    limit: int = 100,
) -> str:
    if len(
        body_key
    ) <= limit:
        return body_key

    return (
        body_key[
            :limit - 3
        ]
        + "..."
    )


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--trace-artifact",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    parser.add_argument(
        "--padding-seconds",
        type=int,
        default=60,
    )

    parser.add_argument(
        "--limit-per-trace",
        type=int,
        default=1000,
    )

    args = parser.parse_args()

    artifact_path = Path(
        args.trace_artifact
    )

    artifact = json.loads(
        artifact_path.read_text(
            encoding="utf-8"
        )
    )

    scenario = artifact[
        "scenario"
    ]

    base_url = os.getenv(
        "ROOTLENS_OPENSEARCH_URL",
        "http://localhost:9200",
    )

    client = OpenSearchClient(
        base_url
    )

    print(
        "=" * 90
    )

    print(
        "ROOTLENS EXPERIMENT 015C.4"
    )

    print(
        "=" * 90
    )

    print(
        f"Scenario: {scenario}"
    )

    print(
        f"Trace artifact: "
        f"{artifact_path}"
    )

    print(
        f"OpenSearch: "
        f"{base_url}"
    )

    print()

    print(
        "Capturing baseline logs..."
    )

    baseline = capture_window(
        client=client,

        window=artifact[
            "baseline"
        ],

        padding_seconds=(
            args.padding_seconds
        ),

        limit_per_trace=(
            args.limit_per_trace
        ),
    )

    print()

    print(
        "Capturing incident logs..."
    )

    incident = capture_window(
        client=client,

        window=artifact[
            "incident"
        ],

        padding_seconds=(
            args.padding_seconds
        ),

        limit_per_trace=(
            args.limit_per_trace
        ),
    )

    baseline_objects = (
        baseline.pop(
            "_observation_objects"
        )
    )

    incident_objects = (
        incident.pop(
            "_observation_objects"
        )
    )

    comparison = (
        compare_log_windows(
            baseline_objects,
            incident_objects,
        )
    )

    output = {
        "experiment":
            "015C.4",

        "scenario":
            scenario,

        "source_trace_artifact":
            str(
                artifact_path
            ),

        "opensearch_url":
            base_url,

        "analysis_unit":
            "trace_presence",

        "signature_definition": {
            "service_name":
                "exact",

            "severity_text":
                "exact_raw",

            "body":
                "exact",
        },

        "baseline":
            baseline,

        "incident":
            incident,

        "comparison":
            asdict(
                comparison
            ),
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

    print()
    print(
        "=" * 90
    )

    print(
        "WINDOW SUMMARY"
    )

    print(
        "=" * 90
    )

    print(
        "Baseline:"
    )

    print(
        "  traces: "
        f"{comparison.baseline.trace_count}"
    )

    print(
        "  traces with logs: "
        f"{comparison.baseline.traces_with_logs}"
    )

    print(
        "  total logs: "
        f"{comparison.baseline.total_logs}"
    )

    print()

    print(
        "Incident:"
    )

    print(
        "  traces: "
        f"{comparison.incident.trace_count}"
    )

    print(
        "  traces with logs: "
        f"{comparison.incident.traces_with_logs}"
    )

    print(
        "  total logs: "
        f"{comparison.incident.total_logs}"
    )

    print()

    print(
        "TOP PREVALENCE DIFFERENCES"
    )

    for difference in (
        comparison
        .differences[:20]
    ):
        signature = (
            difference.signature
        )

        print(
            f"  delta="
            f"{difference.delta:+.3f} "
            f"baseline="
            f"{difference.baseline_trace_count}"
            f"/"
            f"{comparison.baseline.trace_count} "
            f"incident="
            f"{difference.incident_trace_count}"
            f"/"
            f"{comparison.incident.trace_count}"
        )

        print(
            "    "
            f"service="
            f"{signature.service_name!r} "
            f"severity="
            f"{signature.severity_text!r}"
        )

        print(
            "    "
            f"body="
            f"{printable_body(signature.body_key)}"
        )

    print()
    print(
        f"Frozen artifact: "
        f"{output_path}"
    )


if __name__ == "__main__":
    main()